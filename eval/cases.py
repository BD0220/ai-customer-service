# -*- coding: utf-8 -*-
"""
20 条标注评测集 —— AI 客服 Agent

字段说明：
  id           用例编号
  category     类别（订单查询/知识问答/转人工/闲聊/边界）
  message      发给客服的用户输入
  expect_human 期望 need_human（True=应转人工 / False=应自动处理）
  allowed_tools 允许出现的业务工具名列表；空列表 [] 表示不该调任何业务工具
  tool_skip    True 表示本用例跳过工具打分（行为合法但有歧义）
  must         回复中必须包含的关键词（全中才算过）
  forbidden    回复中禁止出现的关键词（出现即记违规）
  note         备注 / 这个用例在验证什么

业务工具集合：query_order / query_logistics / query_product / calculate_return
非业务（不算误调）：escalate_to_human / keyword_gate
"""

CASES = [
    # ============ A. 订单 / 物流查询（Function Calling）============
    {
        "id": "F01", "category": "订单查询",
        "message": "我的订单到哪了？",
        "expect_human": False, "allowed_tools": ["query_order"],
        "must": [], "forbidden": [],
        "note": "无 order_id，应调 query_order 拉该用户全部订单",
    },
    {
        "id": "F02", "category": "物流查询",
        "message": "帮我查一下订单 ORD20260815001 的物流到哪里了",
        "expect_human": False, "allowed_tools": ["query_order", "query_logistics"],
        "must": [], "forbidden": [],
        "note": "给了具体订单号，可先验单再查物流",
    },
    {
        "id": "F03", "category": "商品查询",
        "message": "无线降噪耳机 Pro 现在卖多少钱？",
        "expect_human": False, "allowed_tools": ["query_product"],
        "must": ["耳机"], "forbidden": [],
        "note": "应调 query_product 返回真实商品信息，不许编价格",
    },
    {
        "id": "F04", "category": "商品查询",
        "message": "纯棉圆领T恤有哪些尺码？",
        "expect_human": False, "allowed_tools": ["query_product"],
        "must": [], "forbidden": [],
        "note": "商品维度查询",
    },

    # ============ B. 知识问答（RAG）============
    {
        "id": "R01", "category": "知识问答",
        "message": "你们的退货政策是什么？",
        "expect_human": False, "allowed_tools": [],
        "must": ["无理由"], "forbidden": [],
        "note": "应检索知识库命中退货政策原文",
    },
    {
        "id": "R02", "category": "知识问答",
        "message": "7天无理由退货，运费谁来承担？",
        "expect_human": False, "allowed_tools": [],
        "must": ["运费"], "forbidden": [],
        "note": "政策细节，应基于知识库原文回答",
    },
    {
        "id": "R03", "category": "RAG边界",
        "message": "我买的东西30天了，还能退吗？",
        "expect_human": False, "allowed_tools": [],
        "must": ["7"], "forbidden": [],
        "note": "RAG 幻觉测试：知识库无 30 天档，应引用 7 天条款推理，不得编造；forbidden 不强设，人工复查回复是否把 30 天说成可退",
    },
    {
        "id": "R04", "category": "知识问答",
        "message": "你们一般多久发货？",
        "expect_human": False, "allowed_tools": [],
        "must": ["发货"], "forbidden": [],
        "note": "常见问题覆盖",
    },

    # ============ C. 转人工判定 ============
    {
        "id": "T01", "category": "真实投诉",
        "message": "我要投诉！你们卖的耳机有质量问题，必须给我赔偿！",
        "expect_human": True, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "命中 投诉/赔偿 → 语义确认后仍应建工单（召回优先）",
    },
    {
        "id": "T02", "category": "咨询非投诉",
        "message": "我想了解一下你们的投诉流程是什么？",
        "expect_human": False, "allowed_tools": [],
        "must": ["客服"], "forbidden": [],
        "note": "语义二次确认修复目标：提及'投诉'≠真投诉，应正常回答渠道",
    },
    {
        "id": "T03", "category": "主动转人工",
        "message": "帮我转人工客服，我要问个事情",
        "expect_human": True, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "明确要求转人工 → 第二层 escalate",
    },
    {
        "id": "T04", "category": "查不到转人工",
        "message": "我订单号找不到了，帮我转人工处理一下",
        "expect_human": True, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "查询受阻 + 主动要求 → 应转人工",
    },

    # ============ D. 闲聊（不应幻觉/误调工具）============
    {
        "id": "S01", "category": "闲聊",
        "message": "今天天气不错啊",
        "expect_human": False, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "闲聊不得编造订单/政策",
    },
    {
        "id": "S02", "category": "闲聊",
        "message": "你叫什么名字？",
        "expect_human": False, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "闲聊",
    },
    {
        "id": "S03", "category": "闲聊",
        "message": "给我讲个笑话吧",
        "expect_human": False, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "闲聊",
    },

    # ============ E. 边界 / 易错 ============
    {
        "id": "E01", "category": "边界",
        "message": "我要退货，怎么操作？",
        "expect_human": False, "allowed_tools": [], "tool_skip": True,
        "must": [], "forbidden": [],
        "note": "'退货'不在关键词表；可能走知识回答或 calculate_return，均算合理，故跳过工具打分",
    },
    {
        "id": "E02", "category": "边界",
        "message": "你们卖假货，我要去12315举报你们！",
        "expect_human": True, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "命中 12315/举报 → 应拦截",
    },
    {
        "id": "E03", "category": "边界",
        "message": "你们的赔偿标准是什么？我想了解一下赔偿政策",
        "expect_human": False, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "含'赔偿'强词但是咨询意图——语义确认的最大考验，误拦即为误伤",
    },
    {
        "id": "E04", "category": "知识问答",
        "message": "耳机充不进电了，在保修期内能修吗？",
        "expect_human": False, "allowed_tools": [],
        "must": ["保修"], "forbidden": [],
        "note": "售后知识，应检索产品与售后政策",
    },
    {
        "id": "E05", "category": "边界",
        "message": "哈哈哈",
        "expect_human": False, "allowed_tools": [],
        "must": [], "forbidden": [],
        "note": "无意义输入应正常闲聊回应",
    },
]

if __name__ == "__main__":
    print(f"共 {len(CASES)} 条用例")
    from collections import Counter
    print(Counter(c["category"] for c in CASES))
