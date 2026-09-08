# FIre · 消防技能系列

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Deps](https://img.shields.io/badge/dependencies-0-brightgreen.svg)
![Citations](https://img.shields.io/badge/citations-28-blue.svg)
![Coverage](https://img.shields.io/badge/citation%20coverage-100%25-brightgreen.svg)
![Reproducible](https://img.shields.io/badge/reproducible-30%2F30-brightgreen.svg)

一套面向社会单位消防管理的 AI 技能集合。核心主张只有一句：**每一条结论都能被查证。**

系列共 10 个技能包，覆盖"查—算—答—写"四类动作。全部免费，全部自包含（包内即可跑通），全部规则挂载可核验的法规/标准出处。

---

## 为什么是这套做法

消防领域的自动化工具，一类只会搬条文，一类凭语感生成看起来专业的方案。前者没用，后者危险——网上流传的模板里，GB 35181-2017 已于 2025-11-01 废止却仍被引用、GB 50444-2008"出厂满 5 年首修"已被 GB 55036-2022 覆盖却仍被当作强制要求，这类错误比比皆是。

FIre 的做法是第三条路：把可核验的条文变成可执行的判断规则，工具敢下结论，同时每一条结论都能查证。

四条设计约束：

1. **引用必须有出处**，文号存疑的宁可不写（例如"四个能力"各地文号不一致，只写能力项、不编文号）
2. **主动但不骚扰**——主动暴露缺口，行动清单强制封顶，超出范围直说做不了
3. **确定性优先于聪明**——纯规则引擎，同一输入在任何机器上输出一致
4. **边界写在明处**——不替代现场判定，不构成法律意见

完整说明见 `_foundation/evidence/METHODOLOGY.md`。

---

## 技能一览

| # | 技能包 | 类型 | 做什么 |
|---|---|---|---|
| 1 | check-fire-compliance | check | 消防合规体检：9 个维度 27 条规则，识别单位画像、暴露缺失、红线置顶、给 Top10 行动清单 |
| 2 | gen-fire-remote-duty | gen | 远程值守方案：23 个地区单人值守政策逐条对照，合规条件与人力算式一并给出 |
| 3 | check-fire-smart-maturity | check | 智慧消防成熟度：6 维度 30 要素 5 红线，出成熟度指数与 L1–L5 分级 |
| 4 | gen-fire-extinguisher | gen | 灭火器配置：按 GB 50140 的 Q=KS/U 计算，反推设置点，核查现有配置 |
| 5 | check-fire-hazard | check | 防火隐患识别：隐患三档定级，每条给条款依据、罚则、整改建议 |
| 6 | qa-fire-law | qa | 消防法规问答：12 类 22 条知识库，命中给条文，未命中诚实兜底 |
| 7 | gen-fire-class-method | gen | 火灾分类与灭火方法：按 GB/T 4968 判定火类，给适用与禁用灭火剂 |
| 8 | gen-fire-plan | gen | 预案生成：部位级火情预想、组织机构按规模测算、七步处置、演练频次 |
| 9 | check-fire-inspection | check | 设施巡检：15 项巡检基线、9 类坏状态红线、场所法定频次判定 |
| 10 | gen-fire-training | gen | 培训课件：7 类受众、11 个模块、3 档时长排课、逐页课件与考核题 |

---

## 自己动手验证

```bash
python _foundation/evidence/verify_all.py
```

一条命令做四件事，并生成 `_foundation/evidence/EVIDENCE.md`：

| 检查项 | 内容 |
|---|---|
| 引用清单自检 | 28 条权威引用，核验字段完整性与状态标注 |
| 输出向量复现 | 10 个包共 30 组输入，用包内引擎重跑并与随包输出逐字节比对 |
| 包内冒烟汇总 | 各包 `smoke_test.py` 结果（合计 315 项断言） |
| 出处覆盖率 | 217 条规则/知识条目、312 处出处标注，要求 100% 命中权威清单 |

引擎为纯规则实现，无随机、无网络调用。报告日期可用环境变量 `FIRE_GEN_DATE` 固定，便于自动化比对。

---

## 目录结构

```
FIre/
├── _foundation/           系列共享底座
│   ├── regulations.json        权威引用库（13 条核心，含条款要点）
│   ├── methodology.md          系列设计地基
│   └── evidence/               可验证制品
│       ├── citation-manifest.json   可核验引用清单（28 条，含查证入口）
│       ├── verify_all.py            一键复现脚本
│       ├── gen_artifacts.py         逐包制品生成器
│       ├── METHODOLOGY.md           方法学说明
│       └── EVIDENCE.md              证据摘要（自动生成，含 SHA-256 指纹）
├── check-fire-<name>/     体检类技能
├── gen-fire-<name>/       生成类技能
├── qa-fire-law/           问答类技能
└── *.zip                  发布包（包根即技能根）
```

每个技能包结构一致：`SKILL.md`（技能定义）、`scripts/`（引擎与冒烟）、`resources/`（规则/配方/知识库）、`references/`（依据与可验证制品）、`examples/`（三档输入与随包输出）、`README.md`、`FAQ.md`、`CHANGELOG.md`、`SELF_EVAL.md`。

---

## 从 GitHub 导入到 SkillHub

仓库按 SkillHub 的导入规则组织：每个技能独立目录，目录根即 `SKILL.md`，不含二进制文件（`*.zip` 已排除，需要发布包时用 `_tools/pack_skill.py` 重建）。

在 SkillHub 发布页选「从 GitHub 导入」，绑定账号后会自动扫出 10 个候选。平台单次最多导入 5 个，所以要**分两批**：

| 批次 | 技能 |
|---|---|
| 第一批 | check-fire-compliance、gen-fire-remote-duty、check-fire-smart-maturity、gen-fire-extinguisher、check-fire-hazard |
| 第二批 | qa-fire-law、gen-fire-class-method、gen-fire-plan、check-fire-inspection、gen-fire-training |

导入时 Slug 沿用目录名即可（如 `gen-fire-plan`），显示名称与描述留空会自动读取 `SKILL.md` 的 frontmatter。

后续更新在本仓库提交后，重新导入同一仓库即可刷新，平台按文件清单变化生成新的日期版本号。

---

## 本地使用

```bash
git clone <仓库地址>
```

把需要的技能目录整体复制到你的 Agent skills 目录即可，无需安装依赖（全部只用 Python 标准库）。

单个技能这样跑：

```bash
python gen-fire-plan/scripts/gen.py gen \
       gen-fire-plan/examples/plan-input-office.md 输出报告.md
```

---

## 边界声明

本系列只做法规条文的结构化整理与主动提示，不替代消防技术服务机构的现场判定，也不构成法律意见。法规修订后以官方最新公布文本为准；地方规定差异较大，具体执行口径以属地消防救援机构意见为准。
