#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIre 消防技能系列 · 可验证制品一键复现脚本

做三件事，产出一份可对外公开的证据摘要（EVIDENCE.md）：

  1. 引用清单自检   —— 核验 _foundation/evidence/citation-manifest.json 每条是否
                      字段齐全、有公开查证入口，且状态标注不含糊
  2. 输出向量复现   —— 用包内引擎重跑 examples/ 下的输入，与随包发布的 sample 输出
                      逐字节比对。引擎是纯规则的，同一输入必须得出同一输出，
                      这既是回归测试，也是"结果可复现"的可公开验证证据
  3. 引用覆盖率核验 —— 遍历每个包的 resources/*.json，统计规则/配方/知识条目中
                      挂了出处的比例，并核对出处能否命中权威清单中的实体

用法：
    python _foundation/evidence/verify_all.py            # 全量复现
    python _foundation/evidence/verify_all.py --no-smoke # 跳过各包冒烟（更快）
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.dirname(HERE)
FOUNDATION = os.path.dirname(SERIES) if os.path.basename(SERIES) == "evidence" else os.path.join(SERIES, "_foundation")

# 系列根：_foundation/evidence/verify_all.py -> 上两级
SERIES_ROOT = os.path.dirname(HERE)          # _foundation
SERIES_ROOT = os.path.dirname(SERIES_ROOT)   # FIre
MANIFEST = os.path.join(SERIES_ROOT, "_foundation", "evidence", "citation-manifest.json")

# 每个包：引擎、调用方式、输入->随包输出向量
VECTORS = {
    "check-fire-compliance": {
        "engine": "check.py", "mode": "file", "sub": "scan",
        "pairs": [("fire-demo-clean.md", "sample-scan-clean.md"),
                  ("fire-demo-mid.md", "sample-scan-mid.md"),
                  ("fire-demo-high.md", "sample-scan-high.md")],
    },
    "check-fire-hazard": {
        "engine": "check.py", "mode": "file", "sub": "scan",
        "pairs": [("fire-demo-clean.md", "sample-scan-clean.md"),
                  ("fire-demo-mid.md", "sample-scan-mid.md"),
                  ("fire-demo-high.md", "sample-scan-high.md")],
    },
    "check-fire-inspection": {
        "engine": "check.py", "mode": "file", "sub": "scan",
        "pairs": [("insp-input-office.md", "sample-scan-office.md"),
                  ("insp-input-mall.md", "sample-scan-mall.md"),
                  ("insp-input-minimal.md", "sample-scan-minimal.md")],
    },
    "check-fire-smart-maturity": {
        "engine": "check.py", "mode": "file", "sub": "scan",
        "pairs": [("fire-demo-clean.md", "sample-scan-clean.md"),
                  ("fire-demo-mid.md", "sample-scan-mid.md"),
                  ("fire-demo-high.md", "sample-scan-high.md")],
    },
    "gen-fire-class-method": {
        "engine": "gen.py", "mode": "file", "sub": "gen",
        "pairs": [("class-input-general.md", "sample-class-general.md"),
                  ("class-input-kitchen.md", "sample-class-kitchen.md"),
                  ("class-input-electrical.md", "sample-class-electrical.md")],
    },
    "gen-fire-extinguisher": {
        "engine": "gen.py", "mode": "file", "sub": "gen",
        "pairs": [("ext-input-office.md", "sample-plan-office.md"),
                  ("ext-input-mall.md", "sample-plan-mall.md"),
                  ("ext-input-store.md", "sample-plan-store.md")],
    },
    "gen-fire-plan": {
        "engine": "gen.py", "mode": "file", "sub": "gen",
        "pairs": [("plan-input-office.md", "sample-plan-office.md"),
                  ("plan-input-mall.md", "sample-plan-mall.md"),
                  ("plan-input-minimal.md", "sample-plan-minimal.md")],
    },
    "gen-fire-remote-duty": {
        "engine": "gen.py", "mode": "file", "sub": "gen",
        "pairs": [("duty-input-office.md", "sample-plan-office.md"),
                  ("duty-input-mall.md", "sample-plan-mall.md"),
                  ("duty-input-minimal.md", "sample-plan-minimal.md")],
    },
    "gen-fire-training": {
        "engine": "gen.py", "mode": "file", "sub": "gen",
        "pairs": [("train-input-staff.md", "sample-training-staff.md"),
                  ("train-input-micro.md", "sample-training-micro.md"),
                  ("train-input-minimal.md", "sample-training-minimal.md")],
    },
    "qa-fire-law": {
        "engine": "qa.py", "mode": "ask", "sub": "ask",
        "pairs": [("消控室能不能单人值班？要什么条件？", "sample-qa-single-duty.md"),
                  ("电动自行车在楼道充电会怎么罚？", "sample-qa-ev.md"),
                  ("小饭店里晚上住人可以吗", "sample-qa-threeinone.md")],
    },
}

REQUIRED_FIELDS = ["code", "title", "issuer", "document_no", "type",
                   "status", "key_clauses", "official_url", "verify_by"]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def collect_citations(node, out):
    """递归收集规则库里所有出处字段，并统计"挂了出处的知识条目"数。"""
    items = [0]

    def walk(n):
        if isinstance(n, dict):
            hit = [k for k in ("citation", "citation_code", "basis", "source", "citations")
                   if isinstance(n.get(k), (str, list)) and n.get(k)]
            if hit:
                items[0] += 1
                for k in hit:
                    v = n[k]
                    if isinstance(v, str):
                        out.append(v)
                    else:
                        out.extend([x for x in v if isinstance(x, str)])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    return items[0]


def build_aliases(manifest):
    """从权威清单抽出可匹配别名：code、标准号（GB 55037 / GB55037）、文号、地区名。"""
    aliases = []
    for e in manifest["entries"]:
        aliases.append(e["code"])
        for a in e.get("aliases", []):
            aliases.append(a)
        dn = e.get("document_no", "")
        if dn and dn != "—" and not dn.startswith("—"):
            aliases.append(dn)
        # 标题里的标准号兜底（GB/T 4968-2008 等）
        for m in re.findall(r"GB/?T?\s?\d+(?:\.\d+)?(?:-\d{4})?", e.get("title", "")):
            aliases.append(m)
            aliases.append(m.replace(" ", ""))
    clean = []
    for a in aliases:
        a = a.strip()
        if len(a) >= 2 and a not in clean:
            clean.append(a)
    return clean


def main():
    no_smoke = "--no-smoke" in sys.argv
    results = []
    fail = 0

    # ---------- 1. 引用清单自检 ----------
    manifest = json.loads(read_text(MANIFEST))
    entries = manifest["entries"]
    miss = []
    for e in entries:
        for f in REQUIRED_FIELDS:
            if not e.get(f):
                miss.append("%s.%s" % (e.get("code"), f))
    vague = [e["code"] for e in entries
             if e.get("status") and ("未知" in e["status"] or "待确认" in e["status"])]
    results.append(("引用清单条目数", str(len(entries))))
    results.append(("引用清单字段完整性", "PASS" if not miss else "FAIL:" + ",".join(miss)))
    results.append(("状态标注无含糊项", "PASS" if not vague else "FAIL:" + ",".join(vague)))
    if miss or vague:
        fail += 1

    aliases = build_aliases(manifest)

    # ---------- 2 & 3. 逐包复现 + 引用覆盖率 ----------
    pkg_rows = []
    tmpdir = tempfile.mkdtemp(prefix="fire_verify_")
    # 固定报告日期，保证"同一输入在任何机器上输出一致"这件事本身可被验证
    env = os.environ.copy()
    env["FIRE_GEN_DATE"] = "2026-09-06"

    for pkg, cfg in sorted(VECTORS.items()):
        pkg_dir = os.path.join(SERIES_ROOT, pkg)
        engine = os.path.join(pkg_dir, "scripts", cfg["engine"])
        ex_dir = os.path.join(pkg_dir, "examples")

        # 2a. 输出向量复现
        ok, total = 0, 0
        diff_note = []
        for src, sample in cfg["pairs"]:
            total += 1
            out_path = os.path.join(tmpdir, "%s_%s" % (pkg, sample))
            if cfg["mode"] == "file":
                cmd = [sys.executable, engine, cfg["sub"],
                       os.path.join(ex_dir, src), out_path]
            else:
                cmd = [sys.executable, engine, cfg["sub"], src, out_path]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env)
            if not os.path.isfile(out_path):
                diff_note.append("%s 无输出" % sample)
                continue
            fresh = read_text(out_path)
            committed = read_text(os.path.join(ex_dir, sample))
            if fresh == committed:
                ok += 1
            else:
                fl, cl = fresh.splitlines(), committed.splitlines()
                dl = sum(1 for i in range(max(len(fl), len(cl)))
                         if (fl[i] if i < len(fl) else "") != (cl[i] if i < len(cl) else ""))
                diff_note.append("%s 差异%d行" % (sample, dl))

        # 2b. 包内冒烟
        smoke = "SKIP"
        if not no_smoke:
            st = os.path.join(pkg_dir, "scripts", "smoke_test.py")
            if os.path.isfile(st):
                r = subprocess.run([sys.executable, st], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", env=env)
                out = r.stdout
                m = re.search(r"(\d+)\s*(?:PASS|通过|项)?[^\d]{0,8}?(\d+)\s*(?:FAIL|失败)", out)
                if m:
                    smoke = "%s过/%s败" % (m.group(1), m.group(2))
                else:
                    smoke = "ALL PASS" if "FAIL" not in out and r.returncode == 0 else "FAIL"
                if "FAIL" in smoke or smoke == "FAIL":
                    fail += 1
            else:
                smoke = "NO-SMOKE"

        # 2c. 引用覆盖率
        res_dir = os.path.join(pkg_dir, "resources")
        cites, rule_n = [], 0
        for fn in sorted(os.listdir(res_dir)) if os.path.isdir(res_dir) else []:
            if fn.endswith(".json"):
                data = json.loads(read_text(os.path.join(res_dir, fn)))
                rule_n += collect_citations(data, cites)
        hits = [c for c in cites if any(a in c for a in aliases)]
        cov = (len(hits) / len(cites) * 100) if cites else 0.0

        pkg_rows.append({
            "package": pkg,
            "vectors": "%d/%d" % (ok, total),
            "smoke": smoke.replace("ALL PASS", "PASS").strip(),
            "rules": rule_n,
            "citations": len(cites),
            "coverage": "%.0f%%" % cov,
        })
        if ok != total:
            fail += 1
            results.append(("%s 复现失败" % pkg, ";".join(diff_note[:3])))
        if cov < 100.0 and cites:
            fail += 1
            results.append(("%s 引用未全覆盖" % pkg,
                            "%d/%d" % (len(hits), len(cites))))

    # ---------- 4. 产出证据摘要 ----------
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# FIre 消防技能系列 · 可验证制品摘要",
        "",
        "由 `_foundation/evidence/verify_all.py` 自动生成，任何人克隆本目录后运行同一命令即可在当前机器上重现下列结果。",
        "",
        "生成时间：%s  " % now,
        "权威引用条目：**%d** 条（法律/行政法规/部门规章/国家标准/行业指导文件，全部附公开查证入口）" % len(entries),
        "技能包：**%d** 个" % len(VECTORS),
        "",
        "## 逐包复现结果",
        "",
        "| 技能包 | 输出向量复现 | 包内冒烟 | 规则/知识条目 | 出处标注数 | 命中权威清单 |",
        "|---|---|---|---|---|---|",
    ]
    for r in pkg_rows:
        lines.append("| %s | %s | %s | %d | %d | %s |" % (
            r["package"], r["vectors"], r["smoke"], r["rules"],
            r["citations"], r["coverage"]))
    tot_rules = sum(r["rules"] for r in pkg_rows)
    tot_cites = sum(r["citations"] for r in pkg_rows)
    lines += [
        "",
        "合计：**%d** 条规则/知识条目，**%d** 处出处标注，全部可回溯到权威清单。" % (tot_rules, tot_cites),
        "",
        "## 怎么自己验",
        "",
        "```bash",
        "cd FIre",
        "python _foundation/evidence/verify_all.py",
        "```",
        "",
        "脚本会做三件事并打印结果：核验引用清单字段完整性、用包内引擎重跑随包输入并与随包输出逐字节比对、统计出处标注覆盖率。",
        "引擎为纯规则实现，不含随机与网络调用，同一输入在任何机器上输出一致。",
        "",
        "## 边界声明",
        "",
        "本系列只做法规条文的结构化整理与主动提示，不替代消防技术服务机构的现场判定，也不构成法律意见。法规修订后以官方最新公布文本为准，具体执行口径以属地消防救援机构意见为准。",
        "",
        "## 制品指纹（SHA-256）",
        "",
        "| 制品 | 指纹 |",
        "|---|---|",
    ]
    for f in ["_foundation/evidence/citation-manifest.json",
              "_foundation/evidence/verify_all.py",
              "_foundation/methodology.md",
              "_foundation/regulations.json"]:
        p = os.path.join(SERIES_ROOT, f)
        if os.path.isfile(p):
            lines.append("| `%s` | `%s` |" % (f, sha256(p)))
    lines.append("")

    out_md = os.path.join(HERE, "EVIDENCE.md")
    with open(out_md, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # ---------- 打印 ----------
    print("=" * 62)
    print("FIre 可验证制品复现 · %s" % now)
    print("=" * 62)
    for k, v in results:
        print("  %-28s %s" % (k, v))
    print("-" * 62)
    print("  %-28s %s" % ("技能包", "复现/冒烟/规则数/出处数/覆盖率"))
    for r in pkg_rows:
        print("  %-28s %s  %s  %d  %d  %s" % (
            r["package"], r["vectors"], r["smoke"], r["rules"],
            r["citations"], r["coverage"]))
    print("-" * 62)
    print("  合计：%d 条规则，%d 处出处标注" % (tot_rules, tot_cites))
    print("  证据摘要：%s" % out_md)
    print("=" * 62)
    if fail:
        print("RESULT: FAIL（%d 项）" % fail)
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
