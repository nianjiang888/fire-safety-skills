# -*- coding: utf-8 -*-
"""
gen-fire-plan —— 灭火和应急疏散预案生成器（主动 Agent 版）
FIre 消防系列 #8

定位：输入单位基础信息后，主动生成一份完整的灭火和应急疏散预案——
单位风险画像、应急组织机构、火情预想、报警接警、疏散扑救、
微型消防站联动、演练计划、善后与复盘（后几节用户未要求也主动给出）。

依据 GB/T 38315-2019《社会单位灭火和应急疏散预案编制及实施导则》等。
每一条关键判定挂权威出处。宁可留白，不可错配：缺字段标"待补充"。

纯标准库实现，零外部依赖。python scripts/gen.py gen <input.md> [out.md]
"""
import sys
import os
import re
import json
from datetime import date


def gen_date():
    """报告日期。默认取当天；设置环境变量 FIRE_GEN_DATE 可固定为指定日期，
    用于自动化复现比对（同一输入在任何机器上输出一致）。"""
    return os.environ.get("FIRE_GEN_DATE") or date.today().isoformat()

ENGINE_VERSION = "1.0.1"
SKILL_NAME = "gen-fire-plan"

FIELD_ALIASES = {
    "unit_name": ["单位名称", "项目名称", "单位", "项目"],
    "building_type": ["建筑类型", "业态", "建筑业态", "类型"],
    "area": ["建筑面积", "面积"],
    "headcount": ["人员规模", "在岗人数", "员工人数", "住宿人数", "人数"],
    "key_areas": ["重点部位", "火灾高危部位", "高风险部位", "危险部位", "要害部位"],
    "facilities": ["消防设施", "现有设施", "消防设备", "设施情况"],
    "existing_plan": ["现有预案", "预案现状", "有无预案", "预案情况"],
    "drill_freq": ["演练频次", "演练情况", "演练记录", "演练"],
    "region": ["所在省份", "所在省", "所在城市", "所在地", "省市", "省份", "城市"],
}

FIELD_LABEL = {
    "unit_name": "单位名称", "building_type": "建筑类型", "area": "建筑面积",
    "headcount": "人员规模", "key_areas": "重点部位", "facilities": "消防设施",
    "existing_plan": "现有预案", "drill_freq": "演练频次", "region": "所在省/市",
}


def load_recipe(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_input(text):
    fields = {}
    leftovers = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.split(r"[：:]", line, maxsplit=1)
        if len(m) != 2:
            leftovers.append(line)
            continue
        key, val = m[0].strip(), m[1].strip()
        matched = False
        for fid, aliases in FIELD_ALIASES.items():
            if key in aliases:
                fields[fid] = val
                matched = True
                break
        if not matched:
            leftovers.append(line)
    return fields, leftovers


def detect_profile(text, recipe):
    for pid, prof in recipe["profiles"].items():
        for kw in prof["keywords"]:
            if kw in text:
                return pid, prof["label"], prof
    return "office", "办公楼宇", recipe["profiles"]["office"]


def parse_number(raw):
    if not raw:
        return None
    m = re.search(r"\d+", raw)
    return int(m.group()) if m else None


def split_areas(raw):
    if not raw:
        return []
    parts = re.split(r"[，,、；;]", raw)
    return [p.strip() for p in parts if p.strip()]


def scale_factor(headcount):
    if headcount is None:
        return 1
    if headcount < 200:
        return 1
    if headcount <= 1000:
        return 2
    return 3


def build_org_groups(recipe, sf):
    lines = []
    for g in recipe["org_groups"]:
        if g["id"] == "HQ":
            size = 2 if sf >= 2 else 1
        else:
            size = g["base"] * sf
        lines.append((g, size))
    return lines


def match_scenario(area, scenarios):
    """部位→场景模板：先精确匹配，再双向子串匹配（如"地下车库"→"车库"）。"""
    if area in scenarios:
        return area
    for key in scenarios:
        if key in area or area in key:
            return key
    return None


def build_report(recipe, fields, leftovers, pid, profile_label, prof,
                 headcount, areas, today_str):
    out = []
    add = out.append
    unit = fields.get("unit_name") or "（待补充单位名称）"

    add("# 灭火和应急疏散预案（主动 Agent 版）")
    add("")
    add(f"- 技能：{SKILL_NAME} v{ENGINE_VERSION}")
    add(f"- 单位：**{unit}** · 画像：**{profile_label}**（火灾风险：{prof['risk']}）· 生成日期：{today_str}")
    add("")

    # 〇 输入与假设（主动暴露）
    add("## 〇、输入与假设（主动暴露，宁可留白不可错配）")
    add("")
    provided = []
    for fid, label in FIELD_LABEL.items():
        if fid in fields and fields[fid]:
            provided.append(f"- {label}：{fields[fid]}")
        else:
            provided.append(f"- {label}：**待补充**（本预案未替你假设此项）")
    add("\n".join(provided))
    if leftovers:
        add("- 未识别的补充行（已原样保留，供你归位）：")
        for l in leftovers[:8]:
            add(f"  - {l}")
    add("")

    # 一 法规依据
    add("## 一、预案定位与法规依据（全部带出处）")
    add("")
    add("本预案依据下列现行有效法规与标准编制，每条均在正文落实为具体章节：")
    add("")
    for b in recipe["plan_basis"]:
        add(f"- **{b['code']}**：{b['text']}（来源：{b['source']}）")
    add("")

    # 二 风险画像
    add("## 二、单位火灾风险画像（主动研判）")
    add("")
    if pid in recipe["profiles"]:
        add(f"- 业态定位：**{profile_label}**，火灾风险等级 **{prof['risk']}**；组织要点：{prof['org_note']}")
    if areas:
        known = [a for a in areas if a in recipe["key_area_scenarios"]]
        add(f"- 已识别重点部位 {len(areas)} 处：{('、'.join(areas))}。")
        if known:
            add(f"- 其中 {len(known)} 处已匹配标准火情场景模板（见第四章）。")
    else:
        add("- 重点部位：**待补充**——未提供重点部位，火情预想无法针对性生成；请补充后重跑本预案第四章。")
    add("")

    # 三 组织机构
    add("## 三、应急组织机构（按单位规模测算）")
    add("")
    sf = scale_factor(headcount)
    org_lines = build_org_groups(recipe, sf)
    total = sum(s for _, s in org_lines)
    add("- 规模系数：在岗/住宿人数 " + (f"约 {headcount} 人 → 系数 ×{sf}" if headcount else "**待补充** → 暂按基础配置（系数 ×1），补充人数后自动放大") + "。")
    add(f"- 初估应急组织总规模约 **{total} 人**（含微型消防站前置力量见第八章）。")
    add("")
    add("| 组别 | 职责 | 建议人数 |")
    add("|---|---|---|")
    for g, size in org_lines:
        add(f"| {g['name']} | {g['duty']} | {size} |")
    add("")
    add(f"- 依据：GB/T 38315-2019（预案组织机构要求）、消防法第十六条。人数按规模系数缩放，最终以单位实际排班为准。")
    add("")

    # 四 火情预想（主动）
    add("## 四、火情预想（主动基于重点部位生成）")
    add("")
    if areas:
        shown = 0
        for a in areas:
            key = match_scenario(a, recipe["key_area_scenarios"])
            if key:
                add(f"- **{a}**：{recipe['key_area_scenarios'][key]}")
                shown += 1
            else:
                add(f"- **{a}**：未匹配预设模板，须依据现场火灾危险性（可燃物、工艺、人员）专项研判，并在预案附件补专项措施。")
            if shown >= 8:
                add(f"- （其余重点部位同理专项研判，已封顶展示 {shown} 条。）")
                break
    else:
        add("- 未提供重点部位，无法生成针对性火情预想。建议先补充重点部位清单（如配电室、厨房、仓库、机房等），本预案将自动匹配标准场景。")
    add("")

    # 五 报警接警与处置流程
    add("## 五、报警、接警与处置流程")
    add("")
    for i, step in enumerate(recipe["response_steps"], 1):
        add(f"{i}. {step}")
    add("- 出处：GB/T 38315-2019（报警和接警处置程序、扑救初起火灾程序）。")
    add("")

    # 六 应急疏散（主动给集合点占位）
    add("## 六、应急疏散方案（主动给出要点）")
    add("")
    add("- 疏散原则：低头、捂口鼻、靠右、走楼梯、禁乘电梯；按楼层/区域分区引导，专人看护行动不便人员。")
    add("- 疏散路线：每个防火分区选择最近两个独立安全出口，路线不穿越火灾危险区（依据 GB 55037-2022 疏散要求）。")
    add("- 室外集合点：**待你指定**（建议选上风向、距建筑≥15米且不影响消防车作业的空地），并在平面图标注、全员告知。")
    add("- 人数清点：疏散引导组在集合点按部门/楼层清点，失联人员立即上报指挥部并转告119。")
    add("- 依据：消防法第十六条（四）；GB/T 38315-2019（应急疏散组织程序）。")
    add("")

    # 七 初起火灾扑救（基于设施）
    add("## 七、初起火灾扑救（结合现有消防设施）")
    add("")
    fac = fields.get("facilities", "") or ""
    if fac:
        add(f"- 已登记消防设施：{fac}。扑救时优先就近取用灭火器/室内消火栓，并启动相应固定消防设施。")
    else:
        add("- 消防设施：**待补充**。通用扑救要点：电气火灾先断电再用二氧化碳/干粉；油类火灾用灭火毯/锅盖窒息，严禁用水；火势失控立即撤离转控火待援。")
    add("- 处置纪律：3分钟内微型消防站到场先期控火；火势失控即撤至安全区，交由专业消防队伍处置，严禁盲目内攻。")
    add("- 依据：消防法第十六条；GB/T 38315-2019；GB/T 4968-2008（火灾分类）。")
    add("")

    # 八 微型消防站联动（主动）
    add("## 八、微型消防站联动（主动生成，未要求也给出）")
    add("")
    add(f"- {recipe['micro_station']['text']}")
    add(f"- 依据：{recipe['micro_station']['citation']}。")
    add("")

    # 九 演练计划（主动）
    add("## 九、演练计划（主动给出，对照法定频次）")
    add("")
    if pid in ("hospital", "school") and "寄宿" in (fields.get("building_type", "") + profile_label):
        add(f"- {recipe['drill_rules']['night']}")
    if profile_label in ("办公楼宇",):
        add(f"- {recipe['drill_rules']['general']}")
    else:
        add(f"- {recipe['drill_rules']['key_unit']}")
    add(f"- {recipe['drill_rules']['assembly']}")
    freq = (fields.get("drill_freq", "") or "").lower()
    if "从未" in freq or "没" in freq or "无" in freq or not fields.get("drill_freq"):
        add("- **当前演练状态：待补齐**。材料未体现有效演练记录，须按上述频次制定年度演练计划（总预案+专项+桌面推演组合）。")
    else:
        add(f"- 当前演练频次自述：{fields['drill_freq']}；请对照法定频次核验是否满足（不满足须补足）。")
    add("- 演练须留存方案、签到、照片、评估记录，作为合规证据。")
    add("")

    # 十 善后复盘（主动）
    add("## 十、善后与复盘（主动生成）")
    add("")
    add("- 火灾扑灭后保护现场、配合调查；清点损失、安抚受影响人员、恢复消防设施。")
    add("- 演练/实战后72小时内完成复盘：处置时间线、各组到位时效、暴露短板、整改清单，纳入预案动态修订。")
    add("- 预案每年至少评审修订一次，单位情况重大变化（改建、业态调整、人员结构变化）即时修订。")
    add("")

    # 十一 免责
    add("## 十一、免责声明")
    add("")
    add(recipe["disclaimer"])
    add("")
    add("---")
    add("合规依据汇总：消防法（2021修正）第十六、十七条；GB/T 38315-2019；公安部61号令第四十、四十一条；GB/T 40248-2021；GB 55037-2022；公消〔2015〕301号；消防〔2025〕33号。详见 `_foundation/regulations.json`。")
    add("")

    # 附 自查清单
    add("## 附：预案落地自查清单（逐项打勾）")
    add("")
    add("- [ ] 预案已覆盖单位基本情况与全部重点部位火情预想")
    add("- [ ] 应急组织机构人员已明确并公示（含微型消防站前置力量）")
    add("- [ ] 报警电话、疏散路线、室外集合点已上墙并告知全员")
    add("- [ ] 按法定频次完成演练并留存记录（重点单位每半年/其他每年）")
    add("- [ ] 演练复盘短板已纳入预案修订")
    add("- [ ] 预案每年评审一次，重大变化即时修订")
    add("- [ ] 重点部位专项措施已补全（未匹配模板的部位）")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("用法: python gen.py gen <input.md> [out.md] | version")
        return 2
    cmd = sys.argv[1]
    if cmd == "version":
        print(f"{SKILL_NAME} {ENGINE_VERSION}")
        return 0
    if cmd == "gen":
        if len(sys.argv) < 3:
            print("gen 需要输入文件")
            return 1
        in_path = sys.argv[2]
        out_path = sys.argv[3] if len(sys.argv) > 3 else None
        here = os.path.dirname(os.path.abspath(__file__))
        recipe_path = os.path.join(here, "..", "resources", "recipe.json")
        recipe = load_recipe(recipe_path)
        with open(in_path, "r", encoding="utf-8") as f:
            text = f.read()
        fields, leftovers = parse_input(text)
        pid, profile_label, prof = detect_profile(text, recipe)
        headcount = parse_number(fields.get("headcount", ""))
        areas = split_areas(fields.get("key_areas", ""))
        report = build_report(recipe, fields, leftovers, pid, profile_label, prof,
                              headcount, areas, gen_date())
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            n_area = len(areas)
            print(f"OK 画像={profile_label} 重点部位={n_area} 规模系数={scale_factor(headcount)} 已写入 {out_path}")
            return 0
        else:
            print(report)
            return 0
    print("未知命令")
    return 2


if __name__ == "__main__":
    sys.exit(main())
