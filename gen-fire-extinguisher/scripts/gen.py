#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-fire-extinguisher —— 灭火器配置顾问（FIre 消防技能系列，v1.0.1）

定位：主动 Agent。用户填一张信息卡（key: value，缺项可跑），引擎按 GB 50140-2005：
  1. 判定火灾种类与危险等级（每项判定挂条款依据；材料不足时保守取值并主动说明）
  2. 透明算式计算最小需配灭火级别 Q=K·S/U（商场/网吧/地下等 1.3 加严，第 7.3.3 条）
  3. 按最大保护距离反推设置点数，逐点给出型号/数量/灭火级别（附录 A 举例库）
  4. 若提供了现有灭火器，做达标核查（数量、单具级别、总级别三重比对）
  5. 主动缺口：没给的信息列出"补齐后可精确化"清单；D 类场所直接转专业设计
主动但不骚扰：单次运行出一份方案书，不轮询、不追问。

命令：
  gen <input> [output]    生成配置方案书（缺省打印到 stdout）
  version                 打印版本
  recipe                  打印配方基数

退出码：0 = 生成成功（含配置核查达标）；1 = 现有配置核查不达标；2 = 参数/输入错误。
纯标准库，零依赖。输出 UTF-8 + LF。
"""

import json
import math
import os
import re
import sys

ENGINE_VERSION = "1.0.1"
ENGINE_NAME = "gen-fire-extinguisher"

RECIPE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "resources", "recipe.json")


def load_recipe():
    with open(RECIPE_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 信息卡解析
# ---------------------------------------------------------------------------

FIELD_ALIASES = {
    "name": ["场所名称", "名称", "单位名称"],
    "type": ["场所类型", "类型", "用途", "场所用途"],
    "area": ["面积", "建筑面积", "保护面积"],
    "classes": ["火灾种类", "火灾类别", "火灾类型"],
    "severity": ["危险等级", "等级", "危险级别"],
    "floor": ["楼层", "所在楼层"],
    "hydrant": ["室内消火栓", "消火栓", "消火栓系统"],
    "suppression": ["自动灭火系统", "灭火系统", "喷淋", "自动喷淋"],
    "diagonal": ["最长对角线", "对角线", "最长边"],
    "existing": ["现有灭火器", "现有配置", "已有灭火器"],
}


def parse_card(text):
    """解析 key: value 信息卡；返回 {canonical_field: (raw_value, raw_key)} 与未识别行。"""
    fields, unknown = {}, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.split(r"[：:]", line, maxsplit=1)
        if len(m) != 2 or not m[0].strip():
            unknown.append(line)
            continue
        key, val = m[0].strip(), m[1].strip()
        canon = None
        for c, aliases in FIELD_ALIASES.items():
            if key in aliases:
                canon = c
                break
        if canon is None:
            for c, aliases in FIELD_ALIASES.items():
                if key and any(key.endswith(a) or a in key for a in aliases if len(a) >= 2):
                    canon = c
                    break
        if canon:
            if canon == "classes":
                fields.setdefault(canon, [])
                fields[canon].append((val, key))
            else:
                fields[canon] = (val, key)
        else:
            unknown.append(line)
    return fields, unknown


def fnum(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s or "")
    return float(m.group(1)) if m else None


def tri_state(s):
    """有/无/未提供 三态。"""
    if not s:
        return "unknown"
    s = s.strip()
    if re.search(r"未提供|不清楚|不确定", s):
        return "unknown"
    if re.search(r"无|没有|未设|没有设", s):
        return "no"
    if re.search(r"有|设|安装|配备|已建", s):
        return "yes"
    return "unknown"


def parse_classes(vals, rtype_text):
    """火灾种类：显式 > 关键词推断。返回 (letters, basis_str)。"""
    letters = set()
    src = []
    if vals:
        for v, _k in vals:
            for ch in "ABCDE":
                if re.search(r"\b%s\b|(%s类)" % (ch, ch), v) or ("固体" in v and ch == "A") \
                        or ("液体" in v and ch == "B") or ("气体" in v and ch == "C") \
                        or ("金属" in v and ch == "D") or ("带电" in v and ch == "E"):
                    letters.add(ch)
                    src.append("用户指定")
    if not letters:
        for rule in load_recipe()["class_keywords"]:
            if any(t in rtype_text for t in rule["terms"]):
                letters.add(rule["class"])
                src.append("按场所关键词自动推断")
        # A 类为兜底（固体可燃物几乎处处存在）
        if not letters:
            letters.add("A")
            src.append("未识别到明确特征，按含可燃固体兜底")
    return letters, "、".join(sorted(src)) if src else ""


def infer_severity(rtype_text, explicit, recipe):
    """危险等级：显式 > 规则匹配 > 默认中危（保守）。返回 (level, basis, is_default)。"""
    if explicit:
        for lv in ("严重危险级", "中危险级", "轻危险级"):
            if lv.replace("危险级", "") in explicit or lv in explicit:
                return lv, "用户指定（等级判定责任在用户，建议对照 GB 50140-2005 附录C/附录D 复核）", False
    for rule in recipe["severity_rules"]:
        if any(t in rtype_text for t in rule["terms"]):
            return rule["level"], rule["basis"] + "。" + rule.get("note", ""), False
    d = recipe["severity_default"]
    return d["level"], d["reason"], True


# ---------------------------------------------------------------------------
# 核心计算
# ---------------------------------------------------------------------------

def benchmark_key(letters):
    """基准类别：B/C 走 B 基准；否则 A 基准（E 随主类，第 6.2.4 条）。"""
    if "B" in letters or "C" in letters:
        return "B"
    return "A"


def pick_plan(qe, min_rating, cands):
    """选单点配置：优先总级别最小（精确满足），其次具数少；受 6.1.2 每点 ≤5 具约束。"""
    best = None
    for c in cands:
        if c["rating"] < min_rating:
            continue
        n_units = math.ceil(qe / c["rating"])
        if n_units > 5:
            continue
        cost = (n_units * c["rating"], n_units)
        if best is None or cost < best["cost"]:
            best = {"model": c["model"], "agent": c["agent"], "charge": c["charge"],
                    "rating": c["rating"], "units": n_units, "cost": cost}
    return best


def compute(fields, recipe):
    notes = []       # 主动说明（保守取值/推断依据）
    gaps = []        # 主动缺口：补齐后可精确化
    warnings = []    # 警示（非阻断）

    name = fields.get("name", ("（未提供）", ""))[0]
    rtype = fields.get("type", ("", ""))[0]
    area = fnum(fields.get("area", ("", ""))[0])
    diag = fnum(fields.get("diagonal", ("", ""))[0])

    if area is None or area <= 0:
        return {"error": "missing_area"}

    # 火灾种类与危险等级
    cls_vals = fields.get("classes", [])
    letters, cls_basis = parse_classes(cls_vals, rtype)
    sev_explicit = fields.get("severity", ("", ""))[0]
    severity, sev_basis, sev_default = infer_severity(rtype, sev_explicit, recipe)
    sev_key = {"严重危险级": "severe", "中危险级": "mid", "轻危险级": "light"}[severity]

    if "D" in letters:
        return {"error": "d_class", "letters": letters, "severity": severity, "name": name,
                "selection": recipe["selection"]["D"]}

    # 修正系数 K（表 7.3.2）
    hyd = tri_state(fields.get("hydrant", ("", ""))[0])
    sup = tri_state(fields.get("suppression", ("", ""))[0])
    if hyd == "yes" and sup == "yes":
        k, k_desc = 0.5, "设有室内消火栓系统和灭火系统"
    elif hyd == "yes":
        k, k_desc = 0.9, "设有室内消火栓系统"
    elif sup == "yes":
        k, k_desc = 0.7, "设有灭火系统"
    else:
        k, k_desc = 1.0, "未设室内消火栓系统和灭火系统"
    if hyd == "unknown" or sup == "unknown":
        notes.append("消火栓/自动灭火系统信息未提供，K 按 1.0 保守取值（不折减、宁可多配）。"
                     "补齐后：仅设消火栓 K=0.9，仅设灭火系统 K=0.7，两者都有 K=0.5（表 7.3.2）。")
        gaps.append("提供室内消火栓与自动灭火系统设置情况（K 可从 1.0 折减至 0.9/0.7/0.5，直接减少数量）")
    if hyd == "no" and sup == "no":
        k, k_desc = 1.0, "未设室内消火栓系统和灭火系统"

    # 1.3 加严（第 7.3.3 条）
    full_text = rtype + " " + name
    surcharge = any(t in full_text for t in recipe["surcharge_1_3"]["terms"])

    bkey = benchmark_key(letters)
    bench = recipe["min_benchmark"][bkey][sev_key]
    U, min_rating = bench["U"], bench["min_rating"]
    unit = recipe["min_benchmark"][bkey]["unit"]

    # 住宅特殊路径（第 6.1.3 条）
    residential = "住宅" in rtype or "居民楼" in rtype
    if residential and bkey == "A":
        if area > 100:
            n_res = math.ceil(area / 100.0)
            plan_text = "住宅楼每层公共部位按第 6.1.3 条：配置 %d 具 1A 手提式灭火器（每层，按 %gm² 计算）。" % (n_res, area)
            return {"name": name, "residential": True, "plan_text": plan_text,
                    "letters": sorted(letters), "severity": severity, "notes": notes, "gaps": gaps,
                    "warnings": warnings, "sev_basis": sev_basis, "cls_basis": cls_basis, "exit": 0}
        plan_text = "住宅每层公共部位建筑面积未超过 100m²，第 6.1.3 条未作强制要求；建议仍按每层 1 具 1A 配置作为良好实践。"
        return {"name": name, "residential": True, "plan_text": plan_text,
                "letters": sorted(letters), "severity": severity, "notes": notes, "gaps": gaps,
                "warnings": warnings, "sev_basis": sev_basis, "cls_basis": cls_basis, "exit": 0}

    # Q 计算（7.3.1 / 7.3.3）
    raw = k * area / U
    if surcharge:
        raw *= 1.3
    q = math.ceil(raw)

    # 保护距离与设置点数（表 5.2.1/5.2.2 + 7.1.3）
    dist_key = "A" if bkey == "A" else "BC"
    R = recipe["travel_distance"][dist_key][sev_key]
    if diag:
        n_points = max(1, math.ceil(diag / (2.0 * R)))
        n_basis = "按最长对角线 %gm 与保护半径 %dm 布点（对角线/2R 进位）" % (diag, R)
    else:
        n_points = max(1, math.ceil(area / (math.pi * R * R)))
        n_basis = "按保护圆覆盖近似：面积/(πR²)，R=%dm（未提供最长对角线，取下限值）" % R
        gaps.append("提供计算单元的最长对角线（或最长边）长度，可将设置点数从保护圆近似值精确化为实际布点数")

    # 逐点配置
    cands = recipe["extinguisher_db"]["A_candidates" if bkey == "A" else "B_candidates"]
    # 先按当前 N 求 Qe，若单点装不下（>5具）则增点重分摊
    while True:
        qe = math.ceil(q / n_points)
        plan = pick_plan(qe, min_rating, cands)
        if plan is None:
            n_points += 1
            if n_points > 60:
                return {"error": "too_large"}
            continue
        break
    # 6.1.1 单元内不少于 2 具
    if plan["units"] * n_points < 2:
        best = None
        for c in cands:
            if c["rating"] < min_rating:
                continue
            n_u = max(math.ceil(qe / c["rating"]), math.ceil(2.0 / n_points))
            if n_u > 5:
                continue
            cand = {"model": c["model"], "agent": c["agent"], "charge": c["charge"],
                    "rating": c["rating"], "units": n_u, "cost": (n_u * c["rating"], n_u)}
            if best is None or cand["cost"] < best["cost"]:
                best = cand
        if best:
            plan = best

    # 现有配置核查
    existing_verdict = None
    existing_raw = fields.get("existing", ("", ""))[0]
    if existing_raw:
        existing_verdict = verify_existing(existing_raw, q, qe, min_rating, unit, recipe, bkey)

    # 现有配置红线 / E 类警示等
    if "E" in letters:
        warnings.append("场所含带电设备（E类火灾，第3.1.2条）：可选磷酸铵盐干粉或二氧化碳灭火器，"
                        "但不得选用装有金属喇叭喷筒的二氧化碳灭火器（第4.2.5条，强制性条文）。")
    if re.search(r"溶剂|酒精|甲醇|丙酮", rtype):
        warnings.append("检测到极性溶剂线索：极性溶剂的 B 类火灾场所应选择抗溶性灭火器（第 4.2.2 条）。")
    if re.search(r"灭火器箱.{0,6}(上锁|锁闭)|箱.{0,4}锁", full_text):
        warnings.append("灭火器箱不得上锁（第 5.1.3 条）。材料中出现上锁表述，请立即整改。")
    if sev_default:
        gaps.append("提供可判定危险等级的场所细节（附录 C/D 举例口径），当前按中危险级保守计算")

    return {
        "error": None, "name": name, "rtype": rtype, "area": area,
        "letters": sorted(letters), "cls_basis": cls_basis,
        "severity": severity, "sev_basis": sev_basis, "sev_default": sev_default,
        "k": k, "k_desc": k_desc, "surcharge": surcharge,
        "U": U, "unit": unit, "min_rating": min_rating, "raw": raw, "q": q,
        "R": R, "n_points": n_points, "n_basis": n_basis, "qe": qe, "plan": plan,
        "bkey": bkey, "notes": notes, "gaps": gaps, "warnings": warnings,
        "existing": existing_verdict,
        "exit": 1 if (existing_verdict is not None and existing_verdict["pass"] is False) else 0,
    }


def best_cost(p):
    return p["cost"]


def verify_existing(raw, q, qe, min_rating, unit, recipe, bkey="A"):
    """解析现有配置，三重比对：总数量、单具级别、总级别。型号库按基准类别取（防 A/B 同型号串表）。"""
    db = {}
    for c in recipe["extinguisher_db"]["A_candidates" if bkey == "A" else "B_candidates"]:
        db[c["model"].upper()] = c
    items = re.findall(r"(\d+)\s*具?\s*([A-Za-z/]+\d+)", raw.replace("／", "/"))
    total_units, total_rating, unknown_models = 0, 0.0, []
    min_seen = None
    for cnt, model in items:
        c = db.get(model.upper().replace("MFZ", "MF").replace("MTZ", "MT"))
        if c is None or not c["rating"]:
            unknown_models.append(model)
            continue
        total_units += int(cnt)
        total_rating += int(cnt) * c["rating"]
        if min_seen is None or c["rating"] < min_seen:
            min_seen = c["rating"]
    if not items:
        return {"pass": None, "reason": "未检测到有效的现有灭火器配置（需为'N具 型号'格式；未配置的填'暂未配置'即可）。", "items": []}
    checks = []
    ok = True
    if total_units < 2:
        ok = False
        checks.append("数量 %d 具 < 计算单元最少 2 具（第 6.1.1 条，强制性条文）" % total_units)
    else:
        checks.append("数量 %d 具，满足计算单元最少 2 具（第 6.1.1 条）" % total_units)
    if min_seen is not None and min_seen < min_rating:
        ok = False
        checks.append("单具灭火级别最低为 %g%s，低于%s场所单具最低配置 %g%s（表 6.2.%s，强制性条文）"
                      % (min_seen, unit, {"A": "A", "B": "B"}[unit], min_rating, unit, "1" if unit == "A" else "2"))
    elif min_seen is not None:
        checks.append("单具级别 %g%s ≥ 单具最低配置 %g%s，满足" % (min_seen, unit, min_rating, unit))
    if total_rating < q:
        ok = False
        checks.append("总灭火级别 %g%s < 最小需配 %g%s（第 7.1.2 条，强制性条文）" % (total_rating, unit, q, unit))
    else:
        checks.append("总灭火级别 %g%s ≥ 最小需配 %g%s，满足（第 7.1.2 条）" % (total_rating, unit, q, unit))
    if unknown_models:
        checks.append("未能识别的型号：%s（请按铭牌灭火级别人工复核）" % "、".join(unknown_models))
    return {"pass": ok, "checks": checks, "items": items, "total_units": total_units, "total_rating": total_rating}


# ---------------------------------------------------------------------------
# 报告渲染
# ---------------------------------------------------------------------------

def class_names(letters):
    m = {"A": "A类固体", "B": "B类液体（可熔化固体）", "C": "C类气体", "D": "D类金属", "E": "E类带电"}
    return "、".join(m.get(c, c) for c in letters)


def render(r, recipe, src_name):
    L = []
    ap = L.append
    ap("# 灭火器配置方案书")
    ap("")
    ap("> 引擎 %s v%s | FIre 消防技能系列 | 输入：%s | 依据：%s" % (ENGINE_NAME, ENGINE_VERSION, src_name, recipe["standard"]["name"]))
    ap("")
    ap("## 一、输入与假设")
    ap("")
    ap("- 场所名称：%s" % r["name"])
    ap("- 场所类型：%s" % (r["rtype"] or "（未提供）"))
    ap("- 计算单元保护面积 S = %gm²（按建筑面积口径，第 7.2.2 条）" % r["area"])
    ap("- 火灾种类：%s（%s）" % (class_names(r["letters"]), r["cls_basis"]))
    ap("- 危险等级：%s（%s）" % (r["severity"], r["sev_basis"]))
    ap("- 修正系数 K = %s（%s，表 7.3.2）" % (r["k"], r["k_desc"]))
    if r["surcharge"]:
        ap("- 加严系数：本场所适用 1.3 倍加严（第 7.3.3 条：歌舞娱乐放映游艺场所、网吧、商场、寺庙以及地下场所）")
    ap("")
    if r["notes"]:
        ap("**主动说明（材料不足处的保守处理）**")
        ap("")
        for n in r["notes"]:
            ap("- %s" % n)
        ap("")
    ap("## 二、计算过程（算式透明，可复算）")
    ap("")
    ap("- 单位灭火级别最大保护面积 U = %gm²/%s（表 6.2.%s，强制性条文）" % (r["U"], r["unit"], "1" if r["unit"] == "A" else "2"))
    if r["surcharge"]:
        ap("- Q = 1.3 × K × S / U = 1.3 × %s × %g / %g = %.2f → 进位取整 **Q = %d%s**（第 7.3.3、7.1.1 条）" % (r["k"], r["area"], r["U"], r["raw"], r["q"], r["unit"]))
    else:
        ap("- Q = K × S / U = %s × %g / %g = %.2f → 进位取整 **Q = %d%s**（第 7.3.1、7.1.1 条）" % (r["k"], r["area"], r["U"], r["raw"], r["q"], r["unit"]))
    ap("- 最大保护距离 R = %dm（%s）" % (r["R"], recipe["travel_distance"]["A" if r["bkey"] == "A" else "BC"]["note"]))
    ap("- 设置点数 N：%s → **N = %d 个**（第 7.1.3 条：应保证最不利点至少在 1 具灭火器保护范围内）" % (r["n_basis"], r["n_points"]))
    ap("- 每个设置点最小需配灭火级别 Qe = Q / N = %d%s（第 7.3.4 条）" % (r["qe"], r["unit"]))
    ap("")
    ap("## 三、配置清单")
    ap("")
    ap("| 项目 | 配置 |")
    ap("|---|---|")
    ap("| 单具最低配置灭火级别 | %g%s（表 6.2.%s） |" % (r["min_rating"], r["unit"], "1" if r["unit"] == "A" else "2"))
    ap("| 每个设置点 | %s %d 具（%s，单具 %g%s） |" % (r["plan"]["model"], r["plan"]["units"], r["plan"]["charge"], r["plan"]["rating"], r["unit"]))
    ap("| 设置点数 | %d 个 |" % r["n_points"])
    ap("| 合计 | %d 具，总级别 %g%s ≥ Q=%d%s |" % (r["plan"]["units"] * r["n_points"], r["plan"]["units"] * r["plan"]["rating"] * r["n_points"], r["unit"], r["q"], r["unit"]))
    ap("")
    ap("- 型号依据：%s" % recipe["extinguisher_db"]["note"])
    ap("- 选型依据：%s" % recipe["selection"]["A" if r["bkey"] == "A" else ("C" if "C" in r["letters"] else "B")])
    ap("- 若场所同时存在多类火灾，宜选用相同类型和操作方法的通用型灭火器（第 4.1.2 条）；混用两类以上灭火器时须采用相容灭火剂（第 4.1.3 条，强制性条文）。")
    ap("")
    ap("## 四、设置要求（安装时逐条对照）")
    ap("")
    for s in recipe["setting_requirements"]:
        ap("- %s" % s)
    ap("")
    if r["warnings"]:
        ap("## 五、警示")
        ap("")
        for w in r["warnings"]:
            ap("- %s" % w)
        ap("")
    if r["existing"]:
        verdict = r["existing"]["pass"]
        if verdict is None:
            ap("## 现有配置核查（未提供有效配置）")
            ap("")
            ap("- %s" % r["existing"]["reason"])
        else:
            ap("## 现有配置核查（结论：%s）" % ("达标" if verdict else "不达标"))
            ap("")
            for c in r["existing"]["checks"]:
                ap("- %s" % c)
        ap("")
    ap("## 主动缺口（补齐后方案可精确化）")
    ap("")
    if r["gaps"]:
        for g in r["gaps"]:
            ap("- %s" % g)
    else:
        ap("- 无：信息卡要素齐全，本方案已按可用信息精确化。")
    ap("")
    ap("## 验收自查清单")
    ap("")
    ap("1. 实配总级别 ≥ Q，每点实配级别与数量 ≥ Qe 与计算值（第 7.1.2 条，强制性条文）")
    ap("2. 计算单元内总数 ≥ 2 具，每点 ≤ 5 具（第 6.1.1、6.1.2 条）")
    ap("3. 最不利点在 1 具灭火器保护范围内，实际布点未跨越防火分区和楼层（第 7.1.3、7.2.1 条）")
    ap("4. 设置位置明显易取、不影响疏散；箱不上锁；顶离地 ≤1.50m、底离地 ≥0.08m（第 5.1.1、5.1.3 条）")
    ap("5. 在工程设计图上标明型号、数量与位置（第 1.0.3 条）")
    ap("")
    ap("## 免责声明")
    ap("")
    ap("- %s" % recipe["disclaimer"])
    ap("")
    return "\n".join(L)


def render_d_class(r, recipe):
    L = []
    ap = L.append
    ap("# 灭火器配置方案书（D 类火灾场所：转专业设计）")
    ap("")
    ap("- 场所：%s" % r["name"])
    ap("- 材料显示该场所涉及 %s。D 类金属火灾场所：" % class_names(r["letters"]))
    ap("- 应选择扑灭金属火灾的专用灭火器（第 4.2.4 条，强制性条文）；")
    ap("- 其最大保护距离应根据具体情况研究确定（第 5.2.3 条），最低配置基准应根据金属的种类、物态及其特性等研究确定（第 6.2.3 条）。")
    ap("- 因此规范未提供通用查表基准，本工具不生成数量，避免误导。")
    ap("")
    ap("- 选型依据：%s" % recipe["selection"]["D"])
    ap("")
    ap("- %s" % recipe["disclaimer"])
    ap("")
    return "\n".join(L)


def render_residential(r):
    L = []
    ap = L.append
    ap("# 灭火器配置方案书（住宅楼公共部位）")
    ap("")
    ap("- 场所：%s" % r["name"])
    ap("- 火灾种类：%s（%s）" % (class_names(r["letters"]), r["cls_basis"]))
    ap("- %s" % r["plan_text"])
    ap("- 依据：GB 50140-2005 第 6.1.3 条。")
    if r["gaps"]:
        ap("")
        ap("## 主动缺口")
        ap("")
        for g in r["gaps"]:
            ap("- %s" % g)
    ap("")
    ap("- %s" % "本方案基于自述信息生成，不构成消防设计文件。")
    ap("")
    return "\n".join(L)


def print_summary(r):
    if r.get("error") == "missing_area":
        print("错误: 未提供面积（面积/建筑面积字段）")
        return
    if r.get("error") == "d_class":
        print("D 类火灾场所：已转专业设计提示（不生成数量）")
        return
    if r.get("residential"):
        print("住宅路径: %s" % r["plan_text"])
        return
    print("Q=%d%s  R=%dm  N=%d  Qe=%d%s  每点 %s×%d具  合计%d具" % (
        r["q"], r["unit"], r["R"], r["n_points"], r["qe"], r["unit"],
        r["plan"]["model"], r["plan"]["units"], r["plan"]["units"] * r["n_points"]))
    if r.get("existing"):
        v = r["existing"]["pass"]
        label = "达标" if v else ("不达标" if v is False else "未提供有效配置")
        print("现有配置核查: %s" % label)


def main(argv):
    if len(argv) < 2:
        print("用法: gen.py gen <input> [output] | recipe | version", file=sys.stderr)
        return 2
    cmd = argv[1]
    recipe = load_recipe()

    if cmd == "version":
        print("%s %s" % (ENGINE_NAME, ENGINE_VERSION))
        return 0
    if cmd == "recipe":
        n = len(recipe["extinguisher_db"]["A_candidates"]) + len(recipe["extinguisher_db"]["B_candidates"])
        print("火灾五类判据:%d  等级规则:%d  K表:%d  型号库:%d  通用规则:%d  版本:%s" % (
            len(recipe["class_keywords"]), len(recipe["severity_rules"]), len(recipe["k_table"]), n,
            len(recipe["general_rules"]), ENGINE_VERSION))
        return 0
    if cmd != "gen":
        print("未知命令: %s" % cmd, file=sys.stderr)
        return 2
    if len(argv) < 3:
        print("gen 需要 <input> 路径", file=sys.stderr)
        return 2
    in_path = argv[2]
    out_path = argv[3] if len(argv) > 3 else None
    if not os.path.isfile(in_path):
        print("输入文件不存在: %s" % in_path, file=sys.stderr)
        return 2
    if os.path.getsize(in_path) > 4 * 1024 * 1024:
        print("输入超过 4MB 上限", file=sys.stderr)
        return 2
    with open(in_path, encoding="utf-8") as f:
        text = f.read()

    fields, _unknown = parse_card(text)
    r = compute(fields, recipe)

    if r.get("error") == "missing_area":
        report = ("# 灭火器配置方案书（无法生成）\n\n信息卡缺少\"面积\"字段。请补充一行：\n\n"
                  "面积: 例如 450 平方米\n\n本工具按 GB 50140-2005 需要计算单元保护面积 S 才能计算（第 7.3.1 条）。"
                  "\n\n宁可留白不可错配：没有面积就不出数，避免给出错误的配置量。\n")
        code = 2
    elif r.get("error") == "d_class":
        report = render_d_class(r, recipe)
        code = 0
    elif r.get("residential"):
        report = render_residential(r)
        code = 0
    else:
        report = render(r, recipe, os.path.basename(in_path))
        code = r["exit"]

    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(report)
        print("方案书已写入: %s" % out_path)
    else:
        print(report)
    print_summary(r)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
