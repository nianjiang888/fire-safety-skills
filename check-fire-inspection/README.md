# check-fire-inspection 消防设施巡检助手（主动 Agent 版）


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列 #9。输入巡检记录/设施现状，主动发现巡检覆盖缺口与红线信号，每条判定挂权威出处。

## 快速开始

```bash
python scripts/check.py scan examples/insp-input-office.md
python scripts/check.py scan examples/insp-input-office.md report.md
python scripts/check.py version
```

运行环境：Python 3.8+，仅标准库，无第三方依赖。

## 目录结构

```
check-fire-inspection/
├── SKILL.md                        技能说明
├── scripts/
│   ├── check.py                    巡检判定引擎
│   └── smoke_test.py               冒烟测试（自包含）
├── resources/
│   └── rules.json                  规则库：15项巡检基线 + 9类坏状态 + 场所频次
├── references/
│   └── regulatory-basis.md        权威引用基座（自包含）
└── examples/
    ├── insp-input-office.md        写字楼 · 覆盖良好（输入）
    ├── insp-input-mall.md          商场 · 多红线（输入）
    ├── insp-input-minimal.md       养老院 · 极简（输入）
    ├── sample-scan-office.md       对应报告
    ├── sample-scan-mall.md
    └── sample-scan-minimal.md
```

## 三种典型效果

| 输入 | 引擎行为 |
|---|---|
| 写字楼（覆盖良好） | 画像=重点单位（每日巡查频次）；覆盖度 73 分；无红线；喷淋末端、应急照明等 4 项缺口仍主动列出 |
| 商场（多红线） | 主机屏蔽/消火栓无水/记录补签三条红线置顶并附罚则；覆盖度封顶 40 分；商场专属自查清单 |
| 养老院（极简） | 只提灭火器与"每天巡查"→ 覆盖度 13 分，12 项缺口主动摆出；兜底频次与医疗场所自查清单 |

## 自检

```bash
python scripts/smoke_test.py
```

预期：ALL PASS（三案例行为自洽、红线判定与罚则展示正确、画像频次正确、清单封顶、规则库完整、免费合规）。
