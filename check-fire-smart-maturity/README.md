# check-fire-smart-maturity


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

智慧消防成熟度评估（FIre 消防技能系列 #3）。主动 Agent 定位：不仅评估已建了什么，更主动暴露该建还没建什么。

## 快速开始

```bash
python scripts/check.py scan examples/fire-demo-mid.md 我的报告.md
```

## 目录结构

```
check-fire-smart-maturity/
├── SKILL.md                  # 技能说明（含评估框架与边界）
├── README.md                 # 本文件
├── CHANGELOG.md              # 版本记录
├── FAQ.md                    # 常见问题
├── SELF_EVAL.md              # 自评
├── scripts/
│   ├── check.py              # 评估引擎（纯标准库）
│   └── smoke_test.py         # 冒烟测试（自包含，可直接复跑）
├── resources/
│   └── rules.json            # 六维 30 要素 + 5 红线 + 画像与提示词库
├── references/
│   └── regulatory-basis.md   # 权威基座与引用说明（含检索核实日期）
└── examples/
    ├── fire-demo-clean.md    # 样例：成熟综合体（指数 100，L5）
    ├── fire-demo-mid.md      # 样例：起步园区（指数 48，L3）
    ├── fire-demo-high.md     # 样例：瘫痪平台（指数 2，L1，5 红线）
    └── sample-scan-*.md      # 上述样例的真实引擎输出报告
```

## 系列底座

本包属于 FIre 消防技能系列，系列设计方法论与共享引用库见同级 `_foundation/` 目录（`methodology.md`、`regulations.json`）。包内 `references/regulatory-basis.md` 为自包含副本，确保单包可独立分发。

## 复跑冒烟

```bash
python scripts/smoke_test.py
```
