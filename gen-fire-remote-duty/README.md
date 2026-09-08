# gen-fire-remote-duty 消控室远程值守方案生成器（主动 Agent 版）


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列 #2。输入单位基础信息，主动生成完整的远程值守方案书，每条判定挂权威出处。

## 快速开始

```bash
python scripts/gen.py gen examples/duty-input-office.md
python scripts/gen.py gen examples/duty-input-office.md plan.md
python scripts/gen.py version
```

运行环境：Python 3.8+，仅标准库，无第三方依赖。

## 目录结构

```
gen-fire-remote-duty/
├── SKILL.md                        技能说明
├── scripts/
│   ├── gen.py                      方案生成引擎
│   └── smoke_test.py               冒烟测试（自包含）
├── resources/
│   └── recipe.json                 配方：画像/23地区政策库/合规条件/人力规则/流程
├── references/
│   └── regulatory-basis.md        权威引用基座（自包含）
└── examples/
    ├── duty-input-office.md        广西写字楼 · 双人 · 信息齐全（输入）
    ├── duty-input-mall.md          山东商场 · 单人 · 缺远程监控证据（输入）
    ├── duty-input-minimal.md       江西养老院 · 极简输入（输入）
    ├── sample-plan-office.md       对应方案书
    ├── sample-plan-mall.md
    └── sample-plan-minimal.md
```

## 三种典型效果

| 输入 | 引擎行为 |
|---|---|
| 广西写字楼（信息齐全，双人） | 命中广西实施办法第二十五条，双人基线 + 有条件单人路径提示；算式透明人力测算；持证核对通过 |
| 山东商场（单人意向，缺证据） | 命中山东条例第三十二条，判"有条件可行"；但 C2/C3/C5 无证据，明确判"X/5 条满足，维持双人值守" |
| 江西养老院（极简输入） | 江西未命中政策库 → 明确留白"未命中，按双人基线"；缺项全部标"待补充"，不编造政策 |

## 自检

```bash
python scripts/smoke_test.py
```

预期：ALL PASS（三案例行为自洽、算式正确、政策库 23 条完整、不编造未命中地区政策）。
