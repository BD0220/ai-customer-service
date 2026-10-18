"""
FastAPI 后端服务（升级版）
提供 RESTful API，支持多轮对话 session。
"""

import os
import sys

# 目录结构：backend/（业务代码）+ frontend/（界面层）。直接跑这个文件或从仓库根
# `uvicorn api_server:app` 启动时，两边都要在 sys.path 上，否则 `from db import ...`
# 这种平铺导入会直接 ModuleNotFoundError。
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "backend"), os.path.join(_ROOT, "frontend")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from customer_service_agent import chat
from db import (
    get_all_tickets,
    update_ticket_status,
    get_ticket_stats,
    list_open_sessions,
    get_session_messages,
    set_session_mode,
    VALID_SESSION_MODES,
)

# 创建 FastAPI 应用
app = FastAPI(
    title="AI 智能客服工单系统 API",
    description="基于 LLM + Function Calling + RAG 的智能客服 Agent 系统",
    version="2.0.0",
)

# 允许跨域（方便前端/Gradio 调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 数据模型 ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None  # 为空则新建会话


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str
    need_human: bool
    ticket_id: Optional[int] = None
    priority: Optional[str] = None
    session_id: str
    tool_trace: Optional[list] = None  # 工具调用链路（调试用）
    # True = 人工接管中，AI 跳过了应答（消息已转达坐席工作台）
    human_handling: bool = False


class TicketUpdateRequest(BaseModel):
    """工单状态更新请求"""
    status: str  # pending / processing / done


class AgentReplyRequest(BaseModel):
    """人工坐席回复请求"""
    content: str


class SessionModeRequest(BaseModel):
    """会话模式切换请求"""
    mode: str  # ai / human / closed


# ========== 接口 ==========

@app.post("/chat", response_model=ChatResponse, summary="发送消息给客服 Agent")
def post_chat(req: ChatRequest):
    """
    发送用户消息，Agent 会：
    1. 检索知识库（RAG）
    2. 自主决定是否调用工具（查订单/查物流/查商品/退货评估）
    3. 复杂问题自动转人工并生成工单
    4. 支持多轮对话（通过 session_id 维持上下文）
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    result = chat(req.message.strip(), session_id=req.session_id)
    return ChatResponse(**result)


@app.get("/tickets", summary="查询所有工单")
def list_tickets():
    """返回所有工单列表，按创建时间倒序"""
    tickets = get_all_tickets()
    stats = get_ticket_stats()
    return {"total": len(tickets), "stats": stats, "tickets": tickets}


@app.put("/tickets/{ticket_id}", summary="更新工单状态")
def put_ticket(ticket_id: int, req: TicketUpdateRequest):
    """更新工单状态：pending → processing → done"""
    valid_status = ("pending", "processing", "done")
    if req.status not in valid_status:
        raise HTTPException(
            status_code=400,
            detail=f"无效状态，必须是：{', '.join(valid_status)}",
        )

    success = update_ticket_status(ticket_id, req.status)
    if not success:
        raise HTTPException(status_code=404, detail=f"工单 #{ticket_id} 不存在")

    return {
        "ticket_id": ticket_id,
        "status": req.status,
        "message": f"工单 #{ticket_id} 状态已更新为：{req.status}",
    }


@app.get("/stats", summary="获取工单统计数据")
def get_stats():
    """获取工单统计概览"""
    return get_ticket_stats()


# ========== 人工坐席工作台接口（Chatwoot 式接管闭环） ==========

@app.get("/sessions", summary="坐席会话列表")
def list_sessions():
    """
    返回所有未关闭会话（ai / human 模式），带最后一条消息、
    未结工单数 —— 坐席工作台左侧列表的数据源。
    """
    return {"sessions": list_open_sessions()}


@app.get("/sessions/{session_id}/history", summary="会话完整消息流")
def get_history(session_id: str):
    """原始消息流（user / assistant / agent），工作台查看与用户侧轮询渲染用。"""
    messages = get_session_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或没有消息")
    return {"session_id": session_id, "messages": messages}


@app.post("/sessions/{session_id}/agent-reply", summary="人工坐席回复")
def agent_reply(session_id: str, req: AgentReplyRequest):
    """
    人工坐席在系统内直接回复用户。
    消息以 role="agent" 落库：用户侧轮询可见；
    交还 AI 后会作为带标注的 assistant 消息进入上下文，AI 能衔接人工的处理进度。
    """
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="回复内容不能为空")

    from db import save_conversation, touch_session
    save_conversation(session_id, "agent", content)
    touch_session(session_id)
    return {"status": "success", "session_id": session_id}


@app.put("/sessions/{session_id}/mode", summary="切换会话应答方")
def switch_mode(session_id: str, req: SessionModeRequest):
    """
    接管（human）/ 交还 AI（ai）/ 关闭会话（closed）。
    human 模式下 Agent 入口直接短路，AI 不再应答。
    """
    if req.mode not in VALID_SESSION_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"无效模式，必须是：{', '.join(VALID_SESSION_MODES)}",
        )
    ok = set_session_mode(session_id, req.mode)
    if not ok:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return {"status": "success", "session_id": session_id, "mode": req.mode}


@app.get("/health", summary="健康检查")
def health():
    return {
        "service": "AI 智能客服工单系统",
        "version": "3.0.0",
        "status": "ok",
        "features": ["Function Calling", "RAG", "Multi-turn Dialogue", "Auto Ticket", "Human Takeover"],
    }


# ========== 单端口：Gradio 界面挂载到根路径 ==========
# 为什么之前要两个服务：Gradio 自带一个独立的 HTTP 服务器（7860），
# 和 FastAPI（8000）是两个 ASGI 应用，只能各起一个进程。
# 现在 mount_gradio_app 把 Gradio 挂到同一个 FastAPI 应用上，
# 所有路由已在上文注册完毕（路由优先于挂载，/docs /stats 等不会被遮住），
# 一个进程一个端口搞定界面 + API。
try:
    import gradio as gr
    from ui import demo, GRADIO_THEME, CSS

    app = gr.mount_gradio_app(app, demo, path="/", theme=GRADIO_THEME, css=CSS)
except Exception as e:  # Gradio 缺失或界面构建失败时退化为纯 API 服务
    print(f"[启动] Gradio 界面挂载失败，仅提供 API: {e}")


# 启动：python api_server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
