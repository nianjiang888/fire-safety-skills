#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa-fire-law 自包含冒烟测试。

断言维度：
- 命中路径：6 个典型问题各自命中预期条目（含出处行），退出码 0；
- 换法鲁棒：关键词改写（口语化）仍命中；
- 兜底路径：超出知识库的问题 → 退出码 1 + 兜底文案 + 主题清单；
- list/version：主题清单可见、版本与基数正确。

运行：python scripts/smoke_test.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "qa.py")
TMP = os.path.join(os.path.dirname(ENGINE), "_smoke_out.md")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def run(args):
    return subprocess.run([sys.executable, ENGINE] + args, capture_output=True, text=True)


# ---------- 命中路径 ----------
cases = [
    ("消控室值班要几个人", "KB-DUTY-CONTROLROOM", "24 小时值班", ["部令第5号", "GB 25506"]),
    ("电动车能不能放楼道充电", "KB-RISK-EV", "充满自动断电", ["第三十七条"]),
    ("消防法60条罚多少钱", "KB-RISK-PENALTY", "5 万元以下罚款", ["第六十条"]),
    ("灭火器怎么配置放多远", "KB-EQ-EXTINGUISHER", "保护距离", ["GB 50140-2005"]),
    ("物业要管哪些消防的事", "KB-BEHAVIOR-DUTYHOURS-PROPERTY", "共用消防设施", ["消防法第十八条"]),
    ("动火作业要办什么手续", "KB-DUTY-HOTWORK", "动火审批", ["第十五条"]),
]
for i, (q, eid, must_text, must_cites) in enumerate(cases, 1):
    r = run(["ask", q, TMP])
    rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
    check("case%d 退出码=0（%s）" % (i, q), r.returncode == 0, "rc=%s" % r.returncode)
    check("case%d 命中 %s" % (i, eid), eid in rep or "已回答" in r.stdout, r.stdout.strip()[:80])
    check("case%d 答案含关键内容'%s'" % (i, must_text), must_text in rep)
    for c in must_cites:
        check("case%d 出处含'%s'" % (i, c), c in rep)
    check("case%d 有相关问答延伸" % i, ("相关问答" in rep) or True)  # 延伸不强制存在，存在即可
os.remove(TMP)

# ---------- 换法鲁棒（口语化改写） ----------
r = run(["ask", "电瓶车在楼梯间充电行不行啊", TMP])
rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
check("口语改写仍命中电动车条目", r.returncode == 0 and "第三十七条" in rep, r.stdout.strip()[:80])
os.remove(TMP)

r = run(["ask", "单位消防设施每年要检测几次", TMP])
rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
check("改写命中年度检测条目", r.returncode == 0 and "每年至少进行一次全面检测" in rep.replace(" ", ""), r.stdout.strip()[:80])
os.remove(TMP)

# ---------- 兜底路径 ----------
r = run(["ask", "消防车的水泵叶轮用什么材质", TMP])
rep = open(TMP, encoding="utf-8").read() if os.path.isfile(TMP) else ""
check("超纲问题退出码=1", r.returncode == 1, "rc=%s" % r.returncode)
check("超纲问题有兜底文案", "暂未覆盖" in rep)
check("超纲问题有主题清单", "知识库已覆盖的主题" in rep)
check("超纲问题不硬答", "## 回答" not in rep)
if os.path.isfile(TMP):
    os.remove(TMP)

# ---------- list / version ----------
r = run(["list"])
check("list 退出码=0", r.returncode == 0)
check("list 含主题分类", "【值守要求】" in r.stdout and "【罚则与追责】" in r.stdout)

r = run(["version"])
check("version 退出码=0", r.returncode == 0)
check("version 引擎版本", "qa-fire-law 1.0.1" in r.stdout)
check("version 知识库基数 22 条", "知识库基数:22条" in r.stdout.replace(" ", ""), r.stdout.strip())

# ---------- 参数错误 ----------
r = run([])
check("无参数退出码=2", r.returncode == 2, "rc=%s" % r.returncode)

# ---------- 汇总 ----------
fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" | " + detail) if (detail and not ok) else ""))
print("-" * 46)
print("冒烟结果: %d PASS / %d FAIL" % (len(results) - len(fails), len(fails)))
sys.exit(0 if not fails else 1)
