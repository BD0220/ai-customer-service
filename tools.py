"""
Agent 工具集（Function Calling）
定义 AI 可以调用的工具函数，以及对应的 OpenAI function schema。
AI 根据用户意图自主决定调用哪个工具、传什么参数。
"""

import json
from datetime import datetime
import mock_data


# ========== 工具函数实现 ==========

def query_order(order_id: str = None, user_id: str = "U10086") -> str:
    """
    查询订单信息。可以按订单号查单个订单，也可以查用户的所有订单。

    Args:
        order_id: 订单号（可选）。如果不提供，则返回该用户的所有订单。
        user_id: 用户 ID，默认当前登录用户 U10086。

    Returns:
        JSON 格式的订单信息字符串
    """
    if order_id:
        # 按订单号查询
        order = mock_data.get_order(order_id.strip())
        if not order:
            return json.dumps({"error": f"未找到订单号 {order_id}，请核实订单号是否正确。"}, ensure_ascii=False)
        if order["user_id"] != user_id:
            return json.dumps({"error": "该订单不属于当前用户，无法查询。"}, ensure_ascii=False)
        return json.dumps({"order": order}, ensure_ascii=False, default=str)
    else:
        # 查询用户所有订单
        orders = mock_data.get_user_orders(user_id)
        if not orders:
            return json.dumps({"message": "您目前没有任何订单。"}, ensure_ascii=False)
        # 简化返回，只返回关键信息
        summary = [
            {
                "order_id": o["order_id"],
                "status": o["status"],
                "total_amount": o["total_amount"],
                "item_count": sum(i["qty"] for i in o["items"]),
                "created_at": o["created_at"],
            }
            for o in orders
        ]
        return json.dumps({"orders": summary, "total": len(summary)}, ensure_ascii=False)


def query_logistics(order_id: str, tracking_no: str = None) -> str:
    """
    查询物流信息。可以通过订单号或运单号查询。

    Args:
        order_id: 订单号
        tracking_no: 运单号（可选）。如果提供则直接查运单，否则根据订单号查找。

    Returns:
        JSON 格式的物流信息字符串
    """
    if tracking_no:
        logistics = mock_data.get_logistics(tracking_no.strip())
        if not logistics:
            return json.dumps({"error": f"未找到运单号 {tracking_no} 的物流信息。"}, ensure_ascii=False)
        return json.dumps({"logistics": logistics}, ensure_ascii=False, default=str)

    if order_id:
        logistics = mock_data.get_order_logistics(order_id.strip())
        if not logistics:
            order = mock_data.get_order(order_id.strip())
            if not order:
                return json.dumps({"error": f"未找到订单号 {order_id}。"}, ensure_ascii=False)
            if order["status"] == "待发货":
                return json.dumps({
                    "message": f"订单 {order_id} 当前状态为「待发货」，尚未生成物流信息。",
                    "order_status": order["status"]
                }, ensure_ascii=False)
            return json.dumps({"message": f"订单 {order_id} 暂无物流信息。"}, ensure_ascii=False)
        return json.dumps({"logistics": logistics}, ensure_ascii=False, default=str)

    return json.dumps({"error": "请提供订单号或运单号以查询物流。"}, ensure_ascii=False)


def query_product(keyword: str = None, product_id: str = None) -> str:
    """
    查询商品信息。可以按关键词搜索商品，也可以按商品 ID 查详情。

    Args:
        keyword: 搜索关键词，如商品名称、类别（T恤、耳机、双肩包等）
        product_id: 商品 ID（可选），查询特定商品的详细信息

    Returns:
        JSON 格式的商品信息字符串
    """
    if product_id:
        product = mock_data.get_product(product_id.strip())
        if not product:
            return json.dumps({"error": f"未找到商品 ID {product_id}。"}, ensure_ascii=False)
        return json.dumps({"product": product}, ensure_ascii=False, default=str)

    if keyword:
        results = mock_data.search_products(keyword.strip())
        if not results:
            return json.dumps({"message": f'未找到与"{keyword}"相关的商品。'}, ensure_ascii=False)
        # 简化返回
        summary = [
            {
                "product_id": p["product_id"],
                "name": p["name"],
                "price": p["price"],
                "original_price": p["original_price"],
                "category": p["category"],
                "stock": p["stock"],
                "tags": p["tags"],
            }
            for p in results
        ]
        return json.dumps({"products": summary, "total": len(summary)}, ensure_ascii=False, default=str)

    # 没传参数，返回热门商品
    all_products = [
        {
            "product_id": p["product_id"],
            "name": p["name"],
            "price": p["price"],
            "category": p["category"],
        }
        for p in mock_data.PRODUCTS
    ]
    return json.dumps({"products": all_products, "tip": "您可以告诉我具体想找什么类型的商品，比如T恤、耳机、双肩包。"}, ensure_ascii=False)


def calculate_return(order_id: str, reason: str = "") -> str:
    """
    估算退货退款信息。根据订单状态和金额，给出退货可行性和退款预估。
    注意：此工具仅提供信息查询，不会实际执行退款。

    Args:
        order_id: 订单号
        reason: 退货原因（可选）

    Returns:
        JSON 格式的退货评估信息
    """
    order = mock_data.get_order(order_id.strip())
    if not order:
        return json.dumps({"error": f"未找到订单号 {order_id}。"}, ensure_ascii=False)

    days_since_order = 4  # 模拟：假设订单是 4 天前签收的
    can_return = days_since_order <= 7

    result = {
        "order_id": order_id,
        "order_status": order["status"],
        "order_amount": order["total_amount"],
        "days_since_delivery": days_since_order,
        "can_return": can_return,
        "refund_estimate": order["total_amount"] if can_return else 0,
        "refund_timeline": "验收合格后 1-3 个工作日原路退回",
        "shipping_fee": "质量问题平台承担；无理由退货买家承担（首单可用运费券）",
        "next_steps": "如需退货，请在订单详情页点击「申请售后」，或由人工客服协助处理。",
    }

    if reason and ("质量" in reason or "坏" in reason or "破" in reason):
        result["note"] = "检测到质量问题描述，建议拍照留证，退货运费将由平台承担。"

    return json.dumps(result, ensure_ascii=False)


def escalate_to_human(reason: str, urgency: str = "normal") -> str:
    """
    将问题升级给人工客服。当 AI 无法解决、用户明确要求转人工、
    或涉及投诉/退款/赔偿等敏感问题时调用。

    Args:
        reason: 需要转人工的原因描述
        urgency: 紧急程度，"normal"（普通）或 "urgent"（紧急）

    Returns:
        确认信息字符串（实际工单创建在 Agent 主循环中处理）
    """
    return json.dumps({
        "escalated": True,
        "reason": reason,
        "urgency": urgency,
        "message": "已为您转接人工客服，请稍候。"
    }, ensure_ascii=False)


# ========== Function Calling Schema 定义 ==========
# 这些 schema 会传给 DeepSeek API，让 AI 知道有哪些工具可用

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "查询用户的订单信息。当用户询问订单状态、订单详情、买了什么、发货情况时调用。可按订单号查询，也可列出用户所有订单。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号，如 ORD20260815001。如果用户没提供具体订单号，则留空，系统会返回用户所有订单。",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户 ID，默认为当前登录用户 U10086。",
                        "default": "U10086",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "查询物流配送信息。当用户询问快递到哪了、物流状态、什么时候送达时调用。需要提供订单号或运单号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号，如 ORD20260815001。",
                    },
                    "tracking_no": {
                        "type": "string",
                        "description": "运单号，如 SF1234567890。如果用户直接提供了运单号，使用此字段。",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_product",
            "description": "查询商品信息或搜索商品。当用户询问产品规格、价格、库存、材质，或搜索某类商品时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如 T恤、耳机、双肩包、运动等。",
                    },
                    "product_id": {
                        "type": "string",
                        "description": "商品 ID，如 P001。如果用户指定了具体商品 ID，使用此字段查询详情。",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_return",
            "description": "估算退货退款信息。当用户询问能退多少钱、退货是否可行、退款时效时调用。仅提供信息，不执行实际退款。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "要退货的订单号。",
                    },
                    "reason": {
                        "type": "string",
                        "description": "退货原因，如质量问题、不想要了、尺寸不合适等。",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "将问题转接给人工客服。当遇到以下情况时必须调用：用户明确要求转人工、投诉、要求退款赔偿、AI 无法解决的问题、涉及账户安全或支付异常。",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "需要转人工的具体原因，例如：用户要求退款、用户投诉商品质量、AI 无法解答的技术问题等。",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent"],
                        "description": "紧急程度。涉及投诉、赔偿、律师、315、举报等设为 urgent，其他为 normal。",
                        "default": "normal",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


# 工具名 -> 函数的映射表
TOOL_MAP = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "query_product": query_product,
    "calculate_return": calculate_return,
    "escalate_to_human": escalate_to_human,
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    执行工具调用，返回工具结果字符串。

    Args:
        tool_name: 工具名称
        arguments: 工具参数字典

    Returns:
        工具执行结果（JSON 字符串）
    """
    func = TOOL_MAP.get(tool_name)
    if not func:
        return json.dumps({"error": f"未知工具：{tool_name}"}, ensure_ascii=False)

    try:
        result = func(**arguments)
        return result
    except Exception as e:
        return json.dumps({"error": f"工具执行出错：{str(e)}"}, ensure_ascii=False)
