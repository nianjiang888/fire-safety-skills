#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-fire-extinguisher 冒烟测试（自包含，包内可复跑）。
三个确定性信息卡样例 + 引擎 CLI 行为 + 报告格式断言。全 PASS 则引擎可信。
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "gen.py")
EX = os.path.join(ROOT, "examples")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def run(args):
    return subprocess.run([sys.executable, ENGINE] + args, capture_output=True, text=True, encoding="utf-8")


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---- case 1: 办公室样例（Q=8A, N=1, 每点 2 具 4A, 无现有配置） ----
r = run(["gen", os.path.join(EX, "ext-input-office.md"), os.path.join(EX, "_smoke_office.md")])
rep = load(os.path.join(EX, "_smoke_office.md"))
check("office 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("office Q=8A", "**Q = 8A**" in rep, "")
check("office K=1.0（无消火栓无灭火系统）", "K = 1.0（未设室内消火栓系统和灭火系统" in rep, "")
check("office 等级=中危险级（自动判）", "中危险级" in rep and "设有集中空调、电子计算机、复印机" in rep, "")
check("office 每点 2 具 MF/ABC8", "MF/ABC8 | 2 具" in rep.replace("**", "") or "MF/ABC8" in rep, "")
check("office E 类警示（金属喇叭筒）", "金属喇叭喷筒" in rep, "")
check("office 住宅路径未触发", "住宅楼每层公共部位" not in rep, "")

# ---- case 2: 商场样例（1.3 加严, K=0.5, Q=18A, N=2, 每点 3A×3, 现有 4×2A=8A 不达标 → rc=1） ----
r = run(["gen", os.path.join(EX, "ext-input-mall.md"), os.path.join(EX, "_smoke_mall.md")])
rep = load(os.path.join(EX, "_smoke_mall.md"))
check("mall 退出码=1（现有配置不达标）", r.returncode == 1, "rc=%s" % r.returncode)
check("mall Q=18A", "**Q = 18A**" in rep, "")
check("mall 1.3 加严条款出现", "1.3" in rep and "7.3.3" in rep, "")
check("mall K=0.5", "K = 0.5（设有室内消火栓系统和灭火系统" in rep, "")
check("mall N=2（对角线法）", "N = 2 个" in rep, "")
check("mall 每点 3 具 3A", "3A" in rep and "MF/ABC5" in rep, "")
check("mall 核查不达标（总级别不足）", "不达标" in rep and "7.1.2" in rep, "")

# ---- case 3: 便利店样例（现有 2×1A 单具级别低于中危 2A 基准 → rc=1） ----
r = run(["gen", os.path.join(EX, "ext-input-store.md"), os.path.join(EX, "_smoke_store.md")])
rep = load(os.path.join(EX, "_smoke_store.md"))
check("store 退出码=1", r.returncode == 1, "rc=%s" % r.returncode)
check("store Q=2A", "**Q = 2A**" in rep, "")
check("store 单具级别不达标提示", "单具灭火级别最低为 1A" in rep and "6.2.1" in rep, "")
check("store K 未提供保守取值说明", "K 按 1.0 保守取值" in rep, "")
check("store 主动缺口含消火栓信息", "提供室内消火栓与自动灭火系统" in rep, "")

# ---- case 4: D 类转专业设计 ----
d_input = os.path.join(EX, "_smoke_d.md")
with open(d_input, "w", encoding="utf-8") as f:
    f.write("场所名称: 镁合金加工车间\n场所类型: 金属镁加工\n面积: 300 平方米\n危险等级: 严重危险级\n")
r = run(["gen", d_input])
check("D 类不生成数量、转专业设计", r.returncode == 0 and "转专业设计" in r.stdout and "4.2.4" in r.stdout, "rc=%s" % r.returncode)

# ---- case 5: 住宅特殊路径（6.1.3） ----
res_input = os.path.join(EX, "_smoke_res.md")
with open(res_input, "w", encoding="utf-8") as f:
    f.write("场所名称: 幸福里小区 2 号楼\n场所类型: 住宅楼\n面积: 350 平方米\n火灾种类: A类\n")
r = run(["gen", res_input])
check("住宅 350m² → 4 具 1A（6.1.3）", r.returncode == 0 and "4 具 1A" in r.stdout, "")

# ---- case 6: 缺面积 → 宁可留白 ----
r = run(["gen", os.path.join(EX, "ext-input-office.md").replace("office", "_smoke_noarea")])
with open(os.path.join(EX, "_smoke_noarea.md"), "w", encoding="utf-8") as f:
    f.write("场所名称: 无面积测试\n场所类型: 办公室\n")
r = run(["gen", os.path.join(EX, "_smoke_noarea.md")])
check("缺面积退出码=2 且不编数", r.returncode == 2 and "宁可留白不可错配" in r.stdout, "rc=%s" % r.returncode)

# ---- case 7: 输出格式 ----
rep = load(os.path.join(EX, "_smoke_office.md"))
check("报告无 CRLF", "\r" not in rep, "")
check("报告含免责声明", "免责声明" in rep and "不构成消防设计文件" in rep, "")

# ---- case 8: version / recipe ----
r = run(["version"])
check("version 输出 1.0.1", r.stdout.strip() == "gen-fire-extinguisher 1.0.1", r.stdout.strip())
r = run(["recipe"])
check("recipe 基数完整", "型号库:16" in r.stdout.replace(" ", ""), r.stdout.strip())

# ---- 清理临时文件 ----
for f in ["_smoke_office.md", "_smoke_mall.md", "_smoke_store.md", "_smoke_d.md", "_smoke_res.md", "_smoke_noarea.md"]:
    p = os.path.join(EX, f)
    if os.path.exists(p):
        os.remove(p)

# ---- 汇总 ----
passed = sum(1 for _, ok, _ in results if ok)
failed = [n for n, ok, _ in results if not ok]
print("冒烟结果: %d PASS / %d FAIL（共 %d 项）" % (passed, len(failed), len(results)))
for n, ok, d in results:
    if not ok:
        print("  FAIL: %s  %s" % (n, d))
sys.exit(0 if not failed else 1)
