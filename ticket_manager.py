"""
工单管理模块
负责判断是否需要转人工，并创建工单
"""

from db import create_ticket_record

# 需要转人工的关键词列表
HUMAN_KEYWORDS = ["投诉", "退款", "赔偿", "转人工", "人工客服", "举报", "律师", "315", "12315"]

# 关键词到紧急程度的映射
URGENT_KEYWORDS = ["投诉", "赔偿", "律师", "315", "12315", "举报"]


def need_human(user_message: str) -> bool:
    """
    判断用户消息是否包含需要转人工的关键词

    Args:
        user_message: 用户发送的消息文本

    Returns:
        True 表示需要转人工，False 表示 AI 可以自行处理
    """
    message_lower = user_message.lower()
    for keyword in HUMAN_KEYWORDS:
        if keyword in message_lower:
            return True
    return False


def judge_priority(user_message: str) -> str:
    """
    根据用户消息内容判断工单紧急程度

    Args:
        user_message: 用户消息文本

    Returns:
        "urgent" 或 "normal"
    """
    for keyword in URGENT_KEYWORDS:
        if keyword in user_message:
            return "urgent"
    return "normal"


def create_ticket(user_message: str, ai_reply: str = "") -> dict:
    """
    创建工单。当 AI 判断需要人工处理时调用。

    Args:
        user_message: 用户的原始消息
        ai_reply: AI 给出的初步回复（可能为空，用于补充摘要）

    Returns:
        包含工单信息的字典：{"ticket_id", "summary", "priority", "message"}
    """
    # 生成问题摘要：优先用 AI 回复中的说明，否则截取用户消息
    if ai_reply and "转人工" not in ai_reply:
        summary = f"用户消息：{user_message} | AI初步回复：{ai_reply[:80]}"
    else:
        summary = f"用户请求人工处理：{user_message[:100]}"

    # 判断紧急程度
    priority = judge_priority(user_message)

    # 写入数据库
    ticket_id = create_ticket_record(summary=summary, priority=priority)

    # 根据紧急程度返回不同提示
    if priority == "urgent":
        message = "您的问题已升级为紧急工单，我们将优先安排人工客服处理，请稍候！"
    else:
        message = "已为您转接人工客服，客服人员会尽快与您联系，请耐心等待～"

    return {
        "ticket_id": ticket_id,
        "summary": summary,
        "priority": priority,
        "message": message,
    }
