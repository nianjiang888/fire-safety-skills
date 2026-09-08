# -*- coding: utf-8 -*-
"""
check-fire-compliance 冒烟测试（主动 Agent 版）
自包含：相对路径定位引擎与样例，使用 sys.executable 运行，不依赖外部目录。
运行：python scripts/smoke_test.py
"""
import os
import re
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
ENGINE = os.path.join(HERE, "check.py")
EX_DIR = os.path.join(SKILL_DIR, "examples")


def run_scan(fname, out_path):
    inp = os.path.join(EX_DIR, fname)
    r = subprocess.run(
        [sys.executable, ENGINE, "scan", inp, out_path],
        capture_output=True, text=True
    )
    return r


def parse_report(path):
    txt = open(path, encoding="utf-8").read()
    cov = None
    m = re.search(r"合规覆盖度：(\d+)", txt)
    if m:
        cov = int(m.group(1))
    redline_ids = set(re.findall(r"-\s+\*\*\[(R-[A-Z]+-\d+)\]", txt))
    # 画像
    prof = None
    mp = re.search(r"单位画像：\*\*(.+?)\*\*", txt)
    if mp:
        prof = mp.group(1)
    return cov, redline_ids, prof


def main():
    cases = [
        # (样例文件, 期望画像含, 期望覆盖度区间(min,max), 期望红线命中ID集合(子集), 期望退出码)
        ("fire-demo-clean.md", ["重点单位", "人员密集"], (80, 100), set(), 0),
        ("fire-demo-mid.md", ["一般单位"], (50, 79), set(), 0),
        ("fire-demo-high.md", None, (0, 49), {"R-FAC-01", "R-FAC-04", "R-EVA-01", "R-EXT-03"}, 4),
    ]
    results = []
    for fname, prof_must, (cmin, cmax), must_redlines, want_rc in cases:
        out = os.path.join(EX_DIR, "smoke-out-" + fname.replace(".md", ".md"))
        r = run_scan(fname, out)
        ok_rc = (r.returncode == want_rc)
        cov, reds, prof = parse_report(out)
        ok_cov = (cov is not None and cmin <= cov <= cmax)
        ok_prof = True
        if prof_must:
            ok_prof = all(p in (prof or "") for p in prof_must)
        ok_red = must_redlines.issubset(reds)
        ok = ok_rc and ok_cov and ok_prof and ok_red
        results.append((fname, ok, f"rc={r.returncode}(want {want_rc}) cov={cov}(want {cmin}-{cmax}) prof={prof} reds={sorted(reds)} must={sorted(must_redlines)}"))
        try:
            os.remove(out)
        except OSError:
            pass

    # version 子命令
    rv = subprocess.run([sys.executable, ENGINE, "version"], capture_output=True, text=True)
    ok_ver = (rv.returncode == 0 and "check-fire-compliance" in rv.stdout and "1.0.1" in rv.stdout)
    results.append(("version", ok_ver, rv.stdout.strip()))

    # 规则基数健全性
    rules_path = os.path.join(SKILL_DIR, "resources", "rules.json")
    rd = __import__("json").load(open(rules_path, encoding="utf-8"))
    n = len(rd["rules"])
    no_code = [x["id"] for x in rd["rules"] if not x.get("citation_code")]
    ok_rules = (n >= 20 and not no_code)
    results.append((f"rules({n})", ok_rules, "无出处规则: %s" % (no_code or "无")))

    print("=" * 60)
    print("check-fire-compliance 冒烟结果")
    print("=" * 60)
    allok = True
    for name, ok, info in results:
        print(("PASS" if ok else "FAIL") + f"  {name}: {info}")
        if not ok:
            allok = False
    print("=" * 60)
    print("ALL PASS" if allok else "SOME FAILED")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
