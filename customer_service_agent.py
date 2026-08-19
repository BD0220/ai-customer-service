"""
核心客服 Agent（升级版）
实现 ReAct 循环：思考 → 调用工具 → 观察结果 → 生成回复。
支持：
  - Function Calling（自主调用查询工具）
  - RAG 知识库检索（退货政策、FAQ 等基于真实文档回答）
  - 多轮对话（session 级上下文记忆）
  - 三层转人工保障（关键词 → Agent 自主调用 → 异常兜底）
"""

import os
import json
import uuid
from openai import OpenAI
from dotenv import load_dotenv

from db import (
    create_session,
    touch_session,
    save_conversation,
    get_conversation_history,
)
from ticket_manager import create_ticket
from tools import TOOL_DEFINITIONS, TOOL_MAP, execute_tool
from rag_engine import search_knowledge_base, format_context

# 加载环境变量
load_dotenv()

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 初始化 OpenAI 客户端（DeepSeek 兼容 OpenAI SDK）
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# 模型名称
MODEL_NAME = "deepseek-chat"

# 最大工具调用轮数（防止无限循环）
MAX_TOOL_ROUNDS = 5

# 历史消息保留条数（控制 token 消耗）
MAX_HISTORY = 20


def build_system_prompt(user_message: str) -> str:
    """
    动态构建 System Prompt：
      1. 基础角色和能力定义
      2. RAG 检索相关知识库段落，注入为参考资料
    """
    # 检索知识库
    kb_results = search_knowledge_base(user_message, top_k=3)
    context = format_context(kb_results)

    prompt = """你是"小助手"，某电商平台的智能客服 Agent。

## 你的能力
1. **查订单**：调用 query_order 工具查询用户订单状态和详情
2. **查物流**：调用 query_logistics 工具查询物流信息和配送进度
3. **商品咨询**：调用 query_product 工具搜索和查询商品信息
4. **退货评估**：调用 calculate_return 工具估算退款金额和退货可行性
5. **解答政策**：根据下方提供的参考资料回答退货政策、常见问题等
6. **转人工**：遇到无法处理的问题，调用 escalate_to_human 工具转接人工

## 行为规则
- 优先使用工具查询真实数据，不要编造订单号、物流信息或商品价格
- 如果工具返回了数据，基于数据回答，不要凭空想象
- 退货政策、保修、发票等问题，参考下方提供的知识库内容回答
- 每次回复只回答用户当前的问题，不要一次性列出所有信息
- 如果用户提供了订单号，直接使用；如果没提供但需要查询，可以列出用户的订单让 TA 选择

## 绝对不能做
- 不能执行实际退款操作（calculate_return 只做信息查询）
- 不能承诺赔偿金额或退款时间（以工具返回和知识库内容为准）
- 不能泄露其他用户的信息
- 不能编造不存在的订单号、运单号或商品信息

## 转人工规则
遇到以下情况，必须调用 escalate_to_human 工具：
- 用户明确要求转人工、投诉、赔偿、举报
- 工具查询不到结果且无法通过知识库回答
- 涉及账户安全、支付异常等敏感问题
- 用户情绪激动或反复表达不满

## 回复风格
- 语气亲切友好、有耐心，像一个热情的朋友 😊
- 回答简洁清晰，避免冗长
- 适当使用表情符号，但不要过度
- 用中文回答
"""

    if context:
        prompt += f"\n## 📚 知识库参考资料\n以下是与用户问题相关的政策和说明，请基于这些内容回答：\n\n{context}\n"

    return prompt


def chat(user_message: str, session_id: str = None) -> dict:
    """
    处理用户消息，执行 ReAct 循环。

    流程：
      1. 确保 session 存在（多轮对话管理）
      2. RAG 检索 → 构建 System Prompt
      3. 加载历史消息
      4. ReAct 循环：
         a. 调用 LLM
         b. 如果 LLM 返回 tool_calls → 执行工具 → 把结果发回 LLM → 继续循环
         c. 如果 LLM 返回普通文本 → 作为最终回复
      5. 检测是否调用了 escalate_to_human → 创建工单
      6. 保存对话记录

    Args:
        user_message: 用户消息
        session_id: 会话 ID，为空则新建

    Returns:
        {reply, need_human, ticket_id, priority, session_id, tool_trace}
    """
    # ---------- 1. Session 管理 ----------
    if not session_id:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
    create_session(session_id)
    touch_session(session_id)

    # ---------- 2. 关键词快速兜底（紧急情况） ----------
    urgent_keywords = ["投诉", "赔偿", "律师", "315", "12315", "举报", "起诉"]
    if any(kw in user_message for kw in urgent_keywords):
        ticket = create_ticket(
            user_message,
            reason="用户消息含紧急关键词",
            session_id=session_id,
        )
        save_conversation(session_id, "user", user_message)
        save_conversation(session_id, "assistant", ticket["message"])
        return {
            "reply": ticket["message"],
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
            "session_id": session_id,
            "tool_trace": [{"tool": "keyword_gate", "result": "urgent_keyword_matched"}],
        }

    # ---------- 3. 构建消息列表 ----------
    system_prompt = build_system_prompt(user_message)

    # 加载历史消息（多轮上下文）
    history = get_conversation_history(session_id, limit=MAX_HISTORY)
    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": user_message})

    # 保存用户消息
    save_conversation(session_id, "user", user_message)

    # ---------- 4. ReAct 循环 ----------
    tool_trace = []
    escalated = False
    escalation_reason = ""
    escalation_urgency = "normal"
    final_reply = ""

    try:
        for round_num in range(MAX_TOOL_ROUNDS):
            # 调用 DeepSeek API
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.5,
                max_tokens=1000,
            )

            choice = response.choices[0]
            msg = choice.message

            # 如果没有 tool_calls，说明 AI 给出了最终回复
            if not msg.tool_calls:
                final_reply = msg.content.strip()
                break

            # 有 tool_calls → 执行工具
            # 先把 assistant 的工具调用请求加入消息历史
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # 逐个执行工具调用
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                print(f"[Agent] 第{round_num+1}轮 调用工具：{tool_name}({arguments})")

                # 执行工具
                result_str = execute_tool(tool_name, arguments)
                tool_trace.append({
                    "round": round_num + 1,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result_preview": result_str[:200],
                })

                # 检查是否是转人工工具
                if tool_name == "escalate_to_human":
                    escalated = True
                    try:
                        result_data = json.loads(result_str)
                        escalation_reason = result_data.get("reason", arguments.get("reason", ""))
                        escalation_urgency = result_data.get("urgency", "normal")
                    except Exception:
                        escalation_reason = arguments.get("reason", "")
                        escalation_urgency = arguments.get("urgency", "normal")

                # 把工具结果加入消息历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

        else:
            # 超过最大轮数，强制收尾
            final_reply = "抱歉，我处理这个问题时遇到了一些困难，已为您转接人工客服。"
            escalated = True
            escalation_reason = "Agent 工具调用超过最大轮数"

    except Exception as e:
        # API 异常兜底：转人工
        error_msg = f"AI 服务暂时不可用（{str(e)[:80]}）"
        print(f"[Agent] 异常：{error_msg}")
        ticket = create_ticket(
            user_message,
            reason=error_msg,
            session_id=session_id,
        )
        save_conversation(session_id, "assistant", ticket["message"])
        return {
            "reply": f"抱歉，{error_msg}，已为您转接人工客服，请稍候。",
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
            "session_id": session_id,
            "tool_trace": tool_trace,
        }

    # ---------- 5. 处理转人工 ----------
    if escalated:
        ticket = create_ticket(
            user_message,
            reason=escalation_reason,
            session_id=session_id,
        )
        final_reply = ticket["message"]
        save_conversation(
            session_id, "assistant", final_reply,
            tool_calls=tool_trace,
        )
        return {
            "reply": final_reply,
            "need_human": True,
            "ticket_id": ticket["ticket_id"],
            "priority": ticket["priority"],
            "session_id": session_id,
            "tool_trace": tool_trace,
        }

    # ---------- 6. 正常回复 ----------
    save_conversation(
        session_id, "assistant", final_reply,
        tool_calls=tool_trace if tool_trace else None,
    )

    return {
        "reply": final_reply,
        "need_human": False,
        "ticket_id": None,
        "priority": None,
        "session_id": session_id,
        "tool_trace": tool_trace,
    }


# 直接运行时测试
if __name__ == "__main__":
    test_cases = [
        "你好，我想查一下我的订单",
        "订单 ORD20260815001 现在什么状态？",
        "帮我查下这个订单的物流",
        "退货需要什么条件？",
        "我要退款！你们的耳机有质量问题！",
    ]
    sid = None
    for msg in test_cases:
        print(f"\n{'='*60}")
        print(f"👤 用户：{msg}")
        result = chat(msg, session_id=sid)
        sid = result["session_id"]
        print(f"🤖 小助手：{result['reply']}")
        if result["tool_trace"]:
            for t in result["tool_trace"]:
                print(f"   🔧 {t['tool']}({t['arguments']})")
        if result["need_human"]:
            print(f"   🎫 工单 #{result['ticket_id']}（{result['priority']}）")
