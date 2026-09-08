# check-fire-hazard README


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

防火隐患识别（主动 Agent 版）—— FIre 消防技能系列 #5。

## 快速开始

```bash
python scripts/check.py scan examples/fire-demo-mid.md my-report.md
python scripts/check.py version
python scripts/smoke_test.py   # 冒烟自检
```

## 目录结构

```
check-fire-hazard/
├── SKILL.md                # 技能说明（触发、用法、边界）
├── README.md
├── CHANGELOG.md
├── FAQ.md
├── SELF_EVAL.md
├── references/
│   └── regulatory-basis.md # 权威引用基座（全部带核实来源）
├── resources/
│   └── rules.json          # 22 条隐患规则（红线/高危/提示三档）
├── scripts/
│   ├── check.py            # 引擎（scan / version）
│   └── smoke_test.py       # 自包含冒烟测试
└── examples/
    ├── fire-demo-clean/mid/high.md   # 三档示例输入
    └── sample-scan-clean/mid/high.md # 真实引擎输出报告
```

## 规则覆盖（22 条 / 三档）

- 疏散与出口：锁闭安全出口、占用堵塞疏散通道、常闭防火门常开、卷帘下堆物、门窗设障碍物、占用消防车通道、占用避难层
- 设施器材：擅自停用消防设施、圈占遮挡消火栓、器材缺失、器材失效超期、无维保
- 电动自行车：楼道停放/充电、飞线充电（部令第 5 号 §37/§47 + 公安部通告）
- 值守：消控室无人值守、值班人员无证
- 用火用电：违规动火作业、私拉乱接
- 空间使用：三合一违规住人、电缆井管道井堆物
- 管理：油烟管道未清洗、防火巡查缺失、员工培训缺失

每条规则含：匹配词、严重度、条款依据（条款代号 + 原文口径）、法定罚则区间、整改动作。

## 依赖

无。纯 Python 标准库，Python 3.8+。
