# gen-fire-extinguisher


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

灭火器配置顾问（FIre 消防技能系列 #4）。按 GB 50140-2005 做查表计算，生成透明可复算的配置方案书。

## 快速开始

```bash
python scripts/gen.py gen examples/ext-input-office.md 我的方案.md
```

## 目录结构

```
gen-fire-extinguisher/
├── SKILL.md                  # 技能说明（用法与边界）
├── README.md                 # 本文件
├── CHANGELOG.md              # 版本记录
├── FAQ.md                    # 常见问题
├── SELF_EVAL.md              # 自评
├── scripts/
│   ├── gen.py                # 计算引擎（纯标准库）
│   └── smoke_test.py         # 冒烟测试（自包含，可直接复跑）
├── resources/
│   └── recipe.json           # 基准表/K表/保护距离/型号库/等级判据（全带条款号）
├── references/
│   └── regulatory-basis.md   # 权威基座与引用说明（含核实日期）
└── examples/
    ├── ext-input-office.md   # 样例输入：办公室（Q=8A，暂未配置）
    ├── ext-input-mall.md     # 样例输入：商场（1.3加严+K0.5，现有配置不达标）
    ├── ext-input-store.md    # 样例输入：便利店（现有单具级别不达标）
    └── sample-plan-*.md      # 上述样例的真实引擎输出方案书
```

## 系列底座

本包属于 FIre 消防技能系列，系列设计方法论与共享引用库见同级 `_foundation/` 目录。包内 `references/regulatory-basis.md` 为自包含副本，确保单包可独立分发。

## 复跑冒烟

```bash
python scripts/smoke_test.py
```
