"""
FastAPI 后端服务（升级版）
提供 RESTful API，支持多轮对话 session。
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status, get_ticket_stats

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


class TicketUpdateRequest(BaseModel):
    """工单状态更新请求"""
    status: str  # pending / processing / done


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


@app.get("/", summary="健康检查")
def root():
    return {
        "service": "AI 智能客服工单系统",
        "version": "2.0.0",
        "status": "ok",
        "features": ["Function Calling", "RAG", "Multi-turn Dialogue", "Auto Ticket"],
    }


# 启动：python api_server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
