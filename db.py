"""
数据库操作模块（升级版）
使用 SQLite 存储工单、对话记录和会话信息。
支持多轮对话的 session 管理。
"""

import sqlite3
import os
import json
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 数据库文件路径：默认 data/ 目录（运行数据与源码分离），CS_DB_PATH 可覆盖
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.environ.get(
    "CS_DB_PATH",
    os.path.join(_DATA_DIR, "customer_service.db"),
)


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库，创建三张表：
    - sessions：会话表（管理多轮对话）
    - tickets：工单表
    - conversations：对话记录表（含工具调用追踪）
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 会话表：每个用户一个活跃会话
    # mode：本会话当前由谁应答 —— ai（Agent 应答）/ human（人工接管，AI 闭嘴）/ closed（已结束）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'U10086',
            status TEXT NOT NULL DEFAULT 'active',
            mode TEXT NOT NULL DEFAULT 'ai',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 旧库迁移：建表时没有 mode 列的话补上（ALTER 不会破坏已有数据）
    cursor.execute("PRAGMA table_info(sessions)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "mode" not in existing_cols:
        cursor.execute(
            "ALTER TABLE sessions ADD COLUMN mode TEXT NOT NULL DEFAULT 'ai'"
        )
        logger.info("sessions 表迁移完成：新增 mode 列（默认 'ai'）")

    # 工单表：增加 session_id 关联
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            summary TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'pending',
            user_id TEXT NOT NULL DEFAULT 'U10086',
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    # 对话记录表：增加工具调用追踪
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT,
            tool_results TEXT,
            tokens_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("数据库初始化完成（sessions / tickets / conversations）")


# ========== 会话管理 ==========

def create_session(session_id: str, user_id: str = "U10086") -> str:
    """创建新会话"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT OR IGNORE INTO sessions (session_id, user_id, status, created_at, updated_at) VALUES (?, ?, 'active', ?, ?)",
        (session_id, user_id, now, now),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> dict | None:
    """获取会话信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def touch_session(session_id: str):
    """更新会话的最后活跃时间"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
        (now, session_id),
    )
    conn.commit()
    conn.close()


VALID_SESSION_MODES = ("ai", "human", "closed")


def set_session_mode(session_id: str, mode: str) -> bool:
    """切换会话的应答方。

    - ai:    Agent 应答（默认）
    - human: 人工接管，Agent 入口直接短路，不再消耗 LLM 调用
    - closed: 会话结束

    转人工的三条路径（关键词兜底 / Agent 调工具 / 超轮与异常）都汇聚在
    ticket_manager.create_ticket()，由它统一调本函数置为 human ——
    "建工单 = 自动接管" 的语义只实现这一处。
    """
    if mode not in VALID_SESSION_MODES:
        logger.warning(f"无效的会话模式：{mode}")
        return False

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE sessions SET mode = ?, updated_at = ? WHERE session_id = ?",
        (mode, now, session_id),
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected:
        logger.info(f"会话 {session_id} 模式 → {mode}")
    return affected > 0


def list_open_sessions(limit: int = 50) -> list[dict]:
    """坐席工作台用的会话列表：全部未关闭会话，带最后一条消息和未结工单数。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.session_id, s.user_id, s.status, s.mode, s.created_at, s.updated_at,
               (SELECT content FROM conversations c
                 WHERE c.session_id = s.session_id
                 ORDER BY c.id DESC LIMIT 1) AS last_message,
               (SELECT COUNT(*) FROM tickets t
                 WHERE t.session_id = s.session_id AND t.status != 'done') AS open_tickets,
               (SELECT MAX(t.id) FROM tickets t
                 WHERE t.session_id = s.session_id AND t.status != 'done') AS open_ticket_id
        FROM sessions s
        WHERE s.mode IN ('ai', 'human')
        ORDER BY s.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_messages(session_id: str, limit: int = 100) -> list[dict]:
    """原始消息流（含人工坐席的回复），给工作台 / 用户侧轮询渲染用。

    注意与 get_conversation_history 的区别：那个是喂给 LLM 的上下文
    （会把 agent 角色映射成 assistant），这里保留原样。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT role, content, created_at
           FROM conversations
           WHERE session_id = ?
           ORDER BY id DESC LIMIT ?""",
        (session_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
        for r in reversed(rows)
    ]


# ========== 对话记录 ==========

def save_conversation(
    session_id: str,
    role: str,
    content: str,
    tool_calls: list = None,
    tool_results: list = None,
    tokens_used: int = 0,
) -> int:
    """
    保存一条对话记录。

    Args:
        session_id: 会话 ID
        role: 角色（user / assistant / tool）
        content: 消息内容
        tool_calls: AI 请求调用的工具列表（JSON 可序列化）
        tool_results: 工具执行结果列表
        tokens_used: 本次调用消耗的 token 数
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """INSERT INTO conversations
           (session_id, role, content, tool_calls, tool_results, tokens_used, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            role,
            content,
            json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            json.dumps(tool_results, ensure_ascii=False) if tool_results else None,
            tokens_used,
            now,
        ),
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id


def get_conversation_history(session_id: str, limit: int = 20) -> list[dict]:
    """
    获取会话的历史消息，用于构建多轮对话上下文。
    返回 OpenAI 消息格式的列表。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT role, content, tool_calls, tool_results
           FROM conversations
           WHERE session_id = ?
           ORDER BY id DESC LIMIT ?""",
        (session_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    # 倒序取出后反转为正序。
    # 人工坐席的回复（role="agent"）也属于"客服说过的话"，映射回 assistant
    # 并加前缀标注——否则 OpenAI 协议不认识 "agent" 角色，会直接报错；
    # 加前缀是为了让 AI 交还后知道这段话是人工说的，衔接上下文。
    messages = []
    for row in reversed(rows):
        role = row["role"]
        content = row["content"]
        if role == "agent":
            role = "assistant"
            content = f"（人工客服的回复）：{content}"
        messages.append({
            "role": role,
            "content": content,
        })
    return messages


# ========== 工单操作 ==========

def create_ticket_record(
    summary: str,
    priority: str = "normal",
    session_id: str = None,
    user_id: str = "U10086",
) -> int:
    """创建一条工单记录"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """INSERT INTO tickets (session_id, summary, priority, status, user_id, created_at)
           VALUES (?, ?, ?, 'pending', ?, ?)""",
        (session_id, summary, priority, user_id, now),
    )
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()
    logger.info(f"工单 #{ticket_id} 已创建：{summary[:50]}")
    return ticket_id


def get_all_tickets() -> list[dict]:
    """查询所有工单，按创建时间倒序"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, s.session_id as sid
        FROM tickets t
        LEFT JOIN sessions s ON t.session_id = s.session_id
        ORDER BY t.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_ticket_status(ticket_id: int, status: str) -> bool:
    """更新工单状态"""
    valid_status = ("pending", "processing", "done")
    if status not in valid_status:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tickets SET status = ? WHERE id = ?",
        (status, ticket_id),
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def get_ticket_stats() -> dict:
    """获取工单统计数据"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent
        FROM tickets
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"total": 0, "pending": 0, "processing": 0, "done": 0, "urgent": 0}


# 模块导入时自动初始化数据库
init_db()
