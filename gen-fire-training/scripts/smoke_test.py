#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-fire-training 自包含冒烟测试。

断言维度：
- 三案例引擎实跑（酒店全员45分钟 / 微型站半天 / 极简新员工）行为自洽；
- 受众识别：微型站、新员工不被泛化"员工"抢先；
- 选课：受众默认方案 ∪ 时长方案；显式主题标重点；
- 主动章节：考核题库、培训记录留痕、复训计划必然出现；
- 超课时校准提示；极简输入待补充不崩溃；
- version / recipe 完整性 / 无价格词。

运行：python scripts/smoke_test.py
"""
import os
import subprocess
import sys
import json
import re

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


# ---------- 案例一：酒店全员 45 分钟 ----------
r, rep = run_gen("train-input-staff.md")
check("staff 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("staff 对象=全体员工", "全体员工" in r.stdout, r.stdout.strip()[:80])
check("staff 时长=45 分钟", "45 分钟" in r.stdout + rep)
for must in ["法规依据", "四个能力", "课程大纲", "课件逐页内容", "实操演练设计",
             "考核题库", "培训记录与留痕", "复训计划", "免责声明", "落地自查清单"]:
    check("staff 章节含《%s》" % must, must in rep)
check("staff 重点主题疏散逃生标星", "重点主题已映射为标星模块" in rep and "会逃生" in rep)
check("staff 题库 6 题（45分钟口径）", rep.count("**答案：") == 6, str(rep.count("**答案：")))
check("staff 考核题带出处", "消防法第四十四条" in rep)
check("staff 超课时校准提示", "课时校准" in rep)
check("staff 四个能力映射输出", "组织疏散逃生能力" in rep)

# ---------- 案例二：微型站半天 ----------
r, rep = run_gen("train-input-micro.md")
check("micro 退出码=0", r.returncode == 0)
check("micro 对象=微型消防站队员", "微型消防站队员" in r.stdout)
check("micro 模块=8（受众∪时长方案）", "模块=8" in r.stdout, r.stdout.strip()[:80])
check("micro 微型站响应模块在列", "微型站响应与处置流程" in rep)
check("micro 3分钟到场出处", "公消〔2015〕301号" in rep)
check("micro 灭火器实操步骤", "提、拔、握、压" in rep)
check("micro 题库 10 题", rep.count("**答案：") == 10, str(rep.count("**答案：")))

# ---------- 案例三：极简新员工 ----------
r, rep = run_gen("train-input-minimal.md")
check("minimal 退出码=0（不崩溃）", r.returncode == 0)
check("minimal 识别新员工岗前（不被'员工'抢先）", "新员工岗前" in r.stdout, r.stdout.strip()[:80])
check("minimal 时长默认90并标假设", "已默认按 90 分钟" in rep)
check("minimal 缺项标待补充", "待补充" in rep)
check("minimal 岗前培训留痕提醒", "未经培训不得上岗" in rep or "新员工上岗前" in rep)

if os.path.isfile(TMP):
    os.remove(TMP)

# ---------- recipe 完整性 ----------
with open(os.path.join(PKG, "resources", "recipe.json"), encoding="utf-8") as f:
    recipe = json.load(f)
for key in ["audiences", "legal_basis", "module_library", "duration_plans",
            "drill_steps", "quiz_bank", "record_requirements", "retrain_rules", "disclaimer"]:
    check("recipe 含 %s" % key, key in recipe)
check("recipe 模块库≥10", len(recipe["module_library"]) >= 10, str(len(recipe["module_library"])))
check("recipe 题库≥10", len(recipe["quiz_bank"]) >= 10)
check("recipe 每模块挂出处", all(m.get("citation") for m in recipe["module_library"]))
check("recipe 每题挂出处+答案", all(q.get("citation") and q.get("answer") for q in recipe["quiz_bank"]))

# ---------- version / 参数 ----------
r = subprocess.run([sys.executable, ENGINE, "version"], capture_output=True, text=True)
check("version 退出码=0", r.returncode == 0)
check("version 引擎版本", "gen-fire-training 1.0.1" in r.stdout, r.stdout.strip())
r = subprocess.run([sys.executable, ENGINE], capture_output=True, text=True)
check("无参数退出码=2", r.returncode == 2, "rc=%s" % r.returncode)

# ---------- 免费约束 ----------
for rel in ["SKILL.md", "README.md", "FAQ.md"]:
    p = os.path.join(PKG, rel)
    if os.path.isfile(p):
        txt = open(p, encoding="utf-8").read()
        txt = re.sub(r"[^\n。]*付费能力[^\n。]*[。\n]?", "", txt)
        bad = [w for w in ["价格", "付费", "充值", "订阅", "收费", "元/"] if w in txt]
        check("%s 无价格词" % rel, not bad, ",".join(bad))

# ---------- 汇总 ----------
fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + detail) if (detail and not ok) else ""))
print("-" * 46)
print("冒烟结果: %d PASS / %d FAIL" % (len(results) - len(fails), len(fails)))
sys.exit(0 if not fails else 1)
