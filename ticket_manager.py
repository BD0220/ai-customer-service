"""
工单管理模块（升级版）
支持会话关联，与 Agent 的 escalate_to_human 工具配合。
"""

from db import create_ticket_record

# 紧急关键词
URGENT_KEYWORDS = ["投诉", "赔偿", "律师", "315", "12315", "举报", "起诉", "法院"]


def judge_priority(user_message: str, reason: str = "") -> str:
    """
    根据用户消息和转人工原因判断紧急程度。

    Args:
        user_message: 用户原始消息
        reason: AI 给出的转人工原因

    Returns:
        "urgent" 或 "normal"
    """
    combined = (user_message + reason).lower()
    for keyword in URGENT_KEYWORDS:
        if keyword in combined:
            return "urgent"
    return "normal"


def create_ticket(
    user_message: str,
    reason: str = "",
    session_id: str = None,
    user_id: str = "U10086",
) -> dict:
    """
    创建工单。当 AI 判断需要人工处理，或用户消息命中紧急关键词时调用。

    Args:
        user_message: 用户的原始消息
        reason: AI 给出的转人工原因
        session_id: 关联的会话 ID
        user_id: 用户 ID

    Returns:
        工单信息字典
    """
    # 生成摘要
    if reason:
        summary = f"用户问题：{user_message[:80]} | 转人工原因：{reason[:100]}"
    else:
        summary = f"用户请求人工处理：{user_message[:120]}"

    # 判断紧急程度
    priority = judge_priority(user_message, reason)

    # 写入数据库
    ticket_id = create_ticket_record(
        summary=summary,
        priority=priority,
        session_id=session_id,
        user_id=user_id,
    )

    # 返回提示消息
    if priority == "urgent":
        message = (
            "非常抱歉给您带来不好的体验 😔\n\n"
            f"您的问题已升级为**紧急工单**（工单号：#{ticket_id}），"
            "我们将优先安排人工客服处理，请您稍候！"
        )
    else:
        message = (
            "好的，已为您转接人工客服 👩‍💼\n\n"
            f"工单号：#{ticket_id}，客服人员会尽快与您联系，请耐心等待～"
        )

    return {
        "ticket_id": ticket_id,
        "summary": summary,
        "priority": priority,
        "message": message,
    }
