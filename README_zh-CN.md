# WikiSkill

**把 Agent 的执行经验，变成下一次能用上的技能。**

给 Agent 一批练习任务和一种检查结果的方法。WikiSkill 会整理它做对、做错的地方，把经验写进持续维护的 Wiki，再生成可以用于后续任务的技能。

本项目基于 **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**，将论文的方法实现到 Codex Agent 上，用于文档分析、表格操作和推理等任务。

[English](README.md) · [快速开始](#快速开始) · [实验结果](docs/research-repeatability-20260908.md) · [原论文](https://arxiv.org/abs/2608.27454)

## 论文提出了什么？

Agent 每次工作都会产生有价值的经验：哪次搜索找到了正确文件、哪个公式出了错、怎样修复才有效。论文关心的是，怎样把这些经验变成可以跨任务积累的知识。

WikiSkill 将它们分成三层：

| 层次 | 保存什么 |
|---|---|
| **原始经验 Raw** | 当时的任务、操作、输出和反馈 |
| **知识 Wiki** | 可复用的模式、原因、成功方法和反例 |
| **技能 Skills** | Agent 工作时可以遵循的具体步骤 |

**Wiki Maintainer** 负责整理经验，**Skill Proposer** 把相关经验写成候选技能。Agent 在验证任务上试用新技能，分数确实提高才保留；技能被拒绝，Wiki 中积累的经验仍然留下。

整个过程改进的是 Agent 的工作方法，不需要训练新的模型权重。

![WikiSkill 学习循环](assets/wikiskill-evolution.svg)

## 一个真实例子：从表格失败中学到了什么？

在我们的 Spreadsheet 实验中，Agent 写好了公式，也检查了重算后的临时文件，但最后提交的却是未经重算的原文件，里面的公式结果仍然为空。

Maintainer 在 Wiki 中记下了这句话：

> “Formula recalculation is useful only if the recalculated file replaces the file handed to the evaluator or user.”

也就是：**只有把重算后的文件真正交给用户，重算才有意义。**

随后产出的技能把它落实成了操作步骤：

> “Never deliver the pre-recalculation workbook while inspecting only a temporary copy.”
>
> “Reopen that exact final output twice: once with formulas visible (`data_only=False`) and once with cached results (`data_only=True`).”

意思是：**检查和交付必须针对同一份最终文件；重新打开它，分别检查公式和计算结果。**

以上英文摘自实际生成的产物。[阅读 Wiki 原页](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md) · [阅读完整技能](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md)

这份技能还写明了公式兼容性、文本与数值类型的区别，以及什么情况下不必重算。它最终成为了一套可以阅读、检查和复用的工作方法。

## 我们实现了什么？

- **完整学习循环**：执行任务、整理 Wiki、提出技能、验证收益、保留或拒绝更新。
- **Codex 接入**：明确配置执行任务和生成技能所用的模型。
- **五类任务适配器**：文档问答、表格编辑、数学、网络研究和 ALFWorld 交互任务。
- **隔离的 Spreadsheet 运行路径**：独立安装即可运行的 macOS 单轮实验，支持 Python/openpyxl、LibreOffice 重算和按角色限定的工具。
- **可检查的过程产物**：查看生成的 Wiki、技能和提案结果，恢复已完成的工作。
- **可复算的研究结果**：公开逐题分数、工件哈希和离线分析脚本。

独立安装包已经完成一次真实闭环：**8 道训练任务、4 道验证任务、Maintainer、Proposer 和候选技能验证**。候选与基线同分，门控因此保留旧版本。[配置与验收记录](docs/isolated-spreadsheet-study.md)

## 可以用在哪些场景？

如果你的 Agent 经常做同类任务，而且有明确反馈、能比较改进前后的表现，WikiSkill 就有用武之地。

| 场景 | 可以学习什么 | 本仓库提供什么 |
|---|---|---|
| **表格自动化** | 编辑公式、重算结果、检查真正交付的文件 | 任务适配器、隔离实验入口和实际生成的技能 |
| **文档分析** | 定位证据、读取表格、区分统计期间、基于资料回答问题 | OfficeQA 指定资料与全库检索适配器 |
| **网络研究** | 改进搜索和证据搜集方法 | SealQA 适配器 |
| **推理任务** | 复用解题步骤，减少反复出现的错误 | 数学任务适配器 |
| **自己的可评分工作流** | 学习针对特定输入、工具和反馈的操作方法 | 用 Python 扩展任务读取、执行和二元评分适配器 |

对于简报、研报或 BriefLoop 这样的多角色工作流，下一步是从已完成任务和人类纠正中学习取证、分析与写作方法。这属于[后续应用方向](docs/research-next-steps.md)，尚未作为内置后端提供。

## 实验结果：同一份技能，三次运行都有提升

我们冻结了上面的 Spreadsheet 技能，让 **Luna/high 在同一批 278 道任务上分别不带技能、带技能执行**，共重复三遍。

| 运行 | 无技能 | 冻结技能 | 提升 |
|---|---:|---:|---:|
| 第 1 遍 | 76.62% | 85.25% | **+8.63pp** |
| 第 2 遍 | 71.94% | 84.17% | **+12.23pp** |
| 第 3 遍 | 72.66% | 87.05% | **+14.39pp** |
| **三遍平均** | **73.74%** | **85.49%** | **+11.75pp** |

后两遍是这次重复性研究的主比较，平均提升 **13.31 个百分点**，按题目聚类的 bootstrap 95% 区间为 **[+9.35，+17.45]pp**。这测量的是同一冻结技能在重复题集上的表现，评分检查任务要求的单元格值；实验由原始研究运行器完成。[完整方法、成本、其他领域结果与证据](docs/research-repeatability-20260908.md)

## 快速开始

需要 Python **3.11+**。离线示例支持 macOS 和 Linux。

```bash
git clone https://github.com/Stahl-G/wikiskill.git
cd wikiskill
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .

# 用合成任务体验学习循环，不需要模型账号。
wikiskill demo runs/demo
wikiskill status runs/demo
```

打开 `runs/demo/wiki/` 看整理出的经验，打开 `runs/demo/skills/` 看技能版本。这个示例会经历接受更新、拒绝更新和不提出修改三种情况。

### 跑一个真实的小型 Spreadsheet 实验

在 macOS 上准备已登录的 Codex CLI、SpreadsheetBench 数据，以及可无界面运行的 LibreOffice 应用。这条入口使用 **Luna/high**，完成一轮有明确预算的学习。

```bash
python -m pip install '.[spreadsheet,paper]'

wikiskill spreadsheet-study prepare runs/spreadsheet \
  --data /path/to/spreadsheet-data \
  --split-dir /path/to/splits \
  --libreoffice-app /path/to/LibreOffice.app

# 开始真实模型调用：最多16次解题和2次学习角色调用。
wikiskill spreadsheet-study run runs/spreadsheet
wikiskill spreadsheet-study status runs/spreadsheet
```

[依赖检查与配置说明](docs/isolated-spreadsheet-study.md) · [其他适配器与数据准备](docs/datasets.md) · [通用演化 CLI](docs/reproduction.md)

## 接下来从哪里看？

| 我想…… | 入口 |
|---|---|
| 理解原始方法 | [WikiSkill 论文](https://huggingface.co/papers/2608.27454) |
| 看 Agent 到底学出了什么 | [Wiki 示例](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md)与[完整技能](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) |
| 自己核对分数 | `python scripts/check_repeatability_20260908.py` |
| 阅读全部实验，包括不确定结果 | [最新报告](docs/research-repeatability-20260908.md)与[历史记录](docs/results.md) |
| 运行或扩展任务 | [复跑说明](docs/reproduction.md)与[数据准备](docs/datasets.md) |
| 了解后续研究和实用化计划 | [下一步](docs/research-next-steps.md) |

## 引用

使用这一方法时，请引用原论文：

```bibtex
@misc{tang2026wikiskill,
  title = {WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution},
  author = {Liyan Tang and Cyrus Rashtchian and Chun-Sung Ferng and Andrew Tomkins and Da-Cheng Juan and Tu Vu},
  year = {2026},
  eprint = {2608.27454},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  url = {https://arxiv.org/abs/2608.27454}
}
```

## 许可

框架代码采用 MIT 许可；第三方评分器和提示词资源保留各自的署名与许可说明。本项目是论文方法的独立实现。见 [LICENSE](LICENSE)、[NOTICE](NOTICE.md) 和[第三方声明](third_party/)。
