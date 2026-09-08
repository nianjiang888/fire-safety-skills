#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-fire-class-method —— 火灾分类与灭火方法生成器（FIre 系列主动 Agent 版，v1.0.1）

用法：
  python gen.py gen <input.md> [out.md]   生成火灾分类与灭火方法简报
  python gen.py version                    打印版本
  python gen.py validate                   校验 recipe.json 完整性

输入为一段自然语言：可以是泛泛的科普请求（如“讲讲火灾分类”），
也可以是具体场景（如“厨房油锅着火能用水泼吗”“配电柜着火怎么办”）。
引擎会主动识别火灾类别、给出对应处置要点与常见误区，不追问、不骚扰。
"""
import os
import sys
import json

ENGINE_VERSION = "1.0.1"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPE = os.path.join(BASE, "resources", "recipe.json")


def load_recipe():
    with open(RECIPE, encoding="utf-8") as f:
        return json.load(f)


def detect_classes(text, recipe):
    """返回命中火类代码列表（去重、保持 A-F 顺序）。"""
    order = ["A", "B", "C", "D", "E", "F"]
    hits = []
    for cls in recipe["fire_classes"]:
        for kw in cls.get("keywords", []):
            if kw in text:
                if cls["code"] not in hits:
                    hits.append(cls["code"])
                break
    hits.sort(key=lambda c: order.index(c))
    return hits


def is_general_request(text, recipe):
    t = text.lower()
    # 含通用触发词，且无具体场景关键词
    has_general = any(g in t for g in recipe["generator"]["general_triggers"])
    has_scenario = detect_classes(text, recipe)
    if has_general and not has_scenario:
        return True
    return False


def class_table(recipe, codes=None):
    rows = recipe["fire_classes"]
    if codes:
        rows = [c for c in rows if c["code"] in codes]
    lines = []
    lines.append("| 类别 | 含义 | 典型可燃物 | 适用灭火剂 | 禁用/慎用 |")
    lines.append("|---|---|---|---|---|")
    for c in rows:
        lines.append(
            "| **%s类** %s | %s | %s | %s | %s |"
            % (
                c["code"],
                c["name"],
                c["def"],
                "、".join(c["fuels"]),
                "、".join(c["use_agent"]),
                "；".join([x for x in c["forbid_agent"] if x != "—"]),
            )
        )
    return "\n".join(lines)


def principles_block(recipe):
    lines = ["灭火的本质是破坏燃烧三条件（可燃物、助燃物、引火源）之一。四种基本方法：", ""]
    for i, p in enumerate(recipe["principles"], 1):
        agents = "、".join(p["typical_agent"])
        lines.append(
            "%d. **%s**：%s（常用：%s。依据：%s）" % (i, p["name"], p["mechanism"], agents, p["citation"])
        )
    return "\n".join(lines)


def disposal_block(recipe, codes):
    lines = []
    for code in codes:
        c = next(x for x in recipe["fire_classes"] if x["code"] == code)
        lines.append("**%s类 %s**" % (code, c["name"]))
        lines.append("- 典型可燃物：%s" % "、".join(c["fuels"]))
        lines.append("- 优先灭火剂：%s" % "、".join(c["use_agent"]))
        forb = [x for x in c["forbid_agent"] if x != "—"]
        if forb:
            lines.append("- 禁用/慎用：%s" % "；".join(forb))
        lines.append("- 处置要点：%s" % c["disposal"])
        lines.append("- 依据：%s" % c["citation"])
        lines.append("")
    return "\n".join(lines).rstrip()


def mistakes_block(recipe, codes=None):
    items = recipe["mistakes"]
    if codes:
        # 优先展示与命中火类相关的误区，不足再补其他
        related = [m for m in items if m.get("class") in codes]
        others = [m for m in items if m.get("class") not in codes]
        items = related + others
    items = items[: recipe["generator"]["max_mistakes_shown"]]
    lines = []
    for m in items:
        lines.append(
            "- **%s**：忌“%s”；应“%s”。（%s类，依据 %s）"
            % (m["scenario"], m["wrong"], m["right"], m.get("class", "—"), m["citation"])
        )
    return "\n".join(lines)


def generate(text, recipe):
    codes = detect_classes(text, recipe)
    general = is_general_request(text, recipe)
    title = recipe["meta"]["title"]
    out = []
    out.append("# 火灾分类与灭火方法简报")
    out.append("")
    out.append("> 生成依据：%s" % "；".join(recipe["meta"]["standards_cited"]))
    out.append("")

    if codes:
        names = "、".join(
            "%s类%s" % (c, next(x for x in recipe["fire_classes"] if x["code"] == c)["name"])
            for c in codes
        )
        out.append("## 一、场景识别")
        out.append("")
        out.append("根据您描述的内容，主动识别为可能涉及：**%s**。" % names)
        if not general:
            out.append("下面先给针对该场景的处置要点，再附完整的分类与原理供您延伸了解。")
        out.append("")

    if codes and not general:
        out.append("## 二、针对该场景的处置要点")
        out.append("")
        out.append(disposal_block(recipe, codes))
        out.append("")

    out.append("## %s、火灾六类划分（GB/T 4968-2008）" % ("二" if general else "三"))
    out.append("")
    out.append(class_table(recipe))
    out.append("")
    out.append(
        "说明：标准将火灾按可燃物类型和燃烧特性分为 A、B、C、D、E、F 六类；"
        "ABC 干粉（磷酸铵盐）可扑救除金属（D 类）外的大部分火灾，是日常最通用的选型。"
    )
    out.append("")

    out.append("## %s、灭火的四种基本方法" % ("三" if general else "四"))
    out.append("")
    out.append(principles_block(recipe))
    out.append("")

    out.append("## %s、常见处置误区（主动提示）" % ("四" if general else "五"))
    out.append("")
    out.append(mistakes_block(recipe, codes if codes else None))
    out.append("")

    # 主动提示：若用户场景涉及最易误操作的两类，追加醒目提醒
    if codes and ("F" in codes or "E" in codes or "D" in codes):
        out.append("### 特别提醒")
        out.append("")
        tips = []
        if "F" in codes:
            tips.append("厨房油锅着火：**严禁泼水、严禁端锅跑**，关火盖锅盖或灭火毯最有效。")
        if "E" in codes:
            tips.append("带电设备着火：**先断电**再处置；无法断电务必用不导电灭火剂，禁用导电介质。")
        if "D" in codes:
            tips.append("金属火灾：**严禁用水和二氧化碳**，干砂/专用金属干粉覆盖。")
        for t in tips:
            out.append("- %s" % t)
        out.append("")

    out.append("## %s、免责声明" % ("五" if general else "六"))
    out.append("")
    out.append(recipe["generator"]["disclaimer"])
    out.append("")
    return "\n".join(out).strip() + "\n", codes, general


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("用法: python gen.py gen <input.md> [out.md] | version | validate\n")
        return 2
    cmd = argv[1]
    recipe = load_recipe()

    if cmd == "version":
        print("%s %s" % (recipe["meta"]["skill"], ENGINE_VERSION))
        return 0

    if cmd == "validate":
        problems = []
        codes = [c["code"] for c in recipe["fire_classes"]]
        if sorted(codes) != ["A", "B", "C", "D", "E", "F"]:
            problems.append("fire_classes 应为 A-F 六类，实际：%s" % codes)
        for c in recipe["fire_classes"]:
            for k in ("code", "name", "def", "use_agent", "forbid_agent", "disposal", "citation", "keywords"):
                if not c.get(k):
                    problems.append("类 %s 缺字段 %s" % (c["code"], k))
            if "—" not in c["forbid_agent"] and not any(c["forbid_agent"]):
                problems.append("类 %s forbid_agent 为空" % c["code"])
        if len(recipe["principles"]) != 4:
            problems.append("principles 应为 4 条，实际 %d" % len(recipe["principles"]))
        for m in recipe["mistakes"]:
            if not m.get("citation"):
                problems.append("误区 %s 缺 citation" % m.get("scenario", "?"))
        if problems:
            print("校验不通过：")
            for p in problems:
                print("  - %s" % p)
            return 1
        print(
            "校验通过：六类火灾 %d 条、原理 %d 条、误区 %d 条、引用完整"
            % (len(recipe["fire_classes"]), len(recipe["principles"]), len(recipe["mistakes"]))
        )
        return 0

    if cmd == "gen":
        if len(argv) < 3:
            sys.stderr.write("gen 需要输入文件\n")
            return 2
        in_path = argv[2]
        out_path = argv[3] if len(argv) > 3 else None
        with open(in_path, encoding="utf-8") as f:
            text = f.read().strip()
        content, codes, general = generate(text, recipe)
        if out_path:
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        # 摘要输出到 stdout（供上层程序与冒烟测试解析）
        print("模式: %s" % ("泛科普" if general else "场景处置"))
        print("识别火类: %s" % (",".join(codes) if codes else "无（泛科普）"))
        print("输出字符数: %d" % len(content))
        return 0

    sys.stderr.write("未知命令: %s\n" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
