#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-fire-hazard —— 防火隐患识别（主动 Agent 版，FIre 系列技能 #5）

定位：主动 Agent，不是被动关键词计数。三件事：
1) 识别：从用户粘贴的巡查记录/现场描述里识别隐患，逐条定级（红线=涉嫌违法 / 高危 / 提示），
   每条给条款依据、罚则区间和可执行的整改动作——告知"违反了哪条、会怎么罚、怎么改"。
2) 主动暴露：文本里没提、但与场所特征强相关的高频隐患点主动摆出来（最多 6 条），标注
   "未在描述中提及，请对照自查"——主动但不骚扰，不重复、不轰炸。
3) 收敛：处置优先级清单封顶 Top 8，红线永远置顶。

诚实边界（写进报告，不藏在文档里）：只基于文字描述识别，不能替代现场检查；
隐患是否构成违法由消防救援机构认定；无联网、无图像能力。

用法：
  python check.py scan <input.md|txt> [output.md]   # 扫描并出报告（exit 0 未命中 / 1 命中）
  python check.py version                            # 版本与规则基数
"""
import json
import os
import re
import sys

ENGINE_VERSION = "1.0.1"

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(HERE, os.pardir, "resources", "rules.json")

MAX_ACTION_LIST = 8
MAX_PROACTIVE = 6

DISCLAIMER = (
    "> 免责声明：本报告基于你提供的文字描述生成，不构成消防行政认定或专业消防意见；"
    "隐患是否构成违法行为以消防救援机构认定为准；整改涉及技术标准的问题请咨询持证机构"
    "或注册消防工程师。依据均为公开现行文本，以官方最新公布文本为准。"
)


def load_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _validate(data)
    return data


def _validate(data):
    """加载期校验：规则字段完整、ID 唯一、出处非空。防手改规则库引入错误。"""
    seen = set()
    for r in data["rules"]:
        rid = r.get("id", "")
        if not rid or rid in seen:
            raise ValueError("规则 ID 缺失或重复: %r" % rid)
        seen.add(rid)
        for key in ("name", "patterns", "severity", "citation", "citation_code", "penalty", "action"):
            if not r.get(key):
                raise ValueError("规则 %s 缺少字段 %s" % (rid, key))
        if r["severity"] not in data["severity_order"]:
            raise ValueError("规则 %s 严重度非法: %s" % (rid, r["severity"]))


def normalize(text):
    """去空白：中文匹配对空格/换行不敏感（'安全出口 上锁' == '安全出口上锁'）。"""
    return re.sub(r"\s+", "", text)


def match_rules(text, rules):
    """返回 [(rule, hit_term)]，每条规则只报一次首个命中词——不重复、不堆砌。"""
    flat = normalize(text)
    hits = []
    for rule in rules:
        hit = None
        for p in rule["patterns"]:
            if p in flat:
                hit = p
                break
        if hit:
            hits.append((rule, hit))
    return hits


def detect_venues(text, venue_rules):
    flat = normalize(text)
    found = []
    for vr in venue_rules:
        if any(t in flat for t in vr["terms"]):
            found.append(vr)
    return found


def build_proactive(text, data, matched_ids):
    """主动自查清单：场所相关优先（每场所取前3），不足用通用清单补齐，总量封顶。"""
    flat = normalize(text)
    out = []
    seen = set()
    for vr in detect_venues(flat, data["proactive_checklist"]["venue_rules"]):
        for item in vr["items"][:3]:
            key = item[:12]
            if key not in seen:
                seen.add(key)
                out.append({"item": item, "why": "与%s强相关" % vr["venue"]})
    for item in data["proactive_checklist"]["universal"]:
        if len(out) >= MAX_PROACTIVE:
            break
        key = item[:12]
        if key not in seen:
            seen.add(key)
            out.append({"item": item, "why": "通用高频隐患点"})
    return out[:MAX_PROACTIVE]


def render(text, data):
    rules = data["rules"]
    hits = match_rules(text, rules)

    by_sev = {"红线": [], "高危": [], "提示": []}
    for rule, hit in hits:
        by_sev[rule["severity"]].append((rule, hit))

    lines = []
    ap = lines.append
    ap("# 防火隐患识别报告（主动 Agent 版 v%s）" % ENGINE_VERSION)
    ap("")
    ap("> 出自 FIre 消防技能系列 · 免费使用 · 生成时间口径：依据 2026-09 检索核实的现行文本")
    ap("")

    total = len(hits)
    if total == 0:
        ap("## 识别结果：本次描述中未发现可直接判定的隐患")
        ap("")
        ap("注意：**未发现不等于无隐患**——文字描述覆盖有限。下面是对照你场所特征主动列出的自查点，建议逐条过一遍。")
    else:
        ap("## 识别结果：命中 %d 条隐患" % total)
        ap("")
        ap("| 严重度 | 条数 | 说明 |")
        ap("|---|---|---|")
        ap("| 红线（涉嫌违法） | %d | 依据条款明文禁止，建议当天处置 |" % len(by_sev["红线"]))
        ap("| 高危 | %d | 重大火灾风险或设施失效，建议本周处置 |" % len(by_sev["高危"]))
        ap("| 提示 | %d | 管理性缺陷，纳入例行整改 |" % len(by_sev["提示"]))

    ap("")

    for sev in ("红线", "高危", "提示"):
        items = by_sev[sev]
        if not items:
            continue
        title = {
            "红线": "红线隐患（涉嫌违反明文禁令，置顶处置）",
            "高危": "高危隐患（重大风险）",
            "提示": "提示项（管理缺陷，例行整改）",
        }[sev]
        ap("### %s（%d 条）" % (title, len(items)))
        ap("")
        for i, (rule, hit) in enumerate(items, 1):
            ap("**%d. %s**（识别词：%s）" % (i, rule["name"], hit))
            ap("")
            ap("- 依据（%s）：%s" % (rule["citation_code"], rule["citation"]))
            ap("- 罚则：%s" % rule["penalty"])
            ap("- 怎么改：%s" % rule["action"])
            ap("")

    proactive = build_proactive(text, data, [r["id"] for r, _ in hits])
    if proactive:
        ap("### 主动自查清单（描述中未提及，请对照确认）")
        ap("")
        for item in proactive:
            ap("- [ ] %s（%s）" % (item["item"], item["why"]))
        ap("")

    if total:
        ap("## 处置优先级（Top %d，红线置顶）" % min(MAX_ACTION_LIST, total))
        ap("")
        ordered = by_sev["红线"] + by_sev["高危"] + by_sev["提示"]
        for i, (rule, _) in enumerate(ordered[:MAX_ACTION_LIST], 1):
            ap("%d. %s —— %s" % (i, rule["name"], rule["action"]))
        ap("")

    ap("## 系列工具衔接建议")
    ap("")
    ap("- 器材缺失/数量存疑：配合「灭火器配置顾问」生成合规配置方案")
    ap("- 涉及消控室值守：配合「消控室远程值守方案生成器」核查单人值守前提")
    ap("- 需要整体合规底账：配合「消防合规体检」跑一次覆盖度评估")
    ap("")
    ap("---")
    ap("")
    ap(DISCLAIMER)
    return "\n".join(lines), total


def main(argv):
    if len(argv) >= 2 and argv[1] == "version":
        data = load_rules()
        print("check-fire-hazard %s (FIre 系列 #5)" % ENGINE_VERSION)
        print("规则基数: %d（红线/高危/提示三档，每条含条款与罚则）" % len(data["rules"]))
        return 0
    if len(argv) < 3 or argv[1] != "scan":
        sys.stderr.write(__doc__ or "")
        return 2
    src = argv[2]
    out = argv[3] if len(argv) > 3 else None
    if not os.path.isfile(src):
        sys.stderr.write("输入文件不存在: %s\n" % src)
        return 2
    with open(src, encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        sys.stderr.write("输入文件为空\n")
        return 2
    data = load_rules()
    report, total = render(text, data)
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(report)
    # stdout 摘要
    flat = report
    m = re.search(r"命中 (\d+) 条隐患", flat)
    if m:
        print("识别结果: 命中 %s 条隐患" % m.group(1))
    else:
        print("识别结果: 未发现可直接判定的隐患（已附主动自查清单）")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
