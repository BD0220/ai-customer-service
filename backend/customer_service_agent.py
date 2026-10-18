"""
核心客服 Agent（升级版）
实现 ReAct 循环：思考 → 调用工具 → 观察结果 → 生成回复。
支持：
  - Function Calling（自主调用查询工具）
  - RAG 知识库检索（退货政策、FAQ 等基于真实文档回答）
  - 多轮对话（session 级上下文记忆）
  - 三层转人工保障（关键词 → Agent 自主调用 → 异常兜底）
  - LLM Provider 抽象层，支持 DeepSeek / OpenAI 无缝切换
"""

import os
import json
import uuid
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from db import (
    create_session,
    touch_session,
    save_conversation,
    get_conversation_history,
    get_session,
)
from ticket_manager import create_ticket
from tools import TOOL_DEFINITIONS, TOOL_MAP, execute_tool
from rag_engine import search_knowledge_base, format_context
from llm_provider import get_llm_provider

# 加载环境变量
load_dotenv()

# 通过抽象层初始化 LLM Provider（根据 LLM_PROVIDER 环境变量自动选择）
llm = get_llm_provider()

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
- **政策优先**：用户咨询政策、规则、流程类问题（退货、保修、运费、发货、如何操作等）时，**先直接依据知识库回答**；即使用户话里提到"我的订单/我买的东西"，也不要为了确认购买记录而先调用 query_order / query_logistics。但用户是要查订单状态/物流、或明确要求转人工时，照常调用对应工具，不受本条影响
- 如果用户提供了订单号，直接使用；如果用户询问订单状态或物流进度但未提供订单号，**必须先调用 query_order 查该用户的订单**，再基于查询结果回答，不要只反问订单号

## 绝对不能做
- 不能执行实际退款操作（calculate_return 只做信息查询）
- 不能承诺赔偿金额或退款时间（以工具返回和知识库内容为准）
- 不能泄露其他用户的信息
- 不能编造不存在的订单号、运单号或商品信息

## 转人工规则
遇到以下情况，必须调用 escalate_to_human 工具：
- 用户明确要求转人工、投诉、赔偿、举报（明确要求转人工时直接调用，不要先尝试自行解答或劝阻）
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
         a. 调用 LLM（通过 Provider 抽象层）
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

    # ---------- 1.5 人工接管检查（Chatwoot 式接管闭环的关键） ----------
    # 会话被人工接管后（mode=human，建工单时自动切换），Agent 直接闭嘴：
    # 消息照常落库（坐席工作台能看到），但不查知识库、不调 LLM、不建工单。
    # 这样人工回复期间用户的追问不会被 AI 抢答，也不会白烧 token。
    # 坐席点「交还 AI」把 mode 切回 ai 后，本分支自然失效。
    session_row = get_session(session_id)
    if session_row and session_row.get("mode") == "human":
        save_conversation(session_id, "user", user_message)
        logger.info(f"会话 {session_id} 处于人工接管中，Agent 跳过应答")
        return {
            "reply": "",
            "need_human": True,
            "ticket_id": None,
            "priority": None,
            "session_id": session_id,
            "tool_trace": [],
            "human_handling": True,
        }

    # ---------- 2. 关键词快速兜底（紧急情况，带语义二次确认） ----------
    urgent_keywords = ["投诉", "赔偿", "律师", "315", "12315", "举报", "起诉"]
    if any(kw in user_message for kw in urgent_keywords):
        # 纯关键词会误伤"我想了解投诉流程"这类咨询：
        # 命中后先让 LLM 做语义确认，是真实紧急诉求才建工单。
        # LLM 不可用时保守起见仍直接建工单（fail-safe：宁可误伤，不可漏接）。
        is_urgent = True
        try:
            check = llm.chat_completion(
                messages=[
                    {"role": "system", "content": (
                        "判断用户消息是否为真实的紧急客服诉求（正在投诉/索赔/维权），"
                        "还是仅仅提及相关词语（咨询流程、随口抱怨、假设性提问）。"
                        '只输出 JSON：{"urgent": true} 或 {"urgent": false}，不要输出其他内容。'
                    )},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.0,
                max_tokens=20,
            )
            content = (check.get("content") or "").lower().replace(" ", "")
            if '"urgent":false' in content:
                is_urgent = False
                logger.info(f"关键词命中但语义确认非紧急，继续走 Agent 流程：{user_message[:50]}")
        except Exception as e:
            logger.warning(f"关键词语义确认调用失败，保守处理为紧急：{e}")

        if is_urgent:
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
                "tool_trace": [{"round": 0, "tool": "keyword_gate", "arguments": {}, "result": "urgent_keyword_matched"}],
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
            # 通过 Provider 抽象层调用 LLM（无需关心底层是 DeepSeek 还是 OpenAI）
            llm_response = llm.chat_completion(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.5,
                max_tokens=1000,
            )

            # 如果没有 tool_calls，说明 AI 给出了最终回复
            if not llm_response["tool_calls"]:
                final_reply = llm_response["content"]
                break

            # 有 tool_calls → 执行工具
            # 先把 assistant 的工具调用请求加入消息历史
            messages.append({
                "role": "assistant",
                "content": llm_response["content"],
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                    for tc in llm_response["tool_calls"]
                ],
            })

            # 逐个执行工具调用
            for tc in llm_response["tool_calls"]:
                tool_name = tc["name"]
                arguments = tc["arguments"]

                logger.info(f"第{round_num+1}轮 调用工具：{tool_name}({arguments})")

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
                    "tool_call_id": tc["id"],
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
        logger.error(f"Agent 异常：{error_msg}")

        # 兜底自身也要兜底：若数据库故障，create_ticket / save_conversation 会再抛异常，
        # 导致整个 chat() 直接 500。这里降级处理：工单存不了，也必须给用户一个答复。
        reply = f"抱歉，{error_msg}，已为您转接人工客服，请稍候。"
        ticket_id = None
        priority = None
        try:
            ticket = create_ticket(
                user_message,
                reason=error_msg,
                session_id=session_id,
            )
            save_conversation(session_id, "assistant", ticket["message"])
            ticket_id = ticket["ticket_id"]
            priority = ticket["priority"]
        except Exception as db_err:
            logger.critical(f"兜底路径失败（数据库不可用？）：{db_err}")
            reply += "\n（系统提示：当前无法登记工单，请稍后重试或拨打客服热线。）"

        return {
            "reply": reply,
            "need_human": True,
            "ticket_id": ticket_id,
            "priority": priority,
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
