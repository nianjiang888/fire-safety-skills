# -*- coding: utf-8 -*-
"""
gen-fire-remote-duty —— 消控室远程值守方案生成器（主动 Agent 版）
FIre 消防系列 #2

定位：不是"问一句答一句"的被动工具，而是输入单位基础信息后，
主动生成一份完整的远程值守方案——法定基线、单人值守政策对照、
合规条件逐条核查、人力测算（算式透明）、处置流程、误报治理与
断网降级预案（这两个章节用户没要求也主动给出）。

每一条关键判定都挂权威出处。宁可留白，不可错配：
缺的信息标"待补充"，绝不替用户编造所在地政策。

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
SKILL_NAME = "gen-fire-remote-duty"

# 输入字段别名（支持中英文冒号）
FIELD_ALIASES = {
    "unit_name": ["单位名称", "项目名称", "单位", "项目"],
    "building_type": ["建筑类型", "业态", "建筑业态", "类型"],
    "area": ["建筑面积", "面积"],
    "region": ["所在省份", "所在省", "所在城市", "所在地", "省市", "省份", "城市", "地点"],
    "rooms": ["消控室数量", "消防控制室数量", "消控室数"],
    "mode_intent": ["值班模式意向", "值班模式", "意向模式", "值守模式"],
    "facilities": ["设施现状", "现有设施", "设施情况", "消防设施"],
    "certified": ["持证人数", "持证值班人员数", "持证人员数", "持证人员"],
}

FIELD_LABEL = {
    "unit_name": "单位名称", "building_type": "建筑类型", "area": "建筑面积",
    "region": "所在省/市", "rooms": "消控室数量", "mode_intent": "值班模式意向",
    "facilities": "设施现状", "certified": "持证人数",
}


def load_recipe(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_input(text):
    """解析 key: value 行；返回 (fields, leftovers)。"""
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
                return pid, prof["label"]
    return "general", "通用建筑"


def parse_mode(fields):
    intent = fields.get("mode_intent", "")
    if "单人" in intent:
        return "单人值守", False
    if "双人" in intent:
        return "双人值守", False
    return "双人值守", True  # 未提供 → 默认法定基线，标记为假设


def find_region_policy(fields, text, policy_db):
    """返回命中的政策条目列表。优先 region 字段，其次全文。"""
    region_str = fields.get("region", "") or ""
    hits = []
    seen = set()
    for entry in policy_db:
        for alias in entry["alias"]:
            if alias in region_str or alias in text:
                if entry["region"] not in seen:
                    hits.append(entry)
                    seen.add(entry["region"])
                break
    # 最具体的排前面（city 优先于 province）
    hits.sort(key=lambda e: 0 if e["level"] == "city" else 1)
    return hits


def check_conditions(text, recipe):
    """逐条核查单人值守合规条件。返回 [(cond, evidence_or_None)]。"""
    results = []
    for cond in recipe["single_duty_conditions"]:
        evidence = None
        for kw in cond.get("evidence_keywords", []):
            if kw in text:
                evidence = kw
                break
        results.append((cond, evidence))
    return results


def staffing_calc(mode, certified_raw, recipe):
    """人力测算，算式透明。返回 (lines, required_total)。"""
    per = recipe["staffing"]["per_shift"][mode]
    sup = recipe["staffing"]["supervisor"]
    lines = []
    totals = []
    for opt in recipe["staffing"]["shift_options"]:
        crews = opt["crews"]
        front = crews * per
        total = front + sup
        totals.append(total)
        lines.append({
            "label": opt["label"],
            "calc": f"{crews} × {per} = {front}",
            "front": front,
            "total": total,
        })
    required = min(totals)
    certified = None
    if certified_raw:
        m = re.search(r"\d+", certified_raw)
        if m:
            certified = int(m.group())
    return lines, required, sup, certified


def build_report(recipe, fields, leftovers, profile_label, mode, mode_assumed,
                 policy_hits, cond_results, staff, today_str):
    lines_out = []
    add = lines_out.append

    unit = fields.get("unit_name") or "（待补充单位名称）"
    add(f"# 消防控制室远程值守方案（主动 Agent 版）")
    add("")
    add(f"- 技能：{SKILL_NAME} v{ENGINE_VERSION}")
    add(f"- 单位：{unit} · 画像：**{profile_label}** · 生成日期：{today_str}")
    add("")

    # 〇 输入与假设（主动暴露）
    add("## 〇、输入与假设（主动暴露，宁可留白不可错配）")
    add("")
    provided = []
    for fid, label in FIELD_LABEL.items():
        if fid in fields and fields[fid]:
            provided.append(f"- {label}：{fields[fid]}")
        else:
            provided.append(f"- {label}：**待补充**（本方案未替你假设此项）")
    add("\n".join(provided))
    if mode_assumed:
        add("- 值班模式意向：未提供 → **已按法定基线默认双人值守**，如需单人值守请明确标注并核对第三章条件。")
    if leftovers:
        add("- 未识别的补充行（已原样保留，供你归位）：")
        for l in leftovers[:8]:
            add(f"  - {l}")
    add("")

    # 一 方案摘要
    add("## 一、方案摘要与值守模式判定")
    add("")
    add(f"- 法定基线：**{recipe['duty_baseline']['rule']}**")
    add(f"  - 出处：{recipe['duty_baseline']['citation']}")
    if policy_hits:
        primary = policy_hits[0]
        add(f"- 所在地政策命中：**{primary['region']}** — {primary['basis']}（{primary['effective']} 起施行）")
        add(f"  - 条文要点：{primary['rule']}")
        if mode == "单人值守":
            add(f"- 值守模式判定：**单人值守+远程监控（有条件可行）** — 所在地有明确政策授权，但须逐条满足第三章条件；任一条不满足即回退双人值守。")
        else:
            add(f"- 值守模式判定：**双人值守（法定基线）**；所在地已允许有条件单人值守（{primary['region']}），如需减员可按第三章条件逐条达标后切换。")
    else:
        add("- 所在地政策命中：**未命中已知政策库**。单人值守是否可行以当地现行消防条例与消防部门意见为准（确认路径见第三章 C1）。")
        add("- 值守模式判定：**双人值守（法定基线）**。未核实到所在地单人值守政策前，不应自行减员。")
    add("")

    # 二 法规与政策依据
    add("## 二、法规与政策依据（全部带出处）")
    add("")
    add("### 2.1 国家层面基线")
    add("- 消防法第十六条、第十七条、第二十一条（2021修正）：单位消防职责、重点单位职责、自动消防系统操作人员持证上岗。")
    add("- 公安部61号令第三十一条（六）与 GB 25201-2010 第5.2条：消控室每日二十四小时值班、每班不少于二人。")
    add("- GB 25506-2010《消防控制室通用技术要求》（2011-07-01 实施，第4~7章为强制性条款）：消控室资料、管理、控制显示与信息传输要求。")
    add("- 公消〔2017〕297号《关于全面推进“智慧消防”建设的指导意见》（2017-10-10）：五大任务之首即建设城市物联网消防远程监控系统。")
    add("### 2.2 远程监控系统技术标准")
    add("- GB 26875.1-2011（用户信息传输装置）、GB/T 26875.3-2011（报警传输网络通信协议）、GB/T 26875.7-2015（维护管理软件）、GB/T 26875.8-2015（监控中心对外数据交换协议）。")
    add("- GB/T 26875.10-2026（消防设施信息采集装置及接口要求，2026年新发布国标之一）；GB 50440-2007《城市消防远程监控系统技术规范》。")
    add("- T/CFPA 052-2026《建筑消防设施远程监控系统技术规程》（2026-01-27 发布，现行）。")
    add("### 2.3 单人值守政策对照表（" + recipe["policy_db_note"] + "）")
    add("")
    add("| 地区 | 级别 | 依据 | 施行 | 要点 |")
    add("|---|---|---|---|---|")
    hit_regions = {e["region"] for e in policy_hits}
    for e in recipe["policy_db"]:
        mark = " **←所在地命中**" if e["region"] in hit_regions else ""
        add(f"| {e['region']}{mark} | {'省级' if e['level']=='province' else '设区市'} | {e['basis']} | {e['effective']} | {e['rule'][:38]}… |")
    add("")

    # 三 单人值守合规条件核查
    add("## 三、单人值守合规条件核查（主动逐条对照）")
    add("")
    if mode != "单人值守":
        add("> 当前按双人值守规划。下表供未来切换单人值守时提前对照——**提前把条件列全，而不是等你临用时才发现缺项**。")
        add("")
    add("| 编号 | 条件 | 现状证据 | 判定 | 出处 |")
    add("|---|---|---|---|---|")
    n_met = 0
    for cond, ev in cond_results:
        if cond["id"] == "C1":
            if policy_hits:
                verdict = "满足（所在地政策已命中）"
                ev_show = policy_hits[0]["region"]
                n_met += 1
            else:
                verdict = "未满足/待确认（未命中政策库）"
                ev_show = "—"
        else:
            if ev:
                verdict = "有证据（初步满足）"
                ev_show = f"关键词命中「{ev}」"
                n_met += 1
            else:
                verdict = "**未提供证据**"
                ev_show = "—"
        add(f"| {cond['id']} | {cond['text']} | {ev_show} | {verdict} | {cond['citation']} |")
    add("")
    if mode == "单人值守":
        if n_met == len(cond_results):
            add(f"**判定：{n_met}/{len(cond_results)} 条均有证据支撑，可进入实施评估阶段（仍需当地消防部门确认）。**")
        else:
            add(f"**判定：{n_met}/{len(cond_results)} 条满足。未提供证据的条目须补齐后再切换单人值守；在此之前维持双人值守。**")
    add("")

    # 四 人力测算
    add("## 四、值守人力测算（算式透明）")
    add("")
    for line in staff["lines"]:
        add(f"- **{line['label']}**：一线人力 = 班组数 × 每班人数，即 {line['calc']}；加{recipe['staffing']['supervisor_label']}，**合计 {line['total']} 人**。")
    add(f"- 机动备岗：{recipe['staffing']['reserve_note']}")
    add(f"- 依据：{recipe['staffing']['baseline_citation']}")
    if staff["certified"] is not None:
        if staff["certified"] >= staff["required"]:
            add(f"- 持证人数核对：现有 {staff['certified']} 人，不低于最低方案需求 {staff['required']} 人（含值班长）。")
        else:
            add(f"- **持证缺口：现有 {staff['certified']} 人 < 最低方案需求 {staff['required']} 人（含值班长）。** 在合规条件满足前提下，可采用远程值守模式降低现场人数需求，或补充持证人员；缺口未补前不得减员。")
    else:
        add("- 持证人数核对：**待补充**——请填写持证值班人员数，以便核对其是否覆盖测算需求。")
    add(f"- 说明：{recipe['staffing']['note']}")
    add("")

    # 五 岗位职责与处置流程
    add("## 五、岗位职责与火警处置流程")
    add("")
    add("### 5.1 岗位分工")
    if mode == "单人值守" and policy_hits:
        add("- 现场值班（1人/班）：盯守主机与控制功能、实地核警、初期处置；**不得兼任其他岗位致脱岗**。")
        add("- 远程监控中心（云端）：24小时持证值守，承担告警甄别、远程复核、指令下发与全流程留痕；与现场形成双重防护。")
    else:
        add("- 现场值班（2人/班）：1人负责核警与现场设施操作，1人留守消控室操作联动系统并启动预案。")
        add("- 远程监控中心（如已接入）：承担告警同步复核与信息推送，不替代现场法定值守。")
    add(f"- 依据：{recipe['duty_baseline']['citation']}。")
    add("### 5.2 火警确认与处置流程（时限目标）")
    for item in recipe["response_targets"]["items"]:
        add(f"- {item}")
    add(f"- 出处：{recipe['response_targets']['citation']}。")
    add("### 5.3 误报治理机制（主动给出，未要求也生成）")
    add("- 建立误报台账：登记点位、时间、误报原因（粉尘、水汽、器件老化、施工干扰等）。")
    add("- 月度分析：对重复误报点位挂牌治理，联合维保单位整改并复测。")
    add("- 误报率异常升高时视为设施故障前兆，须立即排查，不得以消音屏蔽代替维修。")
    add("### 5.4 断网/平台故障降级预案（主动给出，未要求也生成）")
    add("- 远程监控系统通信中断或平台故障时，**立即回退双人值守**，直至链路恢复并经复核。")
    add("- 值班人员按 GB/T 26875.3-2011 的断点续传与故障报警要求确认传输装置状态，故障期间加密巡查频次。")
    add("- 降级与恢复过程记入值班台账，作为合规证据留存。")
    add("")

    # 六 技术配置要点
    add("## 六、技术配置要点")
    add("")
    add("- 按 GB 26875.1-2011 配置用户信息传输装置，火灾报警与设施运行状态信息按 GB/T 26875.3-2011 协议实时上传（10秒级），断点续传、信息重发机制可用。")
    add("- 平台须具备**远程操作消控室所有控制功能**的能力（远程复位、消音、水泵控制柜启停等按规程操作并全程留痕），仅有报警数据上传不构成单人值守依据。")
    add("- 新建/改造项目参照 GB/T 26875.10-2026 配置消防设施信息采集装置及接口；系统设计与验收参照 GB 50440-2007 与 T/CFPA 052-2026。")
    add("- 消控室图形显示与信息记录满足 GB 25506-2010 第6、7章（强制性条款）要求。")
    add("")

    # 七 管理制度配套
    add("## 七、管理制度配套")
    add("")
    add("- 交接班制度：书面交接运行状态、遗留问题与台账签字。")
    add("- 在岗核查：视频点名、平台在线状态与定期抽查结合，防脱岗。")
    add("- 培训演练：值班人员年度培训与新员工岗前培训；灭火和应急疏散演练按 GB/T 38315-2019 编制并定期实施（重点单位每半年）。")
    add("- 消防档案：接入方案、平台协议、值班台账、误报台账、维保检测记录一并归档。")
    add("")

    # 八 落地实施计划
    add("## 八、落地实施计划（三阶段）")
    add("")
    add("1. **评估阶段**：核对第三章条件逐条达标；向当地消防救援部门确认单人值守政策适用口径。")
    add("2. **建设阶段**：补齐传输装置与平台远程控制能力；完成持证人员配置与制度文件（岗位职责、处置流程、降级预案）。")
    add("3. **运行阶段**：先以“双人值守+远程监控”并行试运行，记录台账；条件稳定后再按当地政策申请切换，切换后保留回退机制。")
    add("")

    # 九 免责
    add("## 九、免责声明")
    add("")
    add(recipe["disclaimer"])
    add("")
    add("---")
    add("合规依据清单（汇总）：消防法（2021修正）第十六、十七、二十一条；公安部61号令第三十一条（六）；GB 25506-2010；GB 25201-2010；GB 26875.1/.3（2011）、GB/T 26875.7（2015）、GB/T 26875.8（2015）、GB/T 26875.10-2026；GB 50440-2007；T/CFPA 052-2026；公消〔2017〕297号；公消〔2015〕301号；GB/T 38315-2019；各地消防条例（见2.3对照表）。")
    add("")

    # 附 落地自查清单
    add("## 附：落地自查清单（逐项打勾）")
    add("")
    add("- [ ] 所在地单人值守政策已向当地消防部门确认（C1）")
    add("- [ ] 用户信息传输装置已配置并与平台联网（C2，GB 26875.1-2011）")
    add("- [ ] 平台具备远程操作消控室所有控制功能且全程留痕（C2）")
    add("- [ ] 远程监控中心24小时持证值守落实（C3）")
    add("- [ ] 消防设施完好、维保与年度检测记录齐全（C4）")
    add("- [ ] 现场与云端人员均持消防设施操作员证（C5，消防法第二十一条）")
    add("- [ ] 值守人力满足第四章测算且持证覆盖（61号令第三十一条（六））")
    add("- [ ] 处置流程、误报台账、断网降级预案成文并培训到人")
    add("- [ ] 试运行台账留存，切换单人值守前经当地消防部门确认")
    return "\n".join(lines_out)


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
        pid, profile_label = detect_profile(text, recipe)
        mode, mode_assumed = parse_mode(fields)
        policy_hits = find_region_policy(fields, text, recipe["policy_db"])
        cond_results = check_conditions(text, recipe)
        staff_lines, required, sup, certified = staffing_calc(
            mode, fields.get("certified", ""), recipe)
        staff = {"lines": staff_lines, "required": required, "sup": sup, "certified": certified}
        report = build_report(recipe, fields, leftovers, profile_label, mode,
                              mode_assumed, policy_hits, cond_results, staff,
                              gen_date())
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            n_gap = sum(1 for _, ev in cond_results if ev is None)
            print(f"OK 画像={profile_label} 模式={mode} 政策命中={len(policy_hits)} 条件未证={n_gap} 已写入 {out_path}")
            return 0
        else:
            print(report)
            return 0
    print("未知命令")
    return 2


if __name__ == "__main__":
    sys.exit(main())
