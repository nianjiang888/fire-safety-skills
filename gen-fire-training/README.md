# gen-fire-training 消防培训课件生成器（主动 Agent 版）


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列 #10。输入培训对象/时长/场所，主动生成可开课的培训方案与课件，每条判定挂权威出处。

## 快速开始

```bash
python scripts/gen.py gen examples/train-input-staff.md
python scripts/gen.py gen examples/train-input-staff.md training.md
python scripts/gen.py version
```

运行环境：Python 3.8+，仅标准库，无第三方依赖。

## 目录结构

```
gen-fire-training/
├── SKILL.md                        技能说明
├── scripts/
│   ├── gen.py                      培训方案生成引擎
│   └── smoke_test.py               冒烟测试（自包含）
├── resources/
│   └── recipe.json                 配方：7类受众/11个模块/3档时长/10道题库/留痕与复训规则
├── references/
│   └── regulatory-basis.md        权威引用基座（自包含）
└── examples/
    ├── train-input-staff.md        酒店全员 · 45分钟（输入）
    ├── train-input-micro.md        商场微型站 · 半天（输入）
    ├── train-input-minimal.md      新员工 · 极简（输入）
    ├── sample-training-staff.md    对应方案
    ├── sample-training-micro.md
    └── sample-training-minimal.md
```

## 三种典型效果

| 输入 | 引擎行为 |
|---|---|
| 酒店全员（45分钟） | 四模块排课；"疏散逃生"主题自动标星；题库缩为 6 题；超课时给压缩顺序提示 |
| 商场微型站（半天） | 识别微型站受众，受众默认方案 ∪ 时长方案 = 8 模块；含"3分钟到场"处置流程；10 题考核 |
| 新员工（极简） | 正确识别"新员工岗前"（不被泛化"员工"抢先）；时长缺省按 90 分钟并标注假设；岗前留痕要求主动提示 |

## 自检

```bash
python scripts/smoke_test.py
```

预期：ALL PASS（三案例行为自洽、受众识别正确、选课并集正确、题库与出处完整、超课时校准、配方完整、免费合规）。
