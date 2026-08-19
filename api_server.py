"""
FastAPI 后端服务
提供三个接口：
  - POST /chat        ：用户发送消息，返回 AI 回复
  - GET  /tickets     ：查询所有工单
  - PUT  /tickets/{id}：更新工单状态
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from customer_service_agent import chat
from db import get_all_tickets, update_ticket_status

# 创建 FastAPI 应用
app = FastAPI(
    title="AI 智能客服工单系统",
    description="用户通过网页咨询，AI 自动回答常见问题；复杂问题自动生成工单转接人工。",
    version="1.0.0",
)


# ========== 请求/响应数据模型 ==========

class ChatRequest(BaseModel):
    """聊天请求体"""
    message: str  # 用户发送的消息


class ChatResponse(BaseModel):
    """聊天响应体"""
    reply: str                  # AI 回复内容
    need_human: bool            # 是否需要转人工
    ticket_id: Optional[int] = None    # 工单 ID（如果创建了）
    priority: Optional[str] = None     # 紧急程度（如果创建了）


class TicketUpdateRequest(BaseModel):
    """工单状态更新请求体"""
    status: str  # 新状态：pending / processing / done


# ========== 接口定义 ==========

@app.post("/chat", response_model=ChatResponse, summary="发送消息给客服")
def post_chat(req: ChatRequest):
    """
    接收用户消息，调用 AI 客服处理。
    如果命中转人工规则，会自动创建工单。
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    result = chat(req.message.strip())
    return ChatResponse(**result)


@app.get("/tickets", summary="查询所有工单")
def list_tickets():
    """
    返回所有工单列表，按创建时间倒序排列。
    供工单管理页面使用。
    """
    tickets = get_all_tickets()
    return {"total": len(tickets), "tickets": tickets}


@app.put("/tickets/{ticket_id}", summary="更新工单状态")
def put_ticket(ticket_id: int, req: TicketUpdateRequest):
    """
    更新指定工单的状态：
      - pending：待处理
      - processing：处理中
      - done：已完成
    """
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


@app.get("/", summary="健康检查")
def root():
    """服务根路径，用于健康检查"""
    return {"status": "ok", "service": "AI 智能客服工单系统"}


# 直接运行：python api_server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
