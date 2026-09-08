# gen-fire-plan 灭火和应急疏散预案生成器（主动 Agent 版）


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列 #8。输入单位基础信息，主动生成完整的灭火和应急疏散预案书，每条判定挂权威出处。

## 快速开始

```bash
python scripts/gen.py gen examples/plan-input-office.md
python scripts/gen.py gen examples/plan-input-office.md plan.md
python scripts/gen.py version
```

运行环境：Python 3.8+，仅标准库，无第三方依赖。

## 目录结构

```
gen-fire-plan/
├── SKILL.md                        技能说明
├── scripts/
│   ├── gen.py                      预案生成引擎
│   └── smoke_test.py               冒烟测试（自包含）
├── resources/
│   └── recipe.json                 配方：画像/法规依据/组织机构/火情预想模板/演练规则
├── references/
│   └── regulatory-basis.md        权威引用基座（自包含）
└── examples/
    ├── plan-input-office.md        写字楼 · 全信息（输入）
    ├── plan-input-mall.md          商场 · 缺演练记录（输入）
    ├── plan-input-minimal.md       养老院 · 极简输入（输入）
    ├── sample-plan-office.md       对应预案书
    ├── sample-plan-mall.md
    └── sample-plan-minimal.md
```

## 三种典型效果

| 输入 | 引擎行为 |
|---|---|
| 写字楼（全信息，1800人） | 组织机构按规模系数 ×3 测算（灭火行动组 9 人）；配电室/厨房/车库逐一生成部位级火情预想；演练现状自述"每年一次"被引用核验 |
| 商场（缺演练） | 画像=商业综合体；影院部位未匹配模板→明确标"须专项研判"不硬套；演练从未组织→判定"待补齐"并给法定频次 |
| 养老院（极简） | 画像=医疗养老（含失能人员提示）；缺项全部标"待补充"，不编造火情预想；预案骨架完整可继续补 |

## 自检

```bash
python scripts/smoke_test.py
```

预期：ALL PASS（三案例行为自洽、规模缩放正确、不编造未提供部位的场景、配方完整、免费合规）。
