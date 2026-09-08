#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-fire-smart-maturity —— 智慧消防成熟度评估（FIre 消防技能系列，v1.0.1）

定位：主动 Agent。用户给一段单位智慧消防建设现状的自述文本，本引擎做三件事：
  1. 画像识别（场所类型/特征线索）
  2. 六维度成熟度评估：感知接入 / 传输联网 / 平台功能 / 值守运营 / 数据与安全 / 机制闭环
     —— 每个维度的每个要素挂权威出处；材料里"没提到"的要素，主动作为缺口暴露，
        而不是等用户来问（这是"主动"的核心）。
  3. 红线预警：命中违规模式的（平台无人值守、数据不留痕、账号混用、无证上岗、平台停用）置顶。
主动但不骚扰：行动清单封顶 Top 10；单次运行出一份报告，不轮询、不追问。

命令：
  scan <input> [output]   评估并输出 Markdown 报告（缺省打印到 stdout）
  rules                   列出规则基数
  version                 打印版本

退出码：0 = 无红线；1 = 存在红线；2 = 参数/输入错误。

纯标准库，零第三方依赖。报告文件按 UTF-8 + LF 写出。
"""

import json
import os
import re
import sys

ENGINE_VERSION = "1.0.1"
ENGINE_NAME = "check-fire-smart-maturity"

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "resources", "rules.json")

MAX_ACTIONS = 10  # 主动但不骚扰：行动清单封顶


def load_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 规则加载期校验：坏规则在启动时炸，而不是在扫描中静默漏检（check 系列防回归机制）
# ---------------------------------------------------------------------------

def validate_rules(rules):
    seen_ids = set()
    for dim in rules["dimensions"]:
        w = sum(el["weight"] for el in dim["elements"])
        if w != dim["weight"]:
            raise ValueError("维度 %s 要素权重和(%s) != 维度权重(%s)" % (dim["id"], w, dim["weight"]))
        for el in dim["elements"]:
            if el["id"] in seen_ids:
                raise ValueError("要素 ID 重复: %s" % el["id"])
            seen_ids.add(el["id"])
            if not el["citation"]:
                raise ValueError("要素 %s 缺 citation" % el["id"])
    total = sum(d["weight"] for d in rules["dimensions"])
    if total != 100:
        raise ValueError("六维权重和应为 100，实际 %s" % total)


def level_of(index, rules):
    for lv in rules["levels"]:
        if index >= lv["min"]:
            return lv
    return rules["levels"][-1]


def detect_profile(text, rules):
    labels = [p["label"] for p in rules["profile_keywords"] if p["key"] in text]
    hints = []
    for ph in rules["profile_hints"]:
        if re.search(ph["when"], text):
            hints.append(ph["hint"])
    return labels, hints


def scan(text, rules):
    """返回评估结果 dict。"""
    validate_rules(rules)

    # -- 红线 --
    redlines = []
    for rl in rules["redlines"]:
        hits = [p for p in rl["patterns"] if p in text]
        if hits:
            redlines.append({
                "id": rl["id"], "name": rl["name"], "hits": hits,
                "citation": rl["citation"], "why": rl["why"], "next": rl["next"],
            })

    # -- 六维要素命中与评分 --
    dims = []
    total_matched = 0
    gaps = []  # 未覆盖要素 → 主动缺口
    for dim in rules["dimensions"]:
        matched, dim_gaps = [], []
        for el in dim["elements"]:
            hit_terms = [t for t in el["terms"] if t in text]
            if hit_terms:
                matched.append({"el": el, "hit_terms": hit_terms})
                total_matched += el["weight"]
            else:
                dim_gaps.append(el)
        score = int(round(100.0 * sum(m["el"]["weight"] for m in matched) / dim["weight"]))
        dims.append({"dim": dim, "matched": matched, "gaps": dim_gaps, "score": score})
        for el in dim_gaps:
            gaps.append({"dim": dim, "el": el})

    index = int(round(total_matched))  # 六维权重大纲为 100，直接得 0-100 指数
    lv = level_of(index, rules)
    profile_labels, profile_hints = detect_profile(text, rules)

    # -- 主动行动清单：红线优先，其次高优先级缺口，按维度权重排序 --
    actions = []
    for rl in redlines:
        actions.append({"priority": 0, "tag": "红线", "title": rl["name"], "next": rl["next"], "citation": rl["citation"]})
    for g in gaps:
        if g["el"]["priority"] == "高":
            actions.append({"priority": 1, "tag": g["dim"]["name"], "title": g["el"]["name"],
                            "next": g["el"]["next"], "citation": g["el"]["citation"]})
    for g in gaps:
        if g["el"]["priority"] == "中":
            actions.append({"priority": 2, "tag": g["dim"]["name"], "title": g["el"]["name"],
                            "next": g["el"]["next"], "citation": g["el"]["citation"]})
    actions.sort(key=lambda a: a["priority"])
    actions = actions[:MAX_ACTIONS]

    return {
        "profile": profile_labels, "hints": profile_hints,
        "index": index, "level": lv, "dims": dims,
        "redlines": redlines, "gaps": gaps, "actions": actions,
        "element_total": sum(len(d["elements"]) for d in rules["dimensions"]),
        "element_matched": sum(len(d["matched"]) for d in dims),
    }


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

def bar(score, width=10):
    filled = int(round(width * score / 100.0))
    return "█" * filled + "░" * (width - filled)


def render_report(r, rules, source_name):
    lines = []
    ap = lines.append
    ap("# 智慧消防成熟度体检报告")
    ap("")
    ap("> 引擎 %s v%s | FIre 消防技能系列 | 输入文件：%s" % (ENGINE_NAME, ENGINE_VERSION, source_name))
    ap("")
    ap("## 一、单位画像")
    ap("")
    if r["profile"]:
        ap("- 场所特征线索：%s" % "、".join(r["profile"]))
    else:
        ap("- 场所特征线索：未从材料中识别到明确场所类型（一般单位口径评估）")
    if r["hints"]:
        ap("")
        ap("**针对该场所的主动提示**")
        ap("")
        for h in r["hints"]:
            ap("- %s" % h)
    ap("")
    ap("## 二、成熟度总览")
    ap("")
    ap("- 成熟度指数：**%d / 100**（要素覆盖率 %d/%d）" % (r["index"], r["element_matched"], r["element_total"]))
    ap("- 成熟度等级：**%s**" % r["level"]["label"])
    ap("- 等级释义：%s" % r["level"]["desc"])
    ap("")
    ap("| 维度 | 得分 | 图示 | 已覆盖要点 |")
    ap("|---|---|---|---|")
    for d in r["dims"]:
        names = "、".join(m["el"]["name"] for m in d["matched"]) if d["matched"] else "（无）"
        ap("| %s %s（%s） | %d | %s | %s |" % (d["dim"]["id"], d["dim"]["name"], d["dim"]["weight"], d["score"], bar(d["score"]), names))
    ap("")
    ap("## 三、红线预警（%d 条）" % len(r["redlines"]))
    if r["redlines"]:
        ap("")
        for i, rl in enumerate(r["redlines"], 1):
            ap("### 红线 %d：%s" % (i, rl["name"]))
            ap("")
            ap("- 命中表述：%s" % "、".join("「%s」" % h for h in rl["hits"]))
            ap("- 为什么是红线：%s" % rl["why"])
            ap("- 依据：%s" % rl["citation"])
            ap("- 下一步：%s" % rl["next"])
            ap("")
    else:
        ap("")
        ap("未命中红线模式。红线不代表没问题——材料没写到的缺口见下一节。")
        ap("")
    ap("## 四、主动缺口清单（材料中未提及的应建要素）")
    ap("")
    ap("以下要素在你的材料里没有出现。它们不一定是问题——可能确实已建但没写——但按主动评估原则，逐条摆出来并给出依据，请对照确认。")
    ap("")
    if r["gaps"]:
        for d in r["dims"]:
            if not d["gaps"]:
                continue
            ap("### %s %s（本维得分 %d/%d，缺 %d 项）" % (d["dim"]["id"], d["dim"]["name"], d["score"], d["dim"]["weight"], len(d["gaps"])))
            ap("")
            for el in d["gaps"]:
                ap("- **%s**（优先级：%s）" % (el["name"], el["priority"]))
                ap("  - 依据：%s" % el["citation"])
                ap("  - 下一步：%s" % el["next"])
            ap("")
    else:
        ap("六维 30 项要素在材料中全部有对应表述——覆盖完整，建议下一步做真实运行数据核验（报警响应时长、巡检达标率等）。")
        ap("")
    ap("## 五、优先行动清单（Top %d，按红线 > 高优先级缺口排序）" % MAX_ACTIONS)
    ap("")
    if r["actions"]:
        for i, a in enumerate(r["actions"], 1):
            ap("%d. **[%s] %s**：%s" % (i, a["tag"], a["title"], a["next"]))
        ap("")
        ap("清单封顶 %d 条——先做这些，做完再评估下一批（主动但不骚扰）。" % MAX_ACTIONS)
    else:
        ap("当前无待办行动项。")
    ap("")
    ap("## 六、能力边界与免责声明")
    ap("")
    ap("- %s" % rules["disclaimer"])
    ap("- 成熟度等级反映的是材料自述与权威基线的覆盖差距，不预测火灾风险高低，不构成对任何平台的验收结论。")
    ap("")
    return "\n".join(lines)


def print_summary(r):
    print("成熟度指数: %d/100  等级: %s" % (r["index"], r["level"]["label"]))
    print("红线: %d 条  缺口: %d 项  行动清单: %d 条" % (len(r["redlines"]), len(r["gaps"]), len(r["actions"])))
    if r["redlines"]:
        for rl in r["redlines"]:
            print("  [红线] %s" % rl["name"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv):
    if len(argv) < 2:
        print("用法: check.py scan <input> [output] | rules | version", file=sys.stderr)
        return 2
    cmd = argv[1]

    if cmd == "version":
        print("%s %s" % (ENGINE_NAME, ENGINE_VERSION))
        return 0

    rules = load_rules()

    if cmd == "rules":
        n_el = sum(len(d["elements"]) for d in rules["dimensions"])
        print("维度: %d  要素: %d  红线: %d  版本: %s" % (len(rules["dimensions"]), n_el, len(rules["redlines"]), ENGINE_VERSION))
        for d in rules["dimensions"]:
            print("  %s %s (权重%d, %d要素)" % (d["id"], d["name"], d["weight"], len(d["elements"])))
        return 0

    if cmd == "scan":
        if len(argv) < 3:
            print("scan 需要 <input> 路径", file=sys.stderr)
            return 2
        in_path = argv[2]
        out_path = argv[3] if len(argv) > 3 else None
        if not os.path.isfile(in_path):
            print("输入文件不存在: %s" % in_path, file=sys.stderr)
            return 2
        if os.path.getsize(in_path) > 8 * 1024 * 1024:
            print("输入超过 8MB 上限", file=sys.stderr)
            return 2
        with open(in_path, encoding="utf-8") as f:
            text = f.read()
        if not text.strip():
            print("输入为空", file=sys.stderr)
            return 2

        r = scan(text, rules)
        report = render_report(r, rules, os.path.basename(in_path))

        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            print("报告已写入: %s" % out_path)
        else:
            print(report)

        print_summary(r)
        return 1 if r["redlines"] else 0

    print("未知命令: %s" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
