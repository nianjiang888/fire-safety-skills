#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-fire-inspection 自包含冒烟测试。

断言维度：
- 三案例引擎实跑（覆盖良好 / 多红线 / 极简）行为自洽；
- 红线判定：主机屏蔽、消火栓无水、记录补签均置顶红线；
- 覆盖缺口：材料未提及的巡检项主动暴露；
- 场所频次判定：重点单位每日 / 人密营业期 2 小时 / 一般单位兜底；
- 主动自查清单封顶 6 条；
- version / rules 完整性 / 退出码 / 无价格词。

运行：python scripts/smoke_test.py
"""
import os
import subprocess
import sys
import json
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "check.py")
TMP = os.path.join(HERE, "_smoke_out.md")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def run_scan(in_name):
    r = subprocess.run([sys.executable, ENGINE, "scan",
                        os.path.join(PKG, "examples", in_name), TMP],
                       capture_output=True, text=True)
    rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
    return r, rep


# ---------- 案例一：写字楼覆盖良好 ----------
r, rep = run_scan("insp-input-office.md")
check("office 红线=0（退出码按缺口语义=1）", r.returncode == 1 and "红线=0" in r.stdout, "rc=%s %s" % (r.returncode, r.stdout.strip()[:60]))
check("office 覆盖度≥70", "覆盖度" in rep and int(re.search(r"覆盖度：(\d+)", rep).group(1)) >= 70, r.stdout.strip()[:80])
check("office 无红线信号章节为空态", "未发现红线级信号" in rep)
check("office 已覆盖项含灭火器月点检", "灭火器" in rep)
check("office 出处含 GB 25201", "GB 25201-2010" in rep)
check("office 画像识别重点单位", "消防安全重点单位" in rep)
check("office 仍有缺口主动暴露（喷淋/应急照明等）", "巡检覆盖缺口" in rep)

# ---------- 案例二：商场多红线 ----------
r, rep = run_scan("insp-input-mall.md")
check("mall 退出码=1", r.returncode == 1, "rc=%s" % r.returncode)
check("mall 覆盖度被封顶≤40", int(re.search(r"覆盖度：(\d+)", rep).group(1)) <= 40)
check("mall 红线：主机屏蔽", "主机屏蔽/带故障运行" in rep and "擅自停用消防设施" in rep)
check("mall 红线：消火栓无水", "消火栓无水" in rep)
check("mall 红线：记录补签", "补签" in rep or "记录失真" in rep)
check("mall 红线均带罚则", "五千元以上五万元以下罚款" in rep)
check("mall 高危：灭火器失压", "灭火器失压" in rep)
check("mall 高危：年度检测超期", "年度全面检测超期" in rep)
check("mall 画像=公众聚集场所（营业期2小时频次）", "公众聚集/人员密集场所" in rep and "2 小时" in rep)
check("mall 主动自查清单=商场专属", "【商场/市场】" in rep)
check("mall 自查清单封顶6条", rep.count("- [ ] 【") <= 6)

# ---------- 案例三：极简输入 ----------
r, rep = run_scan("insp-input-minimal.md")
check("minimal 退出码=1（有缺口）", r.returncode == 1)
check("minimal 不崩溃且覆盖度很低", int(re.search(r"覆盖度：(\d+)", rep).group(1)) < 30)
check("minimal 缺口主动摆出", "巡检覆盖缺口" in rep)
check("minimal 兜底频次（一般单位每季）", "每季度" in rep)
check("minimal 画像按养老院给医疗场所自查", "医院/养老/学校" in rep)

if os.path.isfile(TMP):
    os.remove(TMP)

# ---------- rules 完整性 ----------
with open(os.path.join(PKG, "resources", "rules.json"), encoding="utf-8") as f:
    rules = json.load(f)
ids = [r["id"] for r in rules["rules"]]
check("rules 无重复ID", len(ids) == len(set(ids)))
check("rules gap+violation ≥ 20", len(ids) >= 20, str(len(ids)))
check("rules 每条挂出处", all(r.get("citation") for r in rules["rules"]))
check("rules 场所频次库≥4", len(rules["profiles"]["venue_rules"]) >= 4)

# ---------- version / 参数 ----------
r = subprocess.run([sys.executable, ENGINE, "version"], capture_output=True, text=True)
check("version 退出码=0", r.returncode == 0)
check("version 引擎版本", "check-fire-inspection 1.0.1" in r.stdout, r.stdout.strip())
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
