#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-fire-class-method 自包含冒烟测试（相对路径 + sys.executable）。"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "gen.py")

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (("  -> " + detail) if detail and not ok else ""))


def run(args):
    return subprocess.run([sys.executable, ENGINE] + args, capture_output=True, text=True)


# case 1: version
r = run(["version"])
check("version 输出 gen-fire-class-method 1.0.1", r.returncode == 0 and "gen-fire-class-method 1.0.1" in r.stdout, r.stdout.strip())

# case 2: validate
r = run(["validate"])
check("validate 校验通过", r.returncode == 0 and "校验通过" in r.stdout, r.stdout.strip())

# case 3: 泛科普请求 -> 模式=泛科普, 无火类
inp = os.path.join(SKILL, "examples", "class-input-general.md")
out = os.path.join(SKILL, "examples", "sample-class-general.md")
r = run(["gen", inp, out])
check("general 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("general 模式=泛科普", "模式: 泛科普" in r.stdout, r.stdout.strip())
check("general 识别火类=无", "识别火类: 无（泛科普）" in r.stdout, r.stdout.strip())
with open(out, encoding="utf-8") as f:
    g = f.read()
check("general 含六类表(A类)", "A类" in g and "F类" in g)
check("general 含四原理", "冷却灭火法" in g and "化学抑制灭火法" in g)
check("general 含免责声明", "免责声明" in g or "免责" in g)
check("general 不出现场景处置段", "针对该场景的处置要点" not in g)

# case 4: 厨房油锅 -> F类, 禁水提示
inp = os.path.join(SKILL, "examples", "class-input-kitchen.md")
out = os.path.join(SKILL, "examples", "sample-class-kitchen.md")
r = run(["gen", inp, out])
check("kitchen 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("kitchen 识别火类=F", "识别火类: F" in r.stdout, r.stdout.strip())
check("kitchen 模式=场景处置", "模式: 场景处置" in r.stdout, r.stdout.strip())
with open(out, encoding="utf-8") as f:
    k = f.read()
check("kitchen 含场景处置段", "针对该场景的处置要点" in k)
check("kitchen 明确禁水", "严禁泼水" in k or "严禁用水" in k)
check("kitchen 含盖锅盖建议", "锅盖" in k or "灭火毯" in k)
check("kitchen 含特别提醒", "特别提醒" in k)

# case 5: 配电柜带电 -> E类, 先断电
inp = os.path.join(SKILL, "examples", "class-input-electrical.md")
out = os.path.join(SKILL, "examples", "sample-class-electrical.md")
r = run(["gen", inp, out])
check("elec 退出码=0", r.returncode == 0, "rc=%s" % r.returncode)
check("elec 识别火类=E", "识别火类: E" in r.stdout, r.stdout.strip())
with open(out, encoding="utf-8") as f:
    e = f.read()
check("elec 含先断电", "先断电" in e or "切断电源" in e)
check("elec 禁用导电介质", "不导电" in e or "导电" in e)
check("elec 含特别提醒", "特别提醒" in e)

# case 6: 鲁棒性——空输入不应崩溃
import tempfile, io
tmp = os.path.join(SKILL, "examples", "_empty.md")
open(tmp, "w", encoding="utf-8").close()
r = run(["gen", tmp, os.path.join(SKILL, "examples", "_empty_out.md")])
check("空输入不崩溃(rc=0)", r.returncode == 0, "rc=%s" % r.returncode)
try:
    os.remove(tmp)
    os.remove(os.path.join(SKILL, "examples", "_empty_out.md"))
except OSError:
    pass

n_fail = sum(1 for _, ok, _ in results if not ok)
print("\n冒烟结果：%d 通过 / %d 失败" % (len(results) - n_fail, n_fail))
sys.exit(1 if n_fail else 0)
