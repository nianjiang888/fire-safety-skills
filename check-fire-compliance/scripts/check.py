# -*- coding: utf-8 -*-
"""
check-fire-compliance —— 消防合规体检（主动 Agent 版）
FIre 消防系列 #1

定位：不是"你给我什么我查什么"的被动工具，而是主动对照完整法规基线，
把材料中缺失的合规项（缺口）主动摆出来，把违规红线先置顶，并给每条可执行下一步。

纯标准库实现，零外部依赖。python scripts/check.py scan <input.md> [out.md]
"""
import sys
import os
import re
import json

ENGINE_VERSION = "1.0.1"
SKILL_NAME = "check-fire-compliance"

# 单位画像关键词
PROFILE_KEYWORDS = {
    "key_unit": ["消防安全重点单位", "重点单位", "公众聚集场所"],
    "assembly": ["医院", "病房", "学校", "教学楼", "幼儿园", "托儿所", "养老院", "敬老院",
                 "福利院", "商场", "市场", "宾馆", "饭店", "酒店", "影剧院", "歌舞厅", "KTV",
                 "酒吧", "网吧", "公共娱乐", "集贸市场", "体育场馆", "展览馆", "博物馆", "图书馆",
                 "劳动密集型", "生产车间", "员工宿舍", "餐饮", "餐厅", "超市"],
    "high_risk": ["超高层", "大型综合体", "城市综合体", "综合体", "易燃易爆", "石油化工",
                  "加油加气站", "储罐", "高危"],
}

PROFILE_LABEL = {
    "general": "一般单位",
    "key_unit": "消防安全重点单位",
    "assembly": "人员密集场所",
    "high_risk": "火灾高危单位",
}

SEVERITY_ORDER = {"redline": 0, "high": 1, "suggest": 2}
SEVERITY_LABEL = {"redline": "红线", "high": "高危", "suggest": "建议"}


def load_rules(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_profile(text):
    found = []
    for prof, kws in PROFILE_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                found.append(prof)
                break
    if not found:
        return ["general"]
    # 去重并保持顺序
    seen = []
    for p in found:
        if p not in seen:
            seen.append(p)
    return seen


def rule_applies(rule, profiles):
    applies = rule.get("applies", ["all"])
    if "all" in applies:
        return True
    return bool(set(applies) & set(profiles))


def match_rule(rule, text):
    det = rule.get("detect", {})
    kind = det.get("kind", "regex")
    patterns = det.get("patterns", [])
    for pat in patterns:
        if kind == "regex":
            if re.search(pat, text):
                return True
        else:
            if pat in text:
                return True
    return False


def run_scan(rules_doc, text, profiles):
    """返回 findings 列表。每个 finding: id, dimension, severity, type, citation, text, action, status"""
    findings = []
    gap_total = 0
    gap_evidenced = 0
    for rule in rules_doc["rules"]:
        if not rule_applies(rule, profiles):
            continue
        rtype = rule.get("type", "gap")
        hit = match_rule(rule, text)
        if rtype == "gap":
            gap_total += 1
            if hit:
                gap_evidenced += 1
                # 材料已有证据：作为"已覆盖"记录（不主动告警，仅内部计分）
                findings.append({
                    "id": rule["id"], "dimension": rule["dimension"], "severity": rule["severity"],
                    "type": "gap", "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                    "text": rule.get("evidence_text", ""), "action": rule.get("action", ""), "status": "covered",
                })
            else:
                # 主动发现缺口
                findings.append({
                    "id": rule["id"], "dimension": rule["dimension"], "severity": rule["severity"],
                    "type": "gap", "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                    "text": rule.get("gap_text", ""), "action": rule.get("action", ""), "status": "gap",
                })
        elif rtype == "violation":
            if hit:
                findings.append({
                    "id": rule["id"], "dimension": rule["dimension"], "severity": "redline",
                    "type": "violation", "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                    "text": rule.get("hit_text", ""), "action": rule.get("action", ""), "status": "violation",
                })
    return findings, gap_total, gap_evidenced


def build_report(rules_doc, text, profiles, findings, gap_total, gap_evidenced):
    profile_labels = "、".join(PROFILE_LABEL.get(p, p) for p in profiles)
    lines = []
    lines.append("# 消防合规体检报告（主动 Agent 版）")
    lines.append("")
    lines.append(f"- 技能：{SKILL_NAME} v{ENGINE_VERSION}")
    lines.append(f"- 单位画像：**{profile_labels}**")
    lines.append(f"- 适用规则：{gap_total} 项合规基线（已按画像过滤不适用项）")
    lines.append("")

    # 覆盖度
    if gap_total > 0:
        coverage = round(gap_evidenced / gap_total * 100)
    else:
        coverage = 0
    redlines = [f for f in findings if f["status"] == "violation"]
    if redlines:
        coverage = min(coverage, 40)
    lines.append(f"## 一、合规覆盖度：{coverage} 分（满分100）")
    if redlines:
        lines.append("> 存在红线违规项，覆盖度已封顶至 40 分以下，须优先清零红线。")
    elif coverage >= 80:
        lines.append("> 材料体现的合规要素较为完整，仍有可优化空间（见下文建议项）。")
    elif coverage >= 50:
        lines.append("> 已覆盖约半数合规基线，存在多处需补齐的高危缺口。")
    else:
        lines.append("> 大量合规基线在材料中无证据，建议尽快系统补齐。")
    lines.append("")

    # 红线
    lines.append("## 二、红线预警（必须立即处理）")
    if redlines:
        for f in sorted(redlines, key=lambda x: x["id"]):
            lines.append(f"- **[{f['id']}] {f['dimension']}** · 出处：{f['citation']}")
            lines.append(f"  - 发现：{f['text']}")
            lines.append(f"  - 下一步：{f['action']}")
    else:
        lines.append("- 未发现材料中的红线违规表述。")
    lines.append("")

    # 高危缺口（主动发现）
    high_gaps = [f for f in findings if f["status"] == "gap" and f["severity"] == "high"]
    lines.append("## 三、高危缺口（主动发现：材料未提供证据）")
    lines.append("> 以下合规要求在对你单位的描述中没有找到任何证据。我们主动把它们列出来——不是等你问“我漏了什么”，而是直接摆出缺口。")
    if high_gaps:
        by_dim = {}
        for f in high_gaps:
            by_dim.setdefault(f["dimension"], []).append(f)
        for dim, items in by_dim.items():
            lines.append(f"### {dim}")
            for f in items:
                lines.append(f"- **[{f['id']}]** 出处：{f['citation']}")
                lines.append(f"  - 缺口：{f['text']}")
                lines.append(f"  - 下一步：{f['action']}")
    else:
        lines.append("- 当前画像下，高危缺口均已覆盖。")
    lines.append("")

    # 建议项
    sugg_gaps = [f for f in findings if f["status"] == "gap" and f["severity"] == "suggest"]
    lines.append("## 四、建议优化（可延后但不建议长期缺席）")
    if sugg_gaps:
        for f in sugg_gaps:
            lines.append(f"- **[{f['id']}] {f['dimension']}** · 出处：{f['citation']} — {f['text']}（下一步：{f['action']}）")
    else:
        lines.append("- 无。")
    lines.append("")

    # 优先级行动清单（封顶 10，防骚扰）
    action_items = [f for f in findings if f["status"] in ("gap", "violation") and f["severity"] in ("redline", "high")]
    action_items.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], x["id"]))
    lines.append("## 五、优先级行动清单（Top 10）")
    lines.append("> 同类已聚合、数量封顶，避免一次性甩给你太多动作。其余项见上方对应章节。")
    if action_items:
        top = action_items[:10]
        for i, f in enumerate(top, 1):
            tag = SEVERITY_LABEL[f["severity"]]
            lines.append(f"{i}. 【{tag}】{f['dimension']}（{f['id']}）：{f['action']}")
        if len(action_items) > 10:
            lines.append(f"... 其余 {len(action_items) - 10} 项高危/红线动作见上方章节。")
    else:
        lines.append("- 暂无需要优先处理的动作。")
    lines.append("")

    # 免责
    lines.append("## 六、免责声明")
    lines.append("本体检基于公开消防法规与国家标准基线进行自查辅助，不能替代注册消防工程师、消防设施操作员等专业资质，也不能替代消防救援机构的监督检查。重大场所、重点单位、火灾高危单位应咨询持证机构并配合官方检查。标准以最新有效版本为准。")
    lines.append("")
    lines.append("---")
    lines.append("引用基线（部分）：消防法（2021修正）、GB 55036-2022、GB 55037-2022、GB 25201-2010、GB/T 40248-2021、GB 50140-2005、公安部61号令、国办发〔2017〕87号、公消〔2015〕301号、消防〔2025〕33号、GB/T 26875.10-2026、GB 35181-2025。详见 `_foundation/regulations.json`。")
    return "\n".join(lines), coverage, len(redlines)


def main():
    if len(sys.argv) < 2:
        print("用法: python check.py scan <input.md> [out.md] | version")
        return 2
    cmd = sys.argv[1]
    if cmd == "version":
        print(f"{SKILL_NAME} {ENGINE_VERSION}")
        return 0
    if cmd == "scan":
        if len(sys.argv) < 3:
            print("scan 需要输入文件")
            return 1
        in_path = sys.argv[2]
        out_path = sys.argv[3] if len(sys.argv) > 3 else None
        here = os.path.dirname(os.path.abspath(__file__))
        rules_path = os.path.join(here, "..", "resources", "rules.json")
        rules_doc = load_rules(rules_path)
        with open(in_path, "r", encoding="utf-8") as f:
            text = f.read()
        profiles = detect_profile(text)
        findings, gap_total, gap_evidenced = run_scan(rules_doc, text, profiles)
        report, coverage, n_red = build_report(rules_doc, text, profiles, findings, gap_total, gap_evidenced)
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            print(f"OK 画像={profiles} 覆盖度={coverage} 红线={n_red} 已写入 {out_path}")
            return 4 if n_red > 0 else 0
        else:
            print(report)
            return 4 if n_red > 0 else 0
    print("未知命令")
    return 2


if __name__ == "__main__":
    sys.exit(main())
