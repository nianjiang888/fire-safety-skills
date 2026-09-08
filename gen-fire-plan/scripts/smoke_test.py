#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-fire-plan 自包含冒烟测试。

断言维度：
- 三案例引擎实跑（全信息 / 缺演练 / 极简）行为自洽；
- 法规依据章节、组织机构表、火情预想、演练频次、微型消防站、自查清单均出现；
- 极简输入不崩溃、缺项标"待补充"、不编造重点部位场景；
- 规模系数缩放正确（1800人 → ×3，灭火行动组 9 人）；
- version / recipe 完整性 / 无价格词。

运行：python scripts/smoke_test.py
"""
import os
import subprocess
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "gen.py")
TMP = os.path.join(HERE, "_smoke_out.md")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def run_gen(in_name):
    r = subprocess.run([sys.executable, ENGINE, "gen",
                        os.path.join(PKG, "examples", in_name), TMP],
                       capture_output=True, text=True)
    rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
    return r, rep


# ---------- 案例一：写字楼全信息 ----------
r, rep = run_gen("plan-input-office.md")
check("office 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("office 画像=办公楼宇", "画像=办公楼宇" in r.stdout, r.stdout.strip()[:80])
for must in ["灭火和应急疏散预案", "法规依据", "应急组织机构", "火情预想",
             "应急疏散方案", "初起火灾扑救", "微型消防站联动", "演练计划",
             "善后与复盘", "免责声明", "落地自查清单"]:
    check("office 章节含《%s》" % must, must in rep)
check("office 法规出处 GB/T 38315-2019", "GB/T 38315-2019" in rep)
check("office 法规出处 消防法第十六条", "消防法第十六条" in rep)
check("office 火情预想命中配电室（电气短路）", "配电室" in rep and "严禁用水" in rep)
check("office 火情预想命中厨房", "油锅" in rep)
check("office 火情预想命中车库（新能源）", "复燃" in rep)
check("office 规模系数×3（1800人）", "系数 ×3" in rep)
check("office 灭火行动组 9 人", "| 9 |" in rep)
check("office 演练现状引用自述", "每年一次" in rep)
check("office 主动暴露待补充省/市字段不存在（已提供）", "所在省/市：**待补充**" not in rep)

# ---------- 案例二：商场缺演练 ----------
r, rep = run_gen("plan-input-mall.md")
check("mall 退出码=0", r.returncode == 0)
check("mall 画像=商业综合体", "商业综合体" in r.stdout + rep)
check("mall 现有预案=无 → 判定待补齐演练", "待补齐" in rep)
check("mall 火情预想命中影院（未匹配模板→专项研判）", "未匹配预设模板" in rep)
check("mall 重点部位厨房命中", "灭火毯" in rep)

# ---------- 案例三：极简输入 ----------
r, rep = run_gen("plan-input-minimal.md")
check("minimal 退出码=0（不崩溃）", r.returncode == 0)
check("minimal 缺项标待补充", "待补充" in rep)
check("minimal 不编造火情预想", "无法生成针对性火情预想" in rep)
check("minimal 仍输出完整预案骨架", "组织机构" in rep and "免责声明" in rep)
check("minimal 画像识别养老院", "医疗养老" in rep)

if os.path.isfile(TMP):
    os.remove(TMP)

# ---------- recipe 完整性 ----------
with open(os.path.join(PKG, "resources", "recipe.json"), encoding="utf-8") as f:
    recipe = json.load(f)
for key in ["profiles", "plan_basis", "org_groups", "response_steps",
            "key_area_scenarios", "drill_rules", "micro_station", "disclaimer"]:
    check("recipe 含 %s" % key, key in recipe)
check("recipe 组织机构 6 组", len(recipe["org_groups"]) == 6)
check("recipe 火情预想模板≥8", len(recipe["key_area_scenarios"]) >= 8)

# ---------- version ----------
r = subprocess.run([sys.executable, ENGINE, "version"], capture_output=True, text=True)
check("version 退出码=0", r.returncode == 0)
check("version 引擎版本", "gen-fire-plan 1.0.1" in r.stdout, r.stdout.strip())

# ---------- 参数错误 ----------
r = subprocess.run([sys.executable, ENGINE], capture_output=True, text=True)
check("无参数退出码=2", r.returncode == 2, "rc=%s" % r.returncode)

# ---------- 免费约束：全文无价格词（排除"付费能力预留"固定声明句） ----------
import re as _re
for rel in ["SKILL.md", "README.md", "FAQ.md"]:
    p = os.path.join(PKG, rel)
    if os.path.isfile(p):
        txt = open(p, encoding="utf-8").read()
        txt = _re.sub(r"[^\n。]*付费能力[^\n。]*[。\n]?", "", txt)
        bad = [w for w in ["价格", "付费", "充值", "订阅", "收费", "元/"] if w in txt]
        check("%s 无价格词" % rel, not bad, ",".join(bad))

# ---------- 汇总 ----------
fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + detail) if (detail and not ok) else ""))
print("-" * 46)
print("冒烟结果: %d PASS / %d FAIL" % (len(results) - len(fails), len(fails)))
sys.exit(0 if not fails else 1)
