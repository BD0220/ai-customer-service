# 简历项目描述 — AI 智能客服 Agent 系统

> 以下文案可直接复制到简历中。根据投递岗位选择版本。

---

## 版本一：Agent/LLM 应用工程师（推荐，最匹配）

### AI 智能客服 Agent 系统
**技术栈**：Python · DeepSeek LLM · Function Calling · RAG · FastAPI · Gradio · SQLite · Docker

- 基于大模型 Function Calling 构建 ReAct 架构智能客服 Agent，AI 自主决策调用订单查询、物流跟踪、商品搜索、退货评估等 5 个工具，实现多步推理和真实数据查询
- 设计并实现 RAG 检索增强模块，基于 TF-IDF 对退换货政策、FAQ 等文档做分块索引和相似度检索，将相关文档动态注入 System Prompt，减少大模型幻觉
- 构建多轮对话 Session 管理机制，结合 SQLite 持久化对话历史和工具调用链路（tool trace），支持上下文连续交互
- 设计三层转人工保障机制：关键词快速拦截 → LLM 自主调用 escalate_to_human 工具 → API 异常兜底，确保投诉/退款等复杂问题 100% 转接人工
- 基于 FastAPI 构建 RESTful API，Gradio 实现双标签页前端（对话 + 工单管理），支持工单自动分级（urgent/normal）和状态流转
- 容器化部署，代码模块化设计（Agent/Tools/RAG/DB 分层解耦），工具层可独立扩展和替换 LLM Provider

**在线演示**：https://huggingface.co/spaces/BD0220/ai-customer-agent（部署后补充）
**代码仓库**：https://github.com/BD0220/ai-customer-service

---

## 版本二：全栈/后端工程师

### AI 智能客服工单系统
**技术栈**：Python · FastAPI · DeepSeek API · Gradio · SQLite · Docker

- 独立开发企业级智能客服系统，集成大语言模型实现自动问答、智能工具调用和工单自动转人工，目标自动解决率 70%+
- 基于 OpenAI Function Calling 协议实现 Agent 工具系统，AI 自主调用订单/物流/商品等 API，替代硬编码规则匹配
- 搭建 RAG 知识库检索模块，支持政策文档分块索引和语义检索，AI 基于真实文档回答而非编造
- 设计多轮对话 Session 管理，SQLite 存储对话、工单和会话数据，支持工具调用链路追踪
- FastAPI 提供 RESTful API（含 CORS、Swagger 文档），Gradio 构建实时交互前端，Docker 一键部署

---

## 版本三：精简版（简历空间有限时）

### AI 智能客服 Agent | DeepSeek, Function Calling, RAG, FastAPI, Python
- 基于 LLM Function Calling 构建 ReAct 架构客服 Agent，AI 自主调用 5 个业务工具查询真实数据，支持多步推理
- 实现 RAG 知识库检索（文档分块 + TF-IDF 相似度），动态注入 System Prompt，降低大模型幻觉
- 三层转人工机制 + 多轮 Session 管理 + 工单自动分级，FastAPI + Gradio 全栈实现，Docker 部署

---

## 项目架构说明（面试口述用）

### 整体架构
```
用户消息
   │
   ▼
┌──────────────────────────────────┐
│         Agent 核心循环            │
│                                  │
│  ① RAG 检索知识库文档            │
│  ② 构建 System Prompt（含文档）  │
│  ③ 加载多轮对话历史              │
│  ④ LLM 推理                      │
│     ├─ 需要工具？→ 执行 → 观察   │
│  ⑤ 循环④直到生成最终回复         │
│     └─ 转人工？→ 创建工单        │
└──────────────────────────────────┘
   │              │
   ▼              ▼
 工具层         工单系统
(5个函数)     (SQLite)
```

### 关键设计决策

**1. 为什么用 Function Calling 而不是关键词匹配？**
> 关键词匹配只能处理预定义的问题模式。Function Calling 让 LLM 自己理解用户意图，决定调哪个工具、传什么参数。比如用户说"我那件衣服到哪了"，AI 能理解这是查物流，先调 query_order 找到订单，再调 query_logistics 查物流——这是多步推理，关键词做不到。

**2. RAG 怎么实现的？**
> 没有用重型向量数据库，而是用 TF-IDF + 余弦相似度做轻量检索。把 markdown 格式的政策文档按标题分块，构建索引，查询时取 top-3 相关段落注入 System Prompt。这个方案零依赖、够用，面试时可以讨论如果数据量大了怎么迁移到 embedding + 向量数据库。

**3. 多轮对话怎么管理的？**
> 每次对话生成一个 session_id，所有消息通过 session_id 关联。加载历史时取最近 20 条作为上下文，既保持对话连贯性，又控制 token 消耗。

**4. 转人工为什么要三层？**
> 第一层关键词是安全网——投诉、赔偿等紧急词必须立即转人工，不经过 LLM 避免延迟和风险；第二层是 LLM 自己判断，覆盖关键词没命中的复杂场景；第三层是 API 异常兜底，保证用户不会遇到无响应。

**5. 怎么防止 AI 编造数据？**
> System Prompt 明确要求"优先使用工具查询真实数据，不要编造"。所有订单、物流、商品信息都来自工具调用，退货政策来自 RAG 检索的真实文档。AI 不凭空生成订单号或价格。

---

## 高频面试题 & 参考回答

### Q1: Function Calling 的工作原理是什么？
> 我们把工具的 schema（名称、描述、参数）传给 LLM。LLM 根据用户意图判断是否需要调工具，如果需要就返回一个结构化的 tool_call 对象（包含工具名和 JSON 参数）。我们在后端执行工具，把结果作为 tool 角色消息返回给 LLM，LLM 再根据结果生成最终回复。这就是 ReAct 模式：Reason → Act → Observe → Respond。

### Q2: RAG 和直接微调有什么区别？你为什么选 RAG？
> RAG 是检索增强生成，每次查询时把相关文档片段注入 Prompt，知识是实时的、可更新的。微调是重新训练模型，成本高、更新慢。客服场景的政策文档经常变化，RAG 可以直接改文档就生效，不需要重新训练。而且 RAG 有来源可追溯，答案可以追溯到具体文档段落。

### Q3: 如果要上生产，这个系统还需要做什么？
> - 工具层接入真实业务 API，替换 mock_data
> - TF-IDF 迁移到 embedding + 向量数据库（如 Milvus/Pinecone），提升检索准确率
> - 加认证鉴权和限流，防止 API 被滥用
> - SQLite 换 PostgreSQL，加 Redis 做会话缓存
> - WebSocket 替代轮询，实现客服和用户实时通信
> - 加监控：token 消耗、工具调用成功率、自动解决率、响应时间
> - 加评测体系：构建测试集，评估回答准确率和转人工准确率

### Q4: 怎么评估这个系统的效果？
> 核心指标是自动解决率（AI 独立解决的问题占比），目标 70%+。另外看：转人工准确率（该转的是否转了、不该转的是否误转）、工具调用成功率、平均响应时间、用户满意度。可以构建一个标注测试集，包含各种类型的问题，跑自动化评测。

### Q5: 如果用户问的问题需要多个工具配合怎么办？
> Agent 循环天然支持多步调用。比如"我要买的耳机能退吗"，AI 会先调 query_order 找耳机订单，再调 calculate_return 评估退货，最后结合 RAG 检索的退货政策给用户完整回复。最多支持 5 轮工具调用（MAX_TOOL_ROUNDS），防止无限循环。
