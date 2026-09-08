# -*- coding: utf-8 -*-
"""
gen-fire-training —— 消防培训课件生成器（主动 Agent 版）
FIre 消防系列 #10

定位：输入培训对象/时长/场所后，主动生成一份可直接开课的消防培训方案——
课程大纲、逐页课件内容、实操设计、考核题库、培训记录留痕、复训计划
（考核与留痕即使用户没要求也主动给出）。

依据 公安部61号令第三十六条、GB/T 40248-2021、社会单位消防安全四个能力。
每一条关键判定挂权威出处。宁可留白，不可错配。

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
SKILL_NAME = "gen-fire-training"

FIELD_ALIASES = {
    "unit_name": ["单位名称", "单位", "项目名称"],
    "audience": ["培训对象", "对象", "学员", "受众"],
    "duration": ["培训时长", "时长", "课时"],
    "venue_type": ["场所", "业态", "单位类型", "行业"],
    "headcount": ["人数", "参训人数", "人员规模"],
    "topics": ["重点主题", "侧重", "重点内容", "主题"],
    "quiz_need": ["考核", "是否考核", "考核需求", "考试"],
    "form": ["培训形式", "形式", "方式"],
}

FIELD_LABEL = {
    "unit_name": "单位名称", "audience": "培训对象", "duration": "培训时长",
    "venue_type": "场所/业态", "headcount": "参训人数", "topics": "重点主题",
    "quiz_need": "考核需求", "form": "培训形式",
}

# 模块 id → 四个能力映射
FOUR_ABILITY_MAP = {
    "检查消除火灾隐患能力": ["RISK-SOURCE", "PATROL-SKILL"],
    "扑救初起火灾能力": ["FIRE-EXT", "MS-RESPONSE"],
    "组织疏散逃生能力": ["EVAC-BASIC", "EVAC-ORG"],
    "消防宣传教育能力": [],  # 本课件本身即载体
}

QUIZ_FOR_45 = 6
QUIZ_DEFAULT = 10


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


def detect_audience(text, recipe):
    """特定受众优先，泛化的 all_staff 最后兜底（避免"新员工"被"员工"抢先）。"""
    for skip_generic in (True, False):
        for aid, aud in recipe["audiences"].items():
            if skip_generic and aid == "all_staff":
                continue
            for kw in aud["keywords"]:
                if kw in text:
                    return aid, aud
    return "all_staff", recipe["audiences"]["all_staff"]


def parse_duration(raw):
    raw = raw or ""
    if "45" in raw:
        return "45"
    if "半天" in raw or "3 小时" in raw or "3小时" in raw or "180" in raw:
        return "half"
    if "90" in raw or "1.5" in raw:
        return "90"
    return "90" if raw else "90"  # 未提供默认 90（并标注为假设）


def select_modules(recipe, aid, duration_key, topics_raw):
    """选课：时长方案 ∪ 受众默认方案（受众在前），显式主题匹配的模块强制纳入并标侧重。"""
    mod_ids = []
    if aid in recipe["audience_default_plan"]:
        mod_ids.extend(recipe["audience_default_plan"][aid])
    mod_ids.extend(recipe["duration_plans"][duration_key]["modules"])
    # 受众 focus 前插
    focus = recipe["audiences"][aid]["focus"]
    for m in focus:
        if m not in mod_ids:
            mod_ids.insert(0, m)
    # 显式主题匹配
    emphasized = []
    if topics_raw:
        lib = {m["id"]: m for m in recipe["module_library"]}
        for mid, m in lib.items():
            blob = m["title"] + "".join(m["points"])
            for kw in re.split(r"[，,、；;\s]", topics_raw):
                if kw and kw in blob:
                    if mid not in mod_ids:
                        mod_ids.append(mid)
                    if mid not in emphasized:
                        emphasized.append(mid)
    mod_ids = list(dict.fromkeys(mod_ids))
    return mod_ids, emphasized


def build_report(recipe, fields, leftovers, aid, aud, duration_key, duration_assumed,
                 mod_ids, emphasized, today_str):
    out = []
    add = out.append
    unit = fields.get("unit_name") or "（待补充单位名称）"
    lib = {m["id"]: m for m in recipe["module_library"]}
    modules = [lib[m] for m in mod_ids if m in lib]
    total_min = sum(m["minutes"] for m in modules)
    plan = recipe["duration_plans"][duration_key]

    add("# 消防培训方案与课件（主动 Agent 版）")
    add("")
    add(f"- 技能：{SKILL_NAME} v{ENGINE_VERSION}")
    add(f"- 单位：**{unit}** · 培训对象：**{aud['label']}** · 生成日期：{today_str}")
    add("")

    # 〇 输入与假设
    add("## 〇、输入与假设（主动暴露，宁可留白不可错配）")
    add("")
    provided = []
    for fid, label in FIELD_LABEL.items():
        if fid in fields and fields[fid]:
            provided.append(f"- {label}：{fields[fid]}")
        else:
            provided.append(f"- {label}：**待补充**（本方案未替你假设此项）")
    add("\n".join(provided))
    if duration_assumed:
        add("- 培训时长：未提供 → **已默认按 90 分钟进阶课时排课**，如需压缩到 45 分钟请重跑并填写时长。")
    if leftovers:
        add("- 未识别的补充行（已原样保留，供你归位）：")
        for l in leftovers[:8]:
            add(f"  - {l}")
    add("")

    # 一 法规依据
    add("## 一、培训定位与法规依据（全部带出处）")
    add("")
    for b in recipe["legal_basis"]:
        add(f"- **{b['code']}**：{b['text']}（来源：{b['source']}）")
    add("")

    # 二 学员画像与课程目标
    add("## 二、学员画像与课程目标（对照四个能力）")
    add("")
    add(f"- 对象特征：{aud['note']}。")
    covered_ids = set(mod_ids)
    for ability, mids in FOUR_ABILITY_MAP.items():
        if not mids:
            add(f"- {ability}：本培训本身就是载体，课后由学员向家人同事转训。")
        elif [m for m in mids if m in covered_ids]:
            # 保持模块库既定顺序输出，避免集合迭代顺序不稳定导致同一输入两次生成结果不同
            hit = "、".join(lib[m]["title"] for m in mids if m in covered_ids)
            add(f"- {ability}：由《{hit}》模块支撑。")
        else:
            add(f"- {ability}：**本次课程未覆盖**，建议在复训中补齐。")
    add("")

    # 三 课程大纲
    add("## 三、课程大纲（合计约 %d 分钟）" % total_min)
    add("")
    add("| 序 | 模块 | 时长 | 侧重 |")
    add("|---|---|---|---|")
    for i, m in enumerate(modules, 1):
        mark = " **重点**" if m["id"] in emphasized else ""
        add(f"| {i} | {m['title']} | {m['minutes']} 分钟 | {mark} |")
    add(f"- 实操环节：{plan['drill']}。")
    nominal = {"45": 45, "90": 90, "half": 180}[duration_key]
    if total_min > nominal:
        add(f"- **课时校准**：讲授合计约 {total_min} 分钟，超出 {nominal} 分钟课时。压缩顺序：先压第一讲（职责概述点到即止），互动提问并入课间；不要压缩实操。")
    if emphasized:
        add(f"- 你填写的重点主题已映射为标星模块：{('、'.join(lib[e]['title'] for e in emphasized))}。")
    add("")

    # 四 逐页课件内容
    add("## 四、课件逐页内容（可直接做成 PPT）")
    add("")
    add("### 开场页：为什么今天讲消防")
    add("- 一句话破题：火灾不会挑日子；今天的每一条，都是事故教训换来的。")
    add("- 本课程依据消防法与公安部61号令开展，学习结果将纳入培训考核记录存档。")
    add("")
    for i, m in enumerate(modules, 1):
        add(f"### 第 {i} 讲：{m['title']}（约 {m['minutes']} 分钟）")
        for p in m["points"]:
            add(f"- {p}")
        add(f"- 出处：{m['citation']}。")
        add("")
    add("### 结尾页：今天带走三句话")
    add("- 会报警：119 六要素张口就来。")
    add("- 会灭火：火小敢灭，火大快跑。")
    add("- 会逃生：低姿捂鼻走楼梯，电梯不坐物不拿。")
    add("")

    # 五 实操设计
    add("## 五、实操演练设计（主动给出）")
    add("")
    for i, s in enumerate(recipe["drill_steps"], 1):
        add(f"{i}. {s}")
    add("- 学生/未成年人培训不组织灭火实操，改为疏散演练与报警模拟。")
    add("")

    # 六 考核题库（主动）
    quiz_n = QUIZ_FOR_45 if duration_key == "45" else QUIZ_DEFAULT
    quiz = recipe["quiz_bank"][:quiz_n]
    add("## 六、考核题库（主动生成 %d 题，未要求也给出）" % quiz_n)
    add("")
    for i, q in enumerate(quiz, 1):
        add(f"{i}. {q['q']}")
        for o in q["opts"]:
            add(f"   - {o}")
        add(f"   - **答案：{q['answer']}** — {q['explain']}（{q['citation']}）")
        add("")
    add("- 考核形式建议：现场口头快问快答或扫码答题，80 分合格，不合格当场补训补考。")
    add("")

    # 七 培训记录留痕（主动）
    add("## 七、培训记录与留痕（主动提醒：这是合规证据）")
    add("")
    add(f"- {recipe['record_requirements']['text']}")
    add(f"- 依据：{recipe['record_requirements']['citation']}。")
    add("")

    # 八 复训计划（主动）
    add("## 八、复训计划（对照法定频次，主动给出）")
    add("")
    add(f"- {recipe['retrain_rules']['key_unit']}")
    add(f"- {recipe['retrain_rules']['assembly']}")
    add(f"- {recipe['retrain_rules']['new_staff']}")
    add(f"- {recipe['retrain_rules']['micro']}")
    add("")

    # 九 免责
    add("## 九、免责声明")
    add("")
    add(recipe["disclaimer"])
    add("")
    add("---")
    add("合规依据汇总：消防法（2021修正）第六、十六、十七、四十四条；公安部61号令第二十五、三十六、四十条；GB/T 40248-2021；GB/T 38315-2019；GB 55037-2022；GB/T 4968-2008；部令第5号；公消〔2015〕301号；消防〔2025〕33号。详见 `_foundation/regulations.json`。")
    add("")

    # 附 自查清单
    add("## 附：培训落地自查清单（逐项打勾）")
    add("")
    add("- [ ] 课件已按本单位重点部位补充真实场景（替换通用案例）")
    add("- [ ] 实操场地、器材、安全监护已落实（学生培训除外）")
    add("- [ ] 考核完成且不合格者已补训补考")
    add("- [ ] 签到表、照片、课件、成绩单四样存档")
    add("- [ ] 未覆盖的四个能力模块已列入复训计划")
    add("- [ ] 新员工岗前培训单独归档")
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
        recipe = load_recipe(os.path.join(here, "..", "resources", "recipe.json"))
        with open(in_path, "r", encoding="utf-8") as f:
            text = f.read()
        fields, leftovers = parse_input(text)
        aid, aud = detect_audience(text, recipe)
        duration_assumed = not fields.get("duration")
        duration_key = parse_duration(fields.get("duration", ""))
        mod_ids, emphasized = select_modules(recipe, aid, duration_key, fields.get("topics", ""))
        report = build_report(recipe, fields, leftovers, aid, aud, duration_key,
                              duration_assumed, mod_ids, emphasized,
                              gen_date())
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(report)
            print(f"OK 对象={aud['label']} 时长={recipe['duration_plans'][duration_key]['label']} 模块={len(mod_ids)} 题目={len(recipe['quiz_bank'][:QUIZ_FOR_45 if duration_key=='45' else QUIZ_DEFAULT])} 已写入 {out_path}")
            return 0
        else:
            print(report)
            return 0
    print("未知命令")
    return 2


if __name__ == "__main__":
    sys.exit(main())
