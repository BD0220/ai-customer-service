# -*- coding: utf-8 -*-
"""
评测集跑批脚本
用法（在项目根目录）：
  .venv/Scripts/python.exe eval/run_eval.py

指标：
  1. 转人工判定准确率：need_human 预测 == 标注
  2. 工具调用准确率：实际调用命中 allowed_tools；allowed 为空时不调业务工具
  3. 自动处理率：标注 expect_human=False 的用例中实际未转人工的比例
  4. 答案质量：must 关键词全中率 / forbidden 违规数
"""
import json
import logging
import os
import sys
import time
import uuid
from collections import Counter

# 确保在项目根运行（读 .env / import 模块）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

logging.basicConfig(level=logging.ERROR, format="%(levelname)s %(message)s")

from customer_service_agent import chat  # noqa: E402
from eval.cases import CASES  # noqa: E402

BUSINESS_TOOLS = {"query_order", "query_logistics", "query_product", "calculate_return"}


def run_one(c):
    """执行单条用例，返回判定结果字典。"""
    session_id = uuid.uuid4().hex[:8]
    t0 = time.time()
    try:
        r = chat(c["message"], session_id=session_id)
    except Exception as e:  # 任何异常都记失败，不中断整批
        return {"case": c, "error": f"{type(e).__name__}: {e}", "elapsed": round(time.time() - t0, 1)}

    reply = r.get("reply", "")
    pred_human = bool(r.get("need_human"))
    tools_called = {t.get("tool") for t in (r.get("tool_trace") or []) if t.get("tool")}

    # 1) 转人工判定
    human_ok = pred_human == c["expect_human"]

    # 2) 工具调用
    allowed = set(c.get("allowed_tools") or [])
    if c.get("tool_skip"):
        tool_ok = "N/A"
        tool_detail = "跳过工具打分"
    elif allowed:
        hit = tools_called & allowed
        tool_ok = bool(hit)
        tool_detail = f"调用={sorted(tools_called)} 期望命中{allowed} → {'✓' if tool_ok else '✗'}"
    else:
        misuse = tools_called & BUSINESS_TOOLS
        tool_ok = not misuse
        tool_detail = f"调用={sorted(tools_called)} 期望无业务工具 → {'✓' if tool_ok else ('✗ 误调 ' + str(sorted(misuse))) if misuse else ''}"

    # 3) 答案质量
    must = c.get("must") or []
    miss = [w for w in must if w not in reply]
    must_ok = not miss
    forbidden = c.get("forbidden") or []
    hits = [w for w in forbidden if w in reply]
    forbid_violation = bool(hits)

    return {
        "case": c, "reply": reply, "pred_human": pred_human,
        "human_ok": human_ok, "tool_ok": tool_ok, "tool_detail": tool_detail,
        "must_ok": must_ok, "miss": miss, "forbid_violation": forbid_violation,
        "hits": hits, "elapsed": round(time.time() - t0, 1),
        "need_human": pred_human, "ticket": r.get("ticket_id"),
    }


def main():
    print(f"开始跑批：{len(CASES)} 条用例，预计 {len(CASES) * 8}-{len(CASES) * 20} 秒，请耐心等待\n", flush=True)
    results = []
    for i, c in enumerate(CASES, 1):
        res = run_one(c)
        results.append(res)
        mark = "OK " if res.get("error") is None and res.get("human_ok") and res.get("tool_ok") is not False else "!! "
        print(f"[{i:02d}/{len(CASES)}] {mark} {c['id']} {c['category']} | human={res.get('pred_human')}(期望{c['expect_human']}) | 耗时{res.get('elapsed')}s", flush=True)
        if res.get("error"):
            print(f"      ERROR: {res['error']}", flush=True)

    # ---- 汇总指标 ----
    ok = [r for r in results if r.get("error") is None]
    human_ok = sum(1 for r in ok if r["human_ok"])
    auto_cases = [r for r in ok if not r["case"]["expect_human"]]
    auto_ok = sum(1 for r in auto_cases if not r["pred_human"])
    tool_judged = [r for r in ok if r["tool_ok"] != "N/A"]
    tool_ok = sum(1 for r in tool_judged if r["tool_ok"])
    must_cases = [r for r in ok if r["case"].get("must")]
    must_ok = sum(1 for r in must_cases if r["must_ok"])
    forbid_bad = [r for r in ok if r["forbid_violation"]]
    fails = [r for r in ok if not r["human_ok"] or r["tool_ok"] is False or r["forbid_violation"]]

    def pct(a, b):
        return f"{a}/{b} = {a / b * 100:.1f}%" if b else "N/A"

    print("\n" + "=" * 60)
    print("评测结果汇总")
    print("=" * 60)
    print(f"总用例            : {len(CASES)}（成功 {len(ok)}，异常 {len(CASES) - len(ok)}）")
    print(f"① 转人工判定准确率 : {pct(human_ok, len(ok))}")
    print(f"② 工具调用准确率   : {pct(tool_ok, len(tool_judged))}")
    print(f"③ 自动处理率       : {pct(auto_ok, len(auto_cases))}（期望不转人工的 {len(auto_cases)} 条中实际未转人工）")
    print(f"④ must 关键词命中  : {pct(must_ok, len(must_cases))}")
    print(f"⑤ forbidden 违规   : {len(forbid_bad)} 条")
    if fails:
        print("\n失败 / 待人工复查用例：")
        for r in fails:
            reasons = []
            if not r["human_ok"]:
                reasons.append(f"转人工判定错(实际{'转' if r['pred_human'] else '不转'})")
            if r["tool_ok"] is False:
                reasons.append("工具调用错")
            if r["forbid_violation"]:
                reasons.append(f"禁区词 {r['hits']}")
            if r["miss"]:
                reasons.append(f"缺关键词 {r['miss']}")
            print(f"  {r['case']['id']} [{r['case']['category']}] {r['case']['message'][:40]}")
            print(f"      {'; '.join(reasons)} | tool_detail: {r['tool_detail']}")
            print(f"      回复: {r['reply'][:150]}")

    # ---- 写报告 ----
    out_dir = os.path.join(PROJECT_ROOT, "eval", "results")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, time.strftime("eval_report_%Y%m%d_%H%M%S.md"))
    lines = [
        "# AI 客服 Agent 评测报告",
        "",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 用例数：{len(CASES)}，成功 {len(ok)}，异常 {len(CASES) - len(ok)}",
        f"- ① 转人工判定准确率：{pct(human_ok, len(ok))}",
        f"- ② 工具调用准确率：{pct(tool_ok, len(tool_judged))}",
        f"- ③ 自动处理率：{pct(auto_ok, len(auto_cases))}",
        f"- ④ must 关键词命中：{pct(must_ok, len(must_cases))}",
        f"- ⑤ forbidden 违规：{len(forbid_bad)} 条",
        "",
        "## 逐条明细",
        "",
        "| id | 类别 | 输入 | 期望human | 实际human | 工具 | must | 备注 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r['case']['id']} | {r['case']['category']} | {r['case']['message'][:30]} | - | ERROR | - | - | {r['error'][:60]} |")
            continue
        c = r["case"]
        tmark = "✓" if r["tool_ok"] is True else ("N/A" if r["tool_ok"] == "N/A" else "✗")
        mmark = "✓" if r["must_ok"] else f"缺{r['miss']}"
        fm = f"⚠禁区{r['hits']}" if r["forbid_violation"] else ""
        hmark = "✓" if r["human_ok"] else "✗"
        lines.append(
            f"| {c['id']} | {c['category']} | {c['message'][:34]} | {c['expect_human']} | "
            f"{r['pred_human']}{hmark} | {tmark} | {mmark} | {fm}{c.get('note','')[:24]} |"
        )
    lines += ["", "## 备注", "", "- 自动处理率口径：期望 need_human=False 的用例中，实际未转人工的比例。"]
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n报告已写入: {report_path}")
    return report_path


if __name__ == "__main__":
    main()
