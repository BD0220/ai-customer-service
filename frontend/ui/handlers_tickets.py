"""工单管理页回调：列表刷新、状态流转。"""

from db import get_all_tickets, update_ticket_status, get_ticket_stats


def refresh_tickets():
    tickets = get_all_tickets()
    stats = get_ticket_stats()

    rows = []
    for t in tickets:
        sm = {"pending": "⏳ 待处理", "processing": "🔄 处理中", "done": "✅ 已完成"}
        pm = {"normal": "🟡 普通", "urgent": "🔴 紧急"}
        rows.append([
            t["id"],
            t["summary"][:80] + ("..." if len(t["summary"]) > 80 else ""),
            pm.get(t["priority"], t["priority"]),
            sm.get(t["status"], t["status"]),
            (t.get("session_id") or "-")[:16],
            t["created_at"],
        ])

    stats_text = (
        f"📊 **工单统计：** 总计 {stats['total']} | "
        f"⏳ 待处理 {stats['pending']} | "
        f"🔄 处理中 {stats['processing']} | "
        f"✅ 已完成 {stats['done']} | "
        f"🔴 紧急 {stats['urgent']}"
    )
    return rows, stats_text, stats


def mark_processing(tid_str):
    if not tid_str:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 请先输入工单号"
    try:
        tid = int(tid_str)
    except ValueError:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "processing")
    msg = f"✅ 工单 #{tid} → 处理中" if ok else f"❌ 工单 #{tid} 不存在"
    r, s, _ = refresh_tickets()
    return r, s, msg


def mark_done(tid_str):
    if not tid_str:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 请先输入工单号"
    try:
        tid = int(tid_str)
    except ValueError:
        r, s, _ = refresh_tickets()
        return r, s, "⚠️ 工单号必须是数字"
    ok = update_ticket_status(tid, "done")
    msg = f"✅ 工单 #{tid} → 已完成" if ok else f"❌ 工单 #{tid} 不存在"
    r, s, _ = refresh_tickets()
    return r, s, msg
