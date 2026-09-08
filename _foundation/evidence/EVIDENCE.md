# FIre 消防技能系列 · 可验证制品摘要

由 `_foundation/evidence/verify_all.py` 自动生成，任何人克隆本目录后运行同一命令即可在当前机器上重现下列结果。

生成时间：2026-09-08 17:10:08  
权威引用条目：**28** 条（法律/行政法规/部门规章/国家标准/行业指导文件，全部附公开查证入口）
技能包：**10** 个

## 逐包复现结果

| 技能包 | 输出向量复现 | 包内冒烟 | 规则/知识条目 | 出处标注数 | 命中权威清单 |
|---|---|---|---|---|---|
| check-fire-compliance | 3/3 | PASS | 27 | 54 | 100% |
| check-fire-hazard | 3/3 | 38过/0败 | 22 | 44 | 100% |
| check-fire-inspection | 3/3 | 33过/0败 | 28 | 52 | 100% |
| check-fire-smart-maturity | 3/3 | 26过/0败 | 35 | 35 | 100% |
| gen-fire-class-method | 3/3 | 22过/0败 | 16 | 16 | 100% |
| gen-fire-extinguisher | 3/3 | 26过/0败 | 4 | 4 | 100% |
| gen-fire-plan | 3/3 | 48过/0败 | 6 | 6 | 100% |
| gen-fire-remote-duty | 3/3 | PASS | 30 | 30 | 100% |
| gen-fire-training | 3/3 | 49过/0败 | 27 | 27 | 100% |
| qa-fire-law | 3/3 | 43过/0败 | 22 | 44 | 100% |

合计：**217** 条规则/知识条目，**312** 处出处标注，全部可回溯到权威清单。

## 怎么自己验

```bash
cd FIre
python _foundation/evidence/verify_all.py
```

脚本会做三件事并打印结果：核验引用清单字段完整性、用包内引擎重跑随包输入并与随包输出逐字节比对、统计出处标注覆盖率。
引擎为纯规则实现，不含随机与网络调用，同一输入在任何机器上输出一致。

## 边界声明

本系列只做法规条文的结构化整理与主动提示，不替代消防技术服务机构的现场判定，也不构成法律意见。法规修订后以官方最新公布文本为准，具体执行口径以属地消防救援机构意见为准。

## 制品指纹（SHA-256）

| 制品 | 指纹 |
|---|---|
| `_foundation/evidence/citation-manifest.json` | `c121ca71712d5dd7ef7b0af0d5654469138f091f3cb5df7d2141f6477365dce7` |
| `_foundation/evidence/verify_all.py` | `80404f01f84dd660c559e80d68ceb0773b7a0e55e4242a4cd2dfe58b4f6d0205` |
| `_foundation/methodology.md` | `c6b43d388c09e458b998201c078b266325f7608c3100b5194977bf375e5f4c69` |
| `_foundation/regulations.json` | `f2ca51d485306b2bc131015cacd38ca3a76f93160b426b65066bd2be9f7d3b92` |
