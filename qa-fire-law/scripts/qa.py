#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa-fire-law —— 消防法规问答（主动 Agent 版，FIre 系列技能 #6）

FIre 系列首个 qa 范式。三条铁律：
1) 有出处才回答：每条答案都带权威出处（法律/规章/标准条款），核实于 2026-09-06；
2) 未覆盖就承认：匹配分不足时不硬答，给出主题建议与兜底渠道——宁可留白不可错配；
3) 回答带延伸：一次问答附带 2-3 条相关问答入口，用户可能没意识到该问什么——主动但不骚扰。

用法：
  python qa.py ask <问题> [output.md]   # 问答（exit 0 已回答 / 1 未覆盖 / 2 参数错误）
  python qa.py list                     # 知识库主题清单
  python qa.py version                  # 版本与知识库基数
"""
import json
import os
import re
import sys

ENGINE_VERSION = "1.0.1"

HERE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(HERE, os.pardir, "resources", "kb.json")

MIN_SCORE = 4
MAX_RELATED = 3

DISCLAIMER = (
    "> 免责声明：本回答基于公开现行法规文本整理（核实于 2026-09-06），仅供管理参考，"
    "不构成法律意见；法规修订后以官方最新公布文本为准；具体执行口径以当地消防救援机构意见为准。"
)


def load_kb():
    with open(KB_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _validate(data)
    return data


def _validate(data):
    seen = set()
    for e in data["entries"]:
        eid = e.get("id", "")
        if not eid or eid in seen:
            raise ValueError("条目 ID 缺失或重复: %r" % eid)
        seen.add(eid)
        for key in ("category", "question", "keywords", "answer", "citations"):
            if not e.get(key):
                raise ValueError("条目 %s 缺少字段 %s" % (eid, key))


def normalize(s):
    s = re.sub(r"\s+", "", s)
    return re.sub(r"[，。？！、：；,.?!:;\"'“”‘’（）()【】\[\]]", "", s)


def score_entry(query, entry):
    """匹配分 = 命中关键词长度之和；另记命中词数与最长命中词长。"""
    total, hits = 0, []
    for kw in entry["keywords"]:
        if kw in query:
            total += len(kw)
            hits.append(kw)
    return total, hits


def is_eligible(score, hits):
    """两级判定：单个长词（>=3 字）强命中，或两个以上短词组合且总分>=4。
    单个 2 字词命中不答——宁可留白不可错配。"""
    if not hits:
        return False
    max_len = max(len(k) for k in hits)
    return max_len >= 3 or (len(hits) >= 2 and score >= 4)


def answer_report(query, kb):
    flat = normalize(query)
    scored = []
    for e in kb["entries"]:
        sc, hits = score_entry(flat, e)
        if sc > 0:
            scored.append((sc, len(hits), e, hits))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["id"]))

    lines = []
    ap = lines.append
    ap("# 消防法规问答（主动 Agent 版 v%s）" % ENGINE_VERSION)
    ap("")
    ap("> 出自 FIre 消防技能系列 · 免费使用")
    ap("")
    ap("**问题**：%s" % query.strip())
    ap("")

    best = scored[0] if scored else None
    if best and is_eligible(best[0], best[3]):
        _, _, e, hits = best
        ap("## 回答")
        ap("")
        ap(e["answer"])
        ap("")
        ap("### 出处")
        ap("")
        for c in e["citations"]:
            ap("- %s" % c)
        ap("")
        related = [(sc, e2) for sc, _, e2, _ in scored[1:MAX_RELATED + 1] if sc >= 2]
        if related:
            ap("### 相关问答（可能也是你想问的）")
            ap("")
            for sc, e2 in related:
                ap("- %s（主题：%s）" % (e2["question"], e2["category"]))
            ap("")
        ap("---")
        ap("")
        ap(DISCLAIMER)
        return "\n".join(lines), 0, e["question"]

    # 未覆盖：诚实兜底
    ap("## 暂未覆盖这个问题")
    ap("")
    ap(kb["fallback"]["text"])
    ap("")
    if scored:
        ap("### 最接近的主题（可能是你要问的）")
        ap("")
        for sc, _, e2, hits in scored[:2]:
            ap("- %s（主题：%s；命中词：%s）" % (e2["question"], e2["category"], "、".join(hits[:3])))
        ap("")
    ap("### 知识库已覆盖的主题")
    ap("")
    cats = {}
    for e2 in kb["entries"]:
        cats.setdefault(e2["category"], []).append(e2["question"])
    for cat, qs in cats.items():
        ap("- **%s**：%s" % (cat, " / ".join(qs[:3]) + ("…" if len(qs) > 3 else "")))
    ap("")
    ap("---")
    ap("")
    ap(DISCLAIMER)
    return "\n".join(lines), 1, None


def list_categories(kb):
    cats = {}
    for e in kb["entries"]:
        cats.setdefault(e["category"], []).append(e["question"])
    out = ["消防法规问答知识库（v%s）" % ENGINE_VERSION, ""]
    for cat, qs in cats.items():
        out.append("【%s】%d 条" % (cat, len(qs)))
        for q in qs:
            out.append("  - %s" % q)
        out.append("")
    return "\n".join(out), 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "version":
        kb = load_kb()
        cats = sorted({e["category"] for e in kb["entries"]})
        print("qa-fire-law %s (FIre 系列技能 #6)" % ENGINE_VERSION)
        print("知识库基数: %d 条 / %d 个主题（每条含出处）" % (len(kb["entries"]), len(cats)))
        return 0
    if len(argv) >= 2 and argv[1] == "list":
        kb = load_kb()
        text, rc = list_categories(kb)
        print(text)
        return rc
    if len(argv) < 3 or argv[1] != "ask":
        sys.stderr.write(__doc__ or "")
        return 2
    query = argv[2]
    out = argv[3] if len(argv) > 3 else None
    if os.path.isfile(query):
        # 支持 ask <input.txt> <output.md>：从文件读问题
        with open(query, encoding="utf-8") as f:
            query = f.read().strip()
    if not query.strip():
        sys.stderr.write("问题为空\n")
        return 2
    kb = load_kb()
    report, rc, matched = answer_report(query, kb)
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(report)
    if matched:
        print("已回答：%s" % matched)
    else:
        print("未覆盖（已给出兜底与主题建议）")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
