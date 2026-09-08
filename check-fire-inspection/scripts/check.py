# -*- coding: utf-8 -*-
"""
check-fire-inspection —— 消防设施巡检助手（主动 Agent 版）
FIre 消防系列 #9

定位：不是"你巡什么我记什么"的被动台账，而是对照法定巡检基线主动发现：
- 巡检覆盖缺口：哪些设施/部位在你的巡检材料里没有任何证据（主动摆出来）；
- 坏状态红线：记录造假、主机屏蔽、消火栓无水等巡检中的危险信号（置顶）；
- 场所频次判定：重点单位每日 / 人密营业期每 2 小时 / 一般单位每季，按画像只报适用的。

每一条判定挂权威出处。宁可留白，不可错配。

纯标准库实现，零外部依赖。python scripts/check.py scan <input.md> [out.md]
"""
import sys
import os
import re
import json

ENGINE_VERSION = "1.0.1"
SKILL_NAME = "check-fire-inspection"

SEVERITY_ORDER = {"红线": 0, "高危": 1, "提示": 2}


def load_rules(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_venue(text, rules_doc):
    """返回命中场所画像列表（按 rules.json profiles.venue_rules）。"""
    hits = []
    for vr in rules_doc["profiles"]["venue_rules"]:
        for kw in vr["terms"]:
            if kw in text:
                hits.append(vr)
                break
    return hits


def run_scan(rules_doc, text):
    """返回 findings, gap_total, gap_evidenced。"""
    findings = []
    gap_total = 0
    gap_evidenced = 0
    for rule in rules_doc["rules"]:
        rtype = rule.get("type", "gap")
        kws = rule.get("detect", [])
        hit = any(kw in text for kw in kws)
        if rtype == "gap":
            gap_total += 1
            if hit:
                gap_evidenced += 1
                findings.append({
                    "id": rule["id"], "item": rule["item"], "freq": rule.get("freq", ""),
                    "severity": rule["severity"], "type": "gap", "status": "covered",
                    "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                })
            else:
                findings.append({
                    "id": rule["id"], "item": rule["item"], "freq": rule.get("freq", ""),
                    "severity": rule["severity"], "type": "gap", "status": "gap",
                    "text": rule.get("gap_text", ""), "action": rule.get("action", ""),
                    "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                })
        elif rtype == "violation":
            if hit:
                findings.append({
                    "id": rule["id"], "item": rule["item"], "freq": rule.get("freq", ""),
                    "severity": rule["severity"], "type": "violation", "status": "violation",
                    "text": rule.get("hit_text", ""), "action": rule.get("action", ""),
                    "penalty": rule.get("penalty", ""),
                    "citation": rule["citation"], "citation_code": rule.get("citation_code", ""),
                })
    return findings, gap_total, gap_evidenced


def build_checklist(rules_doc, text, used_ids):
    """主动自查清单：按场所特征挑未覆盖的漏项，封顶 6 条；不足补通用项。"""
    out = []
    for vr in rules_doc["proactive_checklist"]["venue_rules"]:
        if any(t in text for t in vr["terms"]):
            for item in vr["items"]:
                if item not in out:
                    out.append(f"【{vr['venue']}】{item}")
    for item in rules_doc["proactive_checklist"]["universal"]:
        if len(out) >= 6:
            break
        if item not in out:
            out.append(f"【通用】{item}")
    return out[:6]


def build_report(rules_doc, text, venues, findings, gap_total, gap_evidenced):
    lines = []
    lines.append("# 消防设施巡检报告（主动 Agent 版）")
    lines.append("")
    lines.append(f"- 技能：{SKILL_NAME} v{ENGINE_VERSION}")
    if venues:
        lines.append(f"- 场所画像：**{'、'.join(v['label'] for v in venues)}**")
        for v in venues[:1]:
            lines.append(f"- 法定巡查频次：{v['patrol']}")
            lines.append(f"  - 出处：{v['citation']}")
    else:
        lines.append("- 场所画像：**一般单位**（未识别到特定场所特征）")
        v0 = rules_doc["profiles"]["venue_rules"][-1]
        lines.append(f"- 参考巡查频次：{v0['patrol']}（{v0['citation']}）")
    lines.append(f"- 巡检覆盖基线：{gap_total} 项（按设施与部位拆解，未按画像骚扰）")
    lines.append("")

    # 覆盖度
    coverage = round(gap_evidenced / gap_total * 100) if gap_total else 0
    redlines = [f for f in findings if f["status"] == "violation" and f["severity"] == "红线"]
    highs = [f for f in findings if f["status"] == "violation" and f["severity"] == "高危"]
    if redlines:
        coverage = min(coverage, 40)
    lines.append(f"## 一、巡检覆盖度：{coverage} 分（满分100）")
    if redlines:
        lines.append("> 巡检材料中出现红线信号，覆盖度已封顶至 40 分以下，须优先清零。")
    elif coverage >= 80:
        lines.append("> 巡检覆盖较完整，仍有零星漏项（见下文）。")
    elif coverage >= 50:
        lines.append("> 约半数巡检项有证据，多项设施巡检未见记录，建议按缺口清单补齐。")
    else:
        lines.append("> 巡检覆盖严重不足——多数法定巡检项在材料中无任何证据。")
    lines.append("")

    # 红线信号
    lines.append("## 二、红线信号（巡检中的危险发现，必须立即处理）")
    if redlines:
        for f in sorted(redlines, key=lambda x: x["id"]):
            lines.append(f"- **[{f['id']}] {f['item']}** · 出处：{f['citation']}")
            lines.append(f"  - 发现：{f['text']}")
            lines.append(f"  - 下一步：{f['action']}")
            if f.get("penalty"):
                lines.append(f"  - 罚则：{f['penalty']}")
    else:
        lines.append("- 未发现红线级信号。")
    lines.append("")

    # 高危
    lines.append("## 三、高危信号（发现即挂账整改）")
    if highs:
        for f in sorted(highs, key=lambda x: x["id"]):
            lines.append(f"- **[{f['id']}] {f['item']}** · 出处：{f['citation']}")
            lines.append(f"  - 发现：{f['text']}")
            lines.append(f"  - 下一步：{f['action']}")
    else:
        lines.append("- 未发现高危级信号。")
    lines.append("")

    # 覆盖缺口（主动发现）
    gaps = [f for f in findings if f["status"] == "gap"]
    gaps.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 2), x["id"]))
    lines.append("## 四、巡检覆盖缺口（主动发现：材料未提供巡检证据）")
    lines.append("> 以下设施/部位的巡检证据在你的材料里没有找到。我们主动把它们列出来——不是等你问漏了什么，而是直接摆出缺口。")
    if gaps:
        for f in gaps:
            lines.append(f"- **[{f['id']}] {f['item']}**（法定频次：{f['freq']}）· 出处：{f['citation']}")
            lines.append(f"  - 缺口：{f['text']}")
            lines.append(f"  - 下一步：{f['action']}")
    else:
        lines.append("- 巡检基线全部有证据覆盖。")
    lines.append("")

    # 已覆盖项汇总（简表，不刷屏）
    covered = [f for f in findings if f["status"] == "covered"]
    lines.append("## 五、已覆盖巡检项（%d/%d）" % (gap_evidenced, gap_total))
    if covered:
        lines.append("| 项 | 法定频次 | 出处 |")
        lines.append("|---|---|---|")
        for f in covered:
            lines.append(f"| {f['item']} | {f['freq']} | {f['citation_code']} |")
    else:
        lines.append("- 暂无。")
    lines.append("")

    # 主动自查清单（封顶 6）
    lines.append("## 六、主动自查清单（按场所特征，封顶 6 条防骚扰）")
    for item in build_checklist(rules_doc, text, [f["id"] for f in findings]):
        lines.append(f"- [ ] {item}")
    lines.append("")

    # 免责
    lines.append("## 七、免责声明")
    lines.append("本报告基于公开消防法规与国家标准基线做巡检材料自查辅助，不能替代注册消防工程师、消防设施操作员等专业资质，也不能替代消防救援机构的监督检查。巡检证据判定基于你提供的文本（关键词命中），不验证现场真伪。标准以最新有效版本为准。")
    lines.append("")
    lines.append("---")
    lines.append("引用基线（部分）：消防法（2021修正）第十六、十七、二十八条；公安部61号令第二十五、二十六条；GB 25201-2010；GB 55036-2022；部令第5号。详见 `_foundation/regulations.json`。")
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
        venues = detect_venue(text, rules_doc)
        findings, gap_total, gap_evidenced = run_scan(rules_doc, text)
        report, coverage, n_red = build_report(rules_doc, text, venues, findings, gap_total, gap_evidenced)
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            print(f"OK 场所={','.join(v['label'] for v in venues) or '一般单位'} 覆盖度={coverage} 红线={n_red} 缺口={sum(1 for x in findings if x['status']=='gap')} 已写入 {out_path}")
            return 1 if (n_red > 0 or any(x["status"] == "gap" for x in findings)) else 0
        else:
            print(report)
            return 1 if (n_red > 0 or any(x["status"] == "gap" for x in findings)) else 0
    print("未知命令")
    return 2


if __name__ == "__main__":
    sys.exit(main())
