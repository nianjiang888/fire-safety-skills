# qa-fire-law README


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

消防法规问答（主动 Agent 版）—— FIre 消防技能系列 #6，系列首个 qa 范式技能。

## 快速开始

```bash
python scripts/qa.py ask "电动车在楼道充电会怎么罚？" my-answer.md
python scripts/qa.py list
python scripts/qa.py version
python scripts/smoke_test.py   # 冒烟自检
```

## 目录结构

```
qa-fire-law/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── FAQ.md
├── SELF_EVAL.md
├── references/
│   └── regulatory-basis.md   # 权威引用基座
├── resources/
│   └── kb.json               # 知识库（12 类 22 条，每条带出处）
├── scripts/
│   ├── qa.py                 # 引擎（ask / list / version）
│   └── smoke_test.py
└── examples/
    ├── sample-qa-single-duty.md    # 单人值守政策问答
    ├── sample-qa-ev.md             # 电动车罚则问答
    └── sample-qa-threeinone.md     # 三合一住人问答
```

## 引擎设计

- **匹配**：问题归一（去空白与标点）→ 关键词子串命中计分（长度加权）→ 两级判定（长词强命中，或多短词组合）；
- **宁可留白不可错配**：单个 2 字词命中不回答，走诚实兜底；
- **兜底**：承认未覆盖 + 最接近主题 + 全主题导航 + 官方渠道建议。

## 依赖

无。纯 Python 标准库，Python 3.8+。
