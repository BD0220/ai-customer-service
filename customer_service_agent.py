"""
核心客服 Agent 模块
调用 DeepSeek API 处理用户问题，并判断是否需要转人工
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

from db import save_conversation
from ticket_manager import need_human, create_ticket

# 加载 .env 环境变量
load_dotenv()

# 读取 DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 初始化 OpenAI 客户端（DeepSeek 兼容 OpenAI SDK）
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# 系统提示词：定义"小助手"的身份、能力边界和转人工规则
SYSTEM_PROMPT = """你是"小助手"，某电商平台的智能客服。

## 你的能力
1. 查订单：帮助用户查询订单状态、订单详情
2. 查物流：帮助用户查询物流信息、配送进度
3. 解答退货政策：向用户说明退货、换货的规则和流程
4. 回答产品咨询：解答关于商品规格、使用方法、库存等问题

## 你绝对不能做
- 不能进行退款操作或承诺退款
- 不能承诺任何形式的赔偿
- 不能泄露其他用户的任何信息
- 不能编造不存在的订单号或物流信息

## 转人工规则
当遇到以下情况时，你必须明确回复"[NEED_HUMAN]"开头，后接简短原因：
- 用户明确要求投诉、退款、赔偿
- 用户情绪激动或反复要求转人工
- 问题超出你的能力范围，你无法解答
- 涉及账户安全、支付异常等敏感问题

## 回复风格
- 语气亲切友好、有耐心，像一个热情的朋友
- 不能冷冰冰、机械地回答
- 回答简洁清晰，避免冗长
- 适当使用表情符号增加亲和力 😊
"""


def chat(user_message: str) -> dict:
    """
    处理用户消息，返回 AI 回复。
    流程：
      1. 先用关键词判断是否需要直接转人工
      2. 否则调用 DeepSeek API 获取回复
      3. 如果 AI 返回 [NEED_HUMAN] 标记，则创建工单
      4. 保存对话记录到数据库

    Args:
        user_message: 用户发送的消息文本

    Returns:
        字典：
          - reply: 最终回复给用户的文本
          - need_human: 是否转人工（bool）
          - ticket_id: 工单 ID（如果创建了工单，否则为 None）
          - priority: 工单紧急程度（如果创建了工单，否则为 None）
    """
    # 第一步：关键词快速判断，命中立即转人工
    if need_human(user_message):
        ticket = create_ticket(user_message)
        reply = ticket["message"]
        # 保存对话记录
        save_conversation(user_message, reply)
        return {
            "reply": reply,
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
        }

    # 第二步：调用 DeepSeek API
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.5,
            max_tokens=500,
            stream=False,
        )
        ai_reply = response.choices[0].message.content.strip()
    except Exception as e:
        # API 调用失败时，兜底转人工
        error_msg = f"AI 服务暂时不可用（{str(e)[:60]}），已为您转接人工客服。"
        ticket = create_ticket(user_message, ai_reply=error_msg)
        save_conversation(user_message, error_msg)
        return {
            "reply": error_msg,
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
        }

    # 第三步：检查 AI 是否主动要求转人工
    if ai_reply.startswith("[NEED_HUMAN]"):
        # 去掉标记，保留原因说明（如果有的话）
        reason = ai_reply.replace("[NEED_HUMAN]", "").strip()
        ticket = create_ticket(user_message, ai_reply=reason)
        reply = ticket["message"]
        save_conversation(user_message, reply)
        return {
            "reply": reply,
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
        }

    # 第四步：正常回复，保存对话
    save_conversation(user_message, ai_reply)
    return {
        "reply": ai_reply,
        "need_human": False,
        "ticket_id": None,
        "priority": None,
    }


# 模块直接运行时做一个简单测试
if __name__ == "__main__":
    test_messages = [
        "我的订单什么时候发货？",
        "我要退款！你们的商品有质量问题！",
        "退货政策是什么？",
    ]
    for msg in test_messages:
        print(f"\n用户：{msg}")
        result = chat(msg)
        print(f"小助手：{result['reply']}")
        if result["need_human"]:
            print(f"  → 已创建工单 #{result['ticket_id']}（{result['priority']}）")
