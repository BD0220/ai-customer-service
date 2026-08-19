"""
数据库操作模块
使用 SQLite 存储工单和对话记录
"""

import sqlite3
import os
from datetime import datetime

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "customer_service.db")


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果可以通过列名访问
    return conn


def init_db():
    """
    初始化数据库，创建两张表：
    - tickets：工单表
    - conversations：对话记录表
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 创建工单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,              -- 用户问题摘要
            priority TEXT NOT NULL DEFAULT 'normal',  -- 紧急程度：normal / urgent
            status TEXT NOT NULL DEFAULT 'pending',   -- 状态：pending / processing / done
            created_at TEXT NOT NULL            -- 创建时间
        )
    """)

    # 创建对话记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,         -- 用户消息
            ai_reply TEXT NOT NULL,             -- AI 回复
            created_at TEXT NOT NULL            -- 创建时间
        )
    """)

    conn.commit()
    conn.close()
    print("[数据库] 初始化完成")


def save_conversation(user_message: str, ai_reply: str) -> int:
    """
    保存一条对话记录到 conversations 表

    Args:
        user_message: 用户发送的消息
        ai_reply: AI 的回复内容

    Returns:
        新插入记录的 ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO conversations (user_message, ai_reply, created_at) VALUES (?, ?, ?)",
        (user_message, ai_reply, now),
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id


def create_ticket_record(summary: str, priority: str = "normal") -> int:
    """
    创建一条工单记录到 tickets 表

    Args:
        summary: 用户问题摘要
        priority: 紧急程度，normal 或 urgent

    Returns:
        新创建工单的 ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO tickets (summary, priority, status, created_at) VALUES (?, ?, 'pending', ?)",
        (summary, priority, now),
    )
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()
    print(f"[数据库] 工单 #{ticket_id} 已创建：{summary}")
    return ticket_id


def get_all_tickets() -> list:
    """
    查询所有工单，按创建时间倒序排列（最新的在最前面）

    Returns:
        工单列表，每个工单是一个字典
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    # 将 Row 对象转为字典列表
    return [dict(row) for row in rows]


def update_ticket_status(ticket_id: int, status: str) -> bool:
    """
    更新工单状态

    Args:
        ticket_id: 工单 ID
        status: 新状态（pending / processing / done）

    Returns:
        是否更新成功
    """
    valid_status = ("pending", "processing", "done")
    if status not in valid_status:
        print(f"[数据库] 无效状态：{status}")
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

    if affected > 0:
        print(f"[数据库] 工单 #{ticket_id} 状态更新为：{status}")
        return True
    else:
        print(f"[数据库] 未找到工单 #{ticket_id}")
        return False


# 模块导入时自动初始化数据库
init_db()
