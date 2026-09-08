# -*- coding: utf-8 -*-
"""
gen-fire-remote-duty 冒烟测试（主动 Agent 版）
自包含：相对路径定位引擎与样例，使用 sys.executable 运行。
运行：python scripts/smoke_test.py
"""
import os
import re
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "gen.py")
EX_DIR = os.path.join(SKILL_DIR, "examples")


def run_gen(fname, out_name):
    inp = os.path.join(EX_DIR, fname)
    out = os.path.join(EX_DIR, out_name)
    r = subprocess.run([sys.executable, ENGINE, "gen", inp, out],
                       capture_output=True, text=True)
    txt = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    return r, txt


def main():
    results = []

    # 案例1：广西写字楼 · 双人值守 · 信息齐全
    r1, t1 = run_gen("duty-input-office.md", "smoke-out-office.md")
    checks1 = [
        ("退出码0", r1.returncode == 0, f"rc={r1.returncode}"),
        ("广西政策命中", "广西壮族自治区" in t1, "未命中"),
        ("命中标记", "所在地命中" in t1, "无标记"),
        ("三班倒算式", "3 × 2 = 6" in t1, "算式缺失"),
        ("四班三运转算式", "4 × 2 = 8" in t1, "算式缺失"),
        ("持证核对通过", "不低于最低方案需求" in t1, "核对缺失"),
        ("误报治理章节", "误报治理" in t1, "缺失"),
        ("降级预案章节", "降级预案" in t1, "缺失"),
        ("政策对照表", "单人值守政策对照表" in t1 and "山东省" in t1, "缺失"),
        ("免责声明", "免责声明" in t1, "缺失"),
        ("双人判定", "双人值守（法定基线）" in t1, "判定异常"),
    ]
    results.append(("office(广西·双人·全)", checks1))

    # 案例2：山东商场 · 单人值守 · 无远程监控证据
    r2, t2 = run_gen("duty-input-mall.md", "smoke-out-mall.md")
    checks2 = [
        ("退出码0", r2.returncode == 0, f"rc={r2.returncode}"),
        ("山东政策命中", "山东省" in t2, "未命中"),
        ("有条件可行", "有条件可行" in t2, "判定异常"),
        ("条件未证提示", "未提供证据" in t2, "缺口未暴露"),
        ("单人四班算式", "4 × 1 = 4" in t2, "算式缺失"),
        ("判定不满足", "条满足" in t2 and "维持双人值守" in t2, "缺判定结论"),
        ("主动暴露C2", "C2" in t2 and "远程操作消防控制室所有控制功能" in t2, "条件表异常"),
    ]
    results.append(("mall(山东·单人·缺证据)", checks2))

    # 案例3：江西养老院 · 极简输入
    r3, t3 = run_gen("duty-input-minimal.md", "smoke-out-minimal.md")
    checks3 = [
        ("退出码0", r3.returncode == 0, f"rc={r3.returncode}"),
        ("未命中政策库", "未命中已知政策库" in t3, "应留白而非编造"),
        ("默认双人+假设标注", "双人值守（法定基线）" in t3 and "已按法定基线默认双人值守" in t3, "假设未标注"),
        ("待补充项", "待补充" in t3, "留白缺失"),
        ("养老画像", "医疗养老" in t3, "画像异常"),
        ("不编造江西政策", "江西省消防条例" not in t3, "疑似编造政策"),
    ]
    results.append(("minimal(江西·极简)", checks3))

    # version
    rv = subprocess.run([sys.executable, ENGINE, "version"], capture_output=True, text=True)
    ok_ver = rv.returncode == 0 and "gen-fire-remote-duty" in rv.stdout and "1.0.1" in rv.stdout
    results.append(("version", [("输出正确", ok_ver, rv.stdout.strip())]))

    # recipe 完整性
    recipe = json.load(open(os.path.join(SKILL_DIR, "resources", "recipe.json"), encoding="utf-8"))
    n_policy = len(recipe["policy_db"])
    n_cond = len(recipe["single_duty_conditions"])
    n_prof = len(recipe["profiles"])
    bad_policy = [e["region"] for e in recipe["policy_db"] if not e.get("rule") or not e.get("basis")]
    checks4 = [
        ("政策库>=20", n_policy >= 20, f"n={n_policy}"),
        ("条件>=5", n_cond >= 5, f"n={n_cond}"),
        ("画像>=5", n_prof >= 5, f"n={n_prof}"),
        ("政策条目完整", not bad_policy, str(bad_policy)),
        ("免责非空", bool(recipe.get("disclaimer")), "空"),
    ]
    results.append((f"recipe(政策{n_policy}/条件{n_cond}/画像{n_prof})", checks4))

    print("=" * 60)
    print("gen-fire-remote-duty 冒烟结果")
    print("=" * 60)
    allok = True
    for name, checks in results:
        for label, ok, info in checks:
            print(("PASS" if ok else "FAIL") + f"  {name} · {label}: {info}")
            if not ok:
                allok = False
    print("=" * 60)
    print("ALL PASS" if allok else "SOME FAILED")
    rc = 0 if allok else 1
    # 清理冒烟输出
    for f in ["smoke-out-office.md", "smoke-out-mall.md", "smoke-out-minimal.md"]:
        try:
            os.remove(os.path.join(EX_DIR, f))
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
