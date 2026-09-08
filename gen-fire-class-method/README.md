# gen-fire-class-method 火灾分类与灭火方法生成器


> **技术背书与可验证制品**：本技能的每一条判定规则都挂载了可核验的法规/标准出处（发布机构、文号、施行日期、查证方式见 `references/regulatory-basis.md` 与 `references/verifiable-artifacts.md`）。引擎为纯规则实现，同一输入在任何机器上输出一致，包内 `python scripts/smoke_test.py` 可一键复现。当前版本免费使用。

FIre 消防系列第 7 个技能。依据 GB/T 4968-2008 将火灾分为 A-F 六类，给出各类适用/禁用灭火剂、灭火四原理与常见处置误区，并对用户输入的具体场景主动识别火类、给出处置要点。

## 快速使用

```bash
python scripts/gen.py gen examples/class-input-kitchen.md out.md   # 生成简报
python scripts/gen.py version                                       # 版本
python scripts/gen.py validate                                      # 校验配方
python scripts/smoke_test.py                                        # 自测
```

## 输入示例

- 泛科普：`请讲讲火灾分类和灭火方法，给新员工做科普材料`
- 场景：`厨房油锅着火了，我能直接用水泼灭吗？`
- 场景：`配电柜突然着火，我第一反应用水浇对不对？`

## 输出结构

1. 场景识别（命中火类）
2. 针对该场景的处置要点（仅场景模式）
3. 火灾六类划分表（GB/T 4968-2008）
4. 灭火四种基本方法
5. 常见处置误区（主动提示，封顶 6 条）
6. 特别提醒（命中油锅/带电/金属时追加）
7. 免责声明

## 依赖与授权

纯 Python 标准库，零第三方依赖。当前 `a2m.enabled: false`，免费使用。仅供学习科普与初期处置参考，不构成专业消防设计或救援指令。
