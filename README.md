# 🤖 AI 智能客服工单系统

> 基于大语言模型的企业级智能客服系统，自动处理 70%+ 重复性咨询，复杂问题智能转人工。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Gradio](https://img.shields.io/badge/Gradio-4.44-F37425.svg)](https://www.gradio.app/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-4D6BFE.svg)](https://www.deepseek.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

## 📖 项目简介

本项目是一个面向企业客服团队的 AI 智能客服工单系统。用户通过网页端咨询问题，AI 自动回答查订单、查物流、退货政策、产品咨询等常见问题；遇到投诉、退款等 AI 无法处理的复杂问题，系统自动生成工单并转接人工客服。

**核心业务价值**：替代客服团队大量重复性问答工作，目标自动解决率 70% 以上，让人工客服专注于复杂和高价值的问题。

## ✨ 核心功能

| 功能模块 | 说明 |
|---------|------|
| 🤖 AI 智能对话 | 基于 DeepSeek 大模型，亲切自然地回答用户问题 |
| 🔄 智能转人工 | 关键词 + AI 双层判断，自动识别投诉/退款等复杂问题 |
| 🎫 工单管理 | 自动创建工单，支持紧急程度分级、状态流转、实时刷新 |
| 💬 对话记录 | 所有对话自动持久化存储，支持后续分析和审计 |
| 📊 统计面板 | 工单状态一目了然（待处理/处理中/已完成） |
| 🐳 Docker 部署 | 一键容器化部署，开箱即用 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│                    用户浏览器                      │
│         Gradio UI (localhost:7860)               │
├─────────────────────────────────────────────────┤
│  📑 客服对话页          │    📋 工单管理页         │
│  - 聊天窗口             │    - 工单列表            │
│  - 快捷问题             │    - 状态流转            │
│  - 实时回复             │    - 自动刷新            │
└──────────┬──────────────────────┬───────────────┘
           │                      │
           ▼                      ▼
┌─────────────────────────────────────────────────┐
│           FastAPI 后端 (localhost:8000)          │
│                                                  │
│   POST /chat          GET /tickets               │
│   PUT /tickets/{id}   Swagger /docs              │
└──────────┬──────────────────────┬───────────────┘
           │                      │
           ▼                      ▼
┌────────────────────┐   ┌────────────────────┐
│  customer_service  │   │   ticket_manager   │
│     _agent.py      │   │    .py             │
│  ┌──────────────┐  │   │  - 关键词检测      │
│  │ DeepSeek API │  │   │  - 紧急度判断      │
│  │  (LLM 调用)  │  │   │  - 工单创建        │
│  └──────────────┘  │   └────────────────────┘
│  - System Prompt   │
│  - 转人工判断逻辑   │
└──────────┬─────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│              db.py (SQLite)                      │
│                                                  │
│   tickets 表          conversations 表           │
│   - id                - id                       │
│   - summary           - user_message             │
│   - priority          - ai_reply                 │
│   - status            - created_at               │
│   - created_at                                   │
└─────────────────────────────────────────────────┘
```

## 🧠 转人工机制（三层兜底）

```
用户消息
   │
   ├─① 关键词命中？──→ 投诉/退款/赔偿/转人工/315...
   │                      │
   │                   立即创建工单
   │
   ├─② AI 主动判断？──→ DeepSeek 返回 [NEED_HUMAN] 标记
   │                      │
   │                   创建工单（含 AI 初步分析）
   │
   └─③ API 异常？────→ 网络错误/限流/服务不可用
                          │
                       兜底创建工单
```

工单紧急程度自动分级：
- 🔴 **urgent（紧急）**：涉及投诉、赔偿、律师、315、举报
- 🟡 **normal（普通）**：其他转人工场景

## 📁 项目结构

```
ai-customer-service/
├── .env.example                # 环境变量模板
├── .env                        # DeepSeek API 配置（需自行填入）
├── requirements.txt            # Python 依赖
├── db.py                       # SQLite 数据库操作
├── ticket_manager.py           # 工单管理（关键词检测、创建工单）
├── customer_service_agent.py   # 核心客服 Agent（调用 DeepSeek）
├── api_server.py               # FastAPI 后端（3 个 RESTful 接口）
├── ui.py                       # Gradio 前端（对话 + 工单管理）
├── Dockerfile                  # 容器化部署
└── README.md                   # 项目文档
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/)）

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/ai-customer-service.git
cd ai-customer-service
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
cp .env.example .env
```

编辑 `.env`：
```
DEEPSEEK_API_KEY=sk-你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 4. 启动服务

**方式一：本地运行**

```bash
# 终端 1：启动 FastAPI 后端
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：启动 Gradio 前端
python ui.py
```

- 前端界面：http://localhost:7860
- API 文档（Swagger）：http://localhost:8000/docs

**方式二：Docker 部署**

```bash
docker build -t ai-customer-service .
docker run -p 8000:8000 -p 7860:7860 --env-file .env ai-customer-service
```

## 🔌 API 接口文档

启动后访问 http://localhost:8000/docs 查看交互式 Swagger 文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | 发送消息，返回 AI 回复（自动判断是否转人工） |
| `GET` | `/tickets` | 查询所有工单（按时间倒序） |
| `PUT` | `/tickets/{id}` | 更新工单状态（pending/processing/done） |

### 请求/响应示例

**POST /chat**
```json
// Request
{ "message": "我的订单什么时候发货？" }

// Response（AI 正常回答）
{
  "reply": "您好！您的订单 #20260819 已发货，预计明天送达～",
  "need_human": false,
  "ticket_id": null,
  "priority": null
}

// Response（触发转人工）
{
  "reply": "已为您转接人工客服，客服人员会尽快与您联系～",
  "need_human": true,
  "ticket_id": 3,
  "priority": "urgent"
}
```

**GET /tickets**
```json
{
  "total": 2,
  "tickets": [
    {
      "id": 2,
      "summary": "用户请求人工处理：我要退款！商品有质量问题",
      "priority": "urgent",
      "status": "pending",
      "created_at": "2026-08-19 10:30:00"
    }
  ]
}
```

## 🛠️ 技术栈

| 层面 | 技术选型 | 说明 |
|------|---------|------|
| 后端框架 | FastAPI | 高性能异步框架，自动生成 API 文档 |
| 前端界面 | Gradio | 快速构建 ML/AI 应用界面，支持实时刷新 |
| 大模型 | DeepSeek API | 国产大模型，兼容 OpenAI SDK，性价比高 |
| 数据库 | SQLite | 轻量级，零配置，适合中小规模部署 |
| 容器化 | Docker | 一键部署，环境隔离 |
| 语言 | Python 3.10+ | 全栈统一语言 |

## 🔮 后续优化方向

- [ ] 接入真实订单/物流 API，通过 Function Calling 实现真实查询
- [ ] 支持多轮对话上下文记忆
- [ ] 增加用户身份认证和权限管理
- [ ] 引入 Redis 做会话缓存和工单消息队列
- [ ] 数据库迁移至 PostgreSQL，支持高并发
- [ ] 增加客服工作台（WebSocket 实时通信）
- [ ] 对接飞书/钉钉/企微推送工单通知
- [ ] 增加数据统计看板（自动解决率、响应时间、工单趋势）

## 📄 License

MIT License
