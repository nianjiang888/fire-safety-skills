# check-fire-compliance 消防合规体检（主动 Agent 版）


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列的第 1 个技能。对照消防法规基线，主动发现单位消防安全管理中的合规缺口与违规红线，输出分级报告与可执行的下一步。

## 快速开始

```bash
python scripts/check.py scan examples/fire-demo-clean.md
python scripts/check.py scan examples/fire-demo-clean.md report.md
python scripts/check.py version
```

运行环境：Python 3.8+，仅标准库，无第三方依赖。

## 目录结构

```
check-fire-compliance/
├── SKILL.md                      技能说明（含主动 Agent 定位）
├── scripts/
│   ├── check.py                  主动体检引擎
│   └── smoke_test.py             冒烟测试（自包含）
├── resources/
│   └── rules.json                27 条规则，全部挂权威出处
├── references/
│   └── regulatory-basis.md      权威引用基座（自包含）
└── examples/
    ├── fire-demo-clean.md        高覆盖样例
    ├── fire-demo-mid.md          部分覆盖样例
    ├── fire-demo-high.md         含红线违规样例
    ├── sample-scan-clean.md      对应体检报告
    ├── sample-scan-mid.md
    └── sample-scan-high.md
```

## 自检

```bash
python scripts/smoke_test.py
```

预期：ALL PASS（三档样例画像/覆盖度/红线数自洽，规则库 27 条均有出处）。
