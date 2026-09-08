#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-fire-hazard 自包含冒烟测试。

场景设计（确定性断言）：
- clean：模范小区月报，预期 rc=0、零命中、主动清单恰好 6 条（高层/物业场所特征 + 通用补齐）。
- mid：商业楼自查，预期 rc=1、红线 0 条、高危 3 条（器材失效/防火门楔住/私拉乱接）、提示 2 条（烟道油垢/无演练）。
- high：夜查记录，预期 rc=1、红线 7 条、高危 2 条，关键条款号出现在报告里。

运行：python scripts/smoke_test.py（在包内任意位置可跑，相对路径 + sys.executable）
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, os.pardir))
ENGINE = os.path.join(HERE, "check.py")
EX = os.path.join(PKG, "examples")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def run(args):
    return subprocess.run([sys.executable, ENGINE] + args, capture_output=True, text=True)


# ---------- clean ----------
r = run(["scan", os.path.join(EX, "fire-demo-clean.md")])
check("clean 退出码=0（零命中）", r.returncode == 0, "rc=%s out=%r" % (r.returncode, r.stdout[:120]))
rep = run(["scan", os.path.join(EX, "fire-demo-clean.md")])
# 用再次调用拿报告文件再读，保证测试的是落盘内容
tmp_out = os.path.join(EX, "_smoke_clean_out.md")
run(["scan", os.path.join(EX, "fire-demo-clean.md"), tmp_out])
rep = open(tmp_out, encoding="utf-8").read()
os.remove(tmp_out)
check("clean 输出'未发现可直接判定'", "未发现可直接判定的隐患" in rep)
check("clean 有主动自查清单", "主动自查清单" in rep)
n_pro = rep.count("- [ ]")
check("clean 主动清单恰好 6 条（防骚扰封顶）", n_pro == 6, "count=%d" % n_pro)
check("clean 含免责声明", "免责声明" in rep)
check("clean 无'红线隐患'小节", "红线隐患（涉嫌违反明文禁令" not in rep)

# ---------- mid ----------
tmp_out = os.path.join(EX, "_smoke_mid_out.md")
r = run(["scan", os.path.join(EX, "fire-demo-mid.md"), tmp_out])
rep = open(tmp_out, encoding="utf-8").read()
os.remove(tmp_out)
check("mid 退出码=1（有隐患）", r.returncode == 1, "rc=%s" % r.returncode)
check("mid 命中 6 条", "命中 6 条隐患" in rep, r.stdout.strip())
check("mid 红线 1 条（消火栓箱前堆物）", "| 红线（涉嫌违法） | 1 |" in rep)
check("mid 高危 3 条", "| 高危 | 3 |" in rep)
check("mid 提示 2 条", "| 提示 | 2 |" in rep)
for name in ["器材失效/超期未检", "常闭式防火门常开/损坏", "电气线路私拉乱接", "油烟管道未定期清洗", "员工消防培训缺失", "圈占遮挡消火栓/灭火器材"]:
    check("mid 含《%s》" % name, name in rep)
check("mid 条款号 消防法§28 在报告中", "消防法§28" in rep)
check("mid 处置优先级存在且封顶", "处置优先级（Top 6" in rep)

# ---------- high ----------
tmp_out = os.path.join(EX, "_smoke_high_out.md")
r = run(["scan", os.path.join(EX, "fire-demo-high.md"), tmp_out])
rep = open(tmp_out, encoding="utf-8").read()
os.remove(tmp_out)
check("high 退出码=1", r.returncode == 1, "rc=%s" % r.returncode)
check("high 红线 7 条", "| 红线（涉嫌违法） | 7 |" in rep)
check("high 高危 3 条（飞线同时命中电气隐患，双条款并列）", "| 高危 | 3 |" in rep)
for name in ["电动自行车楼道停放/充电", "锁闭/封堵安全出口", "占用堵塞疏散通道", "三合一场所违规住人",
             "消控室值班人员无证", "擅自停用消防设施", "违规动火作业", "常闭式防火门常开/损坏", "器材失效/超期未检"]:
    check("high 含《%s》" % name, name in rep)
check("high 条款号 部令5号§37 在报告中", "部令5号§37" in rep)
check("high 条款号 消防法§28 在报告中", "消防法§28" in rep)
check("high 电动车罚则区间 2000-10000 在报告中", "二千元以上一万元以下" in rep)
check("high 优先级清单 Top 8 封顶", "处置优先级（Top 8" in rep)

# ---------- version ----------
r = run(["version"])
check("version 退出码=0", r.returncode == 0)
check("version 输出引擎版本", "check-fire-hazard 1.0.1" in r.stdout, r.stdout.strip())
check("version 输出规则基数", "规则基数: 22" in r.stdout.replace("（", "（"), r.stdout.strip())

# ---------- 汇总 ----------
fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + detail) if (detail and not ok) else ""))
print("-" * 46)
print("冒烟结果: %d PASS / %d FAIL" % (len(results) - len(fails), len(fails)))
sys.exit(0 if not fails else 1)
