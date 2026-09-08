# WikiSkill

**把 Agent 的执行经验，变成下一次能用上的技能。**

给 Agent 一批练习任务和一种检查结果的方法。WikiSkill 会整理它做对、做错的地方，把经验写进持续维护的 Wiki，再生成可以用于后续任务的技能。

本项目基于 **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**，让你正在使用的 Agent 用自己的模型和正常工具，进入基于经验的改进循环。

[English](README.md) · [安装入口技能](#快速开始) · [产品指南](docs/product-guide.md) · [实验结果](docs/research-repeatability-20260908.md) · [原论文](https://arxiv.org/abs/2608.27454)

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

![WikiSkill 学习循环](assets/wikiskill-evolution-zh-CN.svg)

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
- **使用自己的 Agent 和模型**：产品入口采用宿主 Agent 协议，不锁定模型，也不强制建立沙箱。
- **支持自己的任务和评分**：输入可以是 JSON 或文件，评分可以是任意有限数值，支持越高越好或越低越好；样本量与轮数由你决定。
- **跨批次积累经验**：用 `start --from` 将保留的技能、Wiki 和反馈带入新任务。
- **人类建议直接进入 Wiki**：保留原话，再与任务经验关联。
- **可安装的入口技能**：直接让 Agent 开始、恢复、检查或导出改进循环。
- **五类任务适配器**：文档问答、表格编辑、数学、网络研究和 ALFWorld 交互任务。
- **独立保留的隔离研究路径**：独立安装即可运行的 macOS 单轮实验，支持 Python/openpyxl、LibreOffice 重算和按角色限定的工具。
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
| **自己的可评分工作流** | 学习针对特定输入、工具和反馈的操作方法 | 任务 JSON、当前 Agent，以及外部评分器或明确的人类／评审评分 |

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

控制器需要 Python **3.11+**。产品模式在 macOS、Linux 或 Windows 上使用 Agent 自己的正常环境。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install git+https://github.com/Stahl-G/wikiskill.git
npx skills add Stahl-G/wikiskill --skill wikiskill
```

Windows PowerShell 请将激活命令替换为 `.venv\Scripts\Activate.ps1`；已有项目虚拟环境也可以直接复用。

然后直接对 Agent 说：

> 用 WikiSkill，根据这些任务样本和我的反馈改进这个技能。用项目测试来评价，先做一轮。

[入口技能](skills/wikiskill/SKILL.md)会指导 Agent 准备任务、执行、整理 Wiki、提出技能并验证。模型、工具和预算由你选择；它不会偷偷启动固定供应商的模型或改变宿主权限。

### 使用 CLI，或接入其他 Agent

```bash
# 用自己的任务创建工作区。
wikiskill start runs/my-task --tasks tasks.json --rounds 2

# 让当前 Agent 获取并执行下一项任务。
wikiskill next runs/my-task

# 直接记入反馈，或查看进度。
wikiskill feedback runs/my-task --text "检查真正要交付的文件。"
wikiskill status runs/my-task

# 循环完成后导出保留的技能。
wikiskill export runs/my-task ./improved-skill
```

外部评分器首次运行前会展示命令和工作目录；本机确认后，未改变的配置不会每道题重复询问。[评分器信任说明](docs/product-guide.md#review-an-external-scorer-once)。

可以用 `--scorer '["python", "score.py"]'` 接入自己的评分器，也可以记录人类或明确评审规则给出的分数。控制器发出工作请求，由当前 Agent 执行并记录实际结果。[任务格式、评分与完整用法](docs/product-guide.md) · [小型任务示例](examples/text-cleanup/)

### 先体验离线示例

```bash
wikiskill demo runs/demo
wikiskill status runs/demo
```

合成示例不需要模型账号，会经历接受、拒绝和不提出修改三种情况。打开 `runs/demo/wiki/` 和 `runs/demo/skills/` 即可查看产物。

原有基准适配器和 macOS 隔离 Spreadsheet 实验作为独立研究工具保留。[研究入口](docs/isolated-spreadsheet-study.md) · [数据准备](docs/datasets.md) · [旧版演化 CLI](docs/reproduction.md)

## 接下来从哪里看？

| 我想…… | 入口 |
|---|---|
| 理解原始方法 | [WikiSkill 论文](https://huggingface.co/papers/2608.27454) |
| 看 Agent 到底学出了什么 | [Wiki 示例](src/wikiskill/resources/research/repeatability-20260908/wiki-deliver-the-recalculated-workbook.md)与[完整技能](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) |
| 自己核对分数 | `python scripts/check_repeatability_20260908.py` |
| 阅读全部实验，包括不确定结果 | [最新报告](docs/research-repeatability-20260908.md)与[历史记录](docs/results.md) |
| 改进自己的任务 | [产品指南](docs/product-guide.md)与[入口技能](skills/wikiskill/SKILL.md) |
| 运行研究适配器 | [复跑说明](docs/reproduction.md)与[数据准备](docs/datasets.md) |
| 了解后续研究和实用化计划 | [下一步](docs/research-next-steps.md) |

可直接使用[表格交付样例](examples/workbook-delivery/)：用四份公开的合成工作簿学习和验证公式编辑、重算与交付检查。

独立 Agent 已通过安装后的产品入口完成这套表格流程，包括 Wiki 维护和候选验证。[实际结果与发现的配置问题](docs/product-first-use-validation.md)。

## 查看进度与使用结果

Agent 会根据你的例子和验收标准整理任务文件。你可以随时检查准备情况、进度和结果：

```bash
wikiskill preflight runs/my-task
wikiskill status runs/my-task --human
wikiskill report runs/my-task
```

结果报告展示门控裁决、逐题改善与退步、实际技能差异和 Wiki 经验。完成后，使用 `wikiskill install runs/my-task ./my-skills/task-name` 安装保留的技能；已授权的 `--replace` 会备份旧文件并返回恢复命令。技能所需的工具和辅助文件仍需就绪。[安装与恢复说明](docs/product-guide.md#install-and-recover-a-local-skill)。

运行 `wikiskill doctor` 可查看发行包与安装路径。本项目是 **Stahl-G/wikiskill**，发行包名为 **wikiskill-research**，可据此区分同名命令。

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
