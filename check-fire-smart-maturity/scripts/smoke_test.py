#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-fire-smart-maturity 冒烟测试（自包含，包内可复跑）。
三个确定性样例 + 引擎 CLI 行为 + 报告格式断言。全 PASS 则引擎可信。
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "check.py")
EX = os.path.join(ROOT, "examples")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def run(args):
    return subprocess.run([sys.executable, ENGINE] + args, capture_output=True, text=True, encoding="utf-8")


def load_report(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---- case 1: clean 样例（高成熟度，无红线） ----
r = run(["scan", os.path.join(EX, "fire-demo-clean.md"), os.path.join(EX, "_smoke_clean.md")])
rep = load_report(os.path.join(EX, "_smoke_clean.md"))
check("clean 退出码=0（无红线）", r.returncode == 0, "rc=%s" % r.returncode)
check("clean 指数>=95", "成熟度指数：**95" in rep or "成熟度指数：**96" in rep or "成熟度指数：**97" in rep
      or "成熟度指数：**98" in rep or "成熟度指数：**99" in rep or "成熟度指数：**100" in rep,
      [ln for ln in rep.splitlines() if "成熟度指数" in ln][:1])
check("clean 等级 L4/L5", ("L4" in rep or "L5" in rep), "")
check("clean 红线 0 条", "红线预警（0 条）" in rep, "")
check("clean 六维均>0", all(s in rep for s in ["感知接入", "传输联网", "平台功能", "值守运营", "数据与安全", "机制闭环"]), "")
check("clean 行动清单为空", "当前无待办行动项" in rep, "")

# ---- case 2: mid 样例（L3 规范级，有缺口无红线） ----
r = run(["scan", os.path.join(EX, "fire-demo-mid.md"), os.path.join(EX, "_smoke_mid.md")])
rep = load_report(os.path.join(EX, "_smoke_mid.md"))
check("mid 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
idx_line = [ln for ln in rep.splitlines() if "成熟度指数" in ln]
check("mid 指数在 40-55 区间", bool(idx_line) and any(("%d / 100" % i) in idx_line[0] for i in range(40, 56)),
      idx_line[:1])
check("mid 等级 L3", "L3 规范级" in rep, "")
check("mid 红线 0 条", "红线预警（0 条）" in rep, "")
check("mid 有主动缺口", "主动缺口清单" in rep and "电气火灾监控" in rep, "")

# ---- case 3: high 样例（L1 + 4 条红线） ----
r = run(["scan", os.path.join(EX, "fire-demo-high.md"), os.path.join(EX, "_smoke_high.md")])
rep = load_report(os.path.join(EX, "_smoke_high.md"))
check("high 退出码=1（有红线）", r.returncode == 1, "rc=%s" % r.returncode)
check("high 红线 5 条", "红线预警（5 条）" in rep, "")
for rl in ["平台无人值守", "数据不留痕不备份", "平台无认证或账号混用", "值守人员无证上岗", "监测平台停用瘫痪"]:
    check("high 红线命中: %s" % rl, rl in rep, "")
check("high 指数<=6", any(("%d / 100" % i) in rep for i in range(0, 7)), "")
check("high 等级 L1", "L1 初始级" in rep, "")
check("high 行动清单红线置顶", rep.find("优先行动清单") < rep.find("[红线]") or "[红线]" in rep, "")

# ---- case 4: 输出格式 ----
check("报告无 CRLF", "\r" not in rep, "")
check("报告含免责声明", "免责声明" in rep and "不构成官方检查结论" in rep, "")

# ---- case 5: version ----
r = run(["version"])
check("version 输出 1.0.1", r.stdout.strip() == "check-fire-smart-maturity 1.0.1", r.stdout.strip())

# ---- case 6: rules 基数 ----
r = run(["rules"])
check("rules: 6 维 30 要素 5 红线", "维度: 6" in r.stdout and "要素: 30" in r.stdout and "红线: 5" in r.stdout,
      r.stdout.splitlines()[0] if r.stdout else "")

# ---- case 7: 异常输入 ----
r = run(["scan", os.path.join(EX, "not-exist.md")])
check("缺文件退出码=2", r.returncode == 2, "rc=%s" % r.returncode)

# ---- 清理临时报告 ----
for t in ("clean", "mid", "high"):
    p = os.path.join(EX, "_smoke_%s.md" % t)
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
