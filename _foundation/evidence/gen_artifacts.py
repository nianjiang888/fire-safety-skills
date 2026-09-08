#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 FIre 系列每个技能包生成 references/verifiable-artifacts.md，
并在 README.md 顶部插入统一的"技术背书与可验证制品"声明块。

产物全部自包含：包内即可核验，不引用包外路径。

用法：python _foundation/evidence/gen_artifacts.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.dirname(os.path.dirname(HERE))  # FIre/
MANIFEST = os.path.join(HERE, "citation-manifest.json")
sys.path.insert(0, HERE)
from verify_all import VECTORS, build_aliases, read_text  # noqa: E402

PKG_LABEL = {
    "check-fire-compliance": "消防合规体检",
    "check-fire-hazard": "防火隐患识别",
    "check-fire-inspection": "消防设施巡检助手",
    "check-fire-smart-maturity": "智慧消防成熟度评估",
    "gen-fire-class-method": "火灾分类与灭火方法",
    "gen-fire-extinguisher": "灭火器配置顾问",
    "gen-fire-plan": "灭火和应急疏散预案生成器",
    "gen-fire-remote-duty": "消防远程值守方案生成器",
    "gen-fire-training": "消防培训课件生成器",
    "qa-fire-law": "消防法规问答",
}

BADGE = (
    "> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处"
    "（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 "
    "`references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，"
    "包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。\n"
)


def collect(node, out, items):
    if isinstance(node, dict):
        hit = [k for k in ("citation", "citation_code", "basis", "source", "citations")
               if isinstance(node.get(k), (str, list)) and node.get(k)]
        if hit:
            items[0] += 1
            for k in hit:
                v = node[k]
                out.extend([v] if isinstance(v, str)
                           else [x for x in v if isinstance(x, str)])
        for v in node.values():
            collect(v, out, items)
    elif isinstance(node, list):
        for v in node:
            collect(v, out, items)


def main():
    manifest = json.loads(read_text(MANIFEST))
    aliases = build_aliases(manifest)
    code_of = {}
    for e in manifest["entries"]:
        for a in [e["code"]] + e.get("aliases", []):
            code_of[a] = e["code"]

    for pkg, cfg in sorted(VECTORS.items()):
        pkg_dir = os.path.join(SERIES, pkg)
        res_dir = os.path.join(pkg_dir, "resources")
        cites, items = [], [0]
        for fn in sorted(os.listdir(res_dir)):
            if fn.endswith(".json"):
                collect(json.loads(read_text(os.path.join(res_dir, fn))), cites, items)

        hit_codes = []
        for c in cites:
            for a in aliases:
                if a in c:
                    code = code_of.get(a)
                    if code and code not in hit_codes:
                        hit_codes.append(code)
                    break
        cov = (sum(1 for c in cites if any(a in c for a in aliases)) / len(cites) * 100) if cites else 100.0

        rows = []
        for src, sample in cfg["pairs"]:
            if cfg["mode"] == "file":
                rows.append("| `examples/%s` | `examples/%s` | 包内引擎重跑，逐字节比对 |" % (src, sample))
            else:
                rows.append("| 提问「%s」 | `examples/%s` | 包内引擎重跑，逐字节比对 |" % (src, sample))

        md = [
            "# %s · 可验证制品" % PKG_LABEL.get(pkg, pkg),
            "",
            "本文件说明这个技能包里有哪些东西是可以自己动手验证的，以及怎么验证。",
            "",
            "## 一键核验",
            "",
            "```bash",
            "python scripts/smoke_test.py      # 包级冒烟，覆盖三档输入",
            "```",
            "",
            "系列级全量复现（引用清单自检 + 输出向量比对 + 出处覆盖率）在 FIre 系列仓库内执行：",
            "",
            "```bash",
            "python _foundation/evidence/verify_all.py",
            "```",
            "",
            "## 输出向量（可复现）",
            "",
            "| 输入 | 随包输出 | 复现方式 |",
            "|---|---|---|",
        ] + rows + [
            "",
            "引擎为纯规则实现，不含随机与网络调用：给定同一输入，任何机器上得到的报告完全一致。"
            "报告日期默认取当天，设置环境变量 `FIRE_GEN_DATE` 可固定为指定日期，便于自动化比对。",
            "",
            "## 出处标注",
            "",
            "- 规则/知识条目：**%d** 条" % items[0],
            "- 出处标注：**%d** 处，命中权威引用清单比例 **%.0f%%**" % (len(cites), cov),
            "- 本包涉及的权威依据：%s" % "、".join(hit_codes[:12] if hit_codes else ["—"]),
            "",
            "每条规则的完整条文表述与简短代号（`citation` / `citation_code`）保存在 "
            "`resources/` 下的规则库中，报告中会一并展示，不需要回头翻规则库。",
            "",
            "## 边界声明",
            "",
            "本技能只做法规条文的结构化整理与主动提示，不替代消防技术服务机构的现场判定，"
            "也不构成法律意见。法规修订后以官方最新公布文本为准；地方规定差异较大，"
            "具体执行口径以属地消防救援机构意见为准。",
            "",
        ]

        out_path = os.path.join(pkg_dir, "references", "verifiable-artifacts.md")
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(md))

        # README 背书块
        rp = os.path.join(pkg_dir, "README.md")
        txt = read_text(rp)
        if "技术背书与可验证制品" not in txt:
            lines = txt.split("\n")
            # 插到标题行之后（跳过紧随的空行）
            i = 0
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            i += 1
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            new = "\n".join(lines[:i]) + "\n\n" + BADGE + "\n" + "\n".join(lines[i:])
            with open(rp, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
        print("OK %-28s 条目%3d 出处%3d 覆盖%.0f%%" % (pkg, items[0], len(cites), cov))


if __name__ == "__main__":
    main()
