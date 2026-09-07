# WikiSkill

**面向可评测 Agent 任务的技能自进化框架。**

> **研究结果（2026-09-07）：** 修正后的 Spreadsheet 固定划分重跑，在 Luna/high 下使用一个冻结技能，从 **213/278 提升至 237/278（+8.63pp）**。SealQA 结论仍不确定；数学重复验证仍属探索性研究。此前测试集暴露、评分边界与协议修订见[最终记录](docs/research-final-20260907.md)。

基于 **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**（Liyan Tang 等，2026）。本仓库是该论文方法的独立实现，原始方法贡献归属论文作者。

[Hugging Face 论文页](https://huggingface.co/papers/2608.27454) · [arXiv 原文](https://arxiv.org/abs/2608.27454)

WikiSkill 将执行经验整理为持久知识，再将知识转化为可复用的程序性指导：Agent 执行任务，Wiki Maintainer 整理模式，Skill Proposer 提出修改，确定性验证门控决定是否保留。技能被拒绝时，Wiki 中的经验继续保存。

本仓库是独立研究实现，当前提供 Codex runtime 与文档问答、表格操作、数学、检索、具身交互五类任务适配器。框架可扩展到具有可靠评分、可重复执行、独立训练/选择/测试数据的任务。

[English](README.md) · [完整结果](docs/results.md) · [复跑说明](docs/reproduction.md) · [数据准备](docs/datasets.md)

## 最新研究观察

修正后的 Spreadsheet `feedback-v3` 研究，在 **Luna/high 执行条件下使用一个冻结技能**，观察到正向配对差异。两臂均在同一组 278 题上重新执行。研究者此前已看过旧测试结果，因此这是**固定划分重跑（fixed-split rerun）**，不是完全未见的确认性测试。它不证明 Wiki 具有独立因果贡献，也不保证之后每次演化都会改善。

| 已完成观察 | 无技能 → 冻结技能 | 净差 | 改善 / 退化题 | 统计证据 |
|---|---:|---:|---:|---|
| Spreadsheet，修正后 `feedback-v3`，278 对 | 213/278 → 237/278 | **+8.63pp** | 31 / 7 | 精确 p=0.000116；四域 Bonferroni p=0.000465；配对 95% CI [+4.68，+12.95]pp |
| SealQA，原冻结技能，85 对 | 41/85 → 44/85 | **+3.53pp** | 10 / 7 | 精确 p=0.6291；四域校正 p=1；配对 95% CI [−5.88，+12.94]pp |

Spreadsheet 候选由验证集选择（**28/40 → 32/40**）。测试评分检查目标单元格的缓存值，不验证全工作簿格式、动态公式行为或目标区域外内容。封存尝试的平均耗时从 **94.11 秒升至 121.05 秒（+28.64%）**，累计工具调用从 **1,287 次增至 1,766 次**。四次传输失败各重试一次，失败记录保留；这些开销数字没有包含失败尝试的全部成本。

SealQA 使用原冻结技能，未改用后来验证集达到 7/10 的候选。一次技能臂超时，按用户在该次超时后批准追加的协议记零；另一次 `view_image` 把 HTTPS URL 当成本地路径，返回 `ENOENT`，未取得数据。经证据限定的审计修订恢复了后者的原始 completion，没有重采样。两项修订均影响结果的解释范围。

数学重复验证共 **18 个题目 ID × 4 臂 × 2 次重复 = 144 次新调用**，执行模型均为 Luna/high，工具调用为零。相对无技能，旧 Luna 技能平均 **+13.89pp**、新 Luna 技能 **+11.11pp**、Astra 编写的技能 **0.00pp**。独立题目簇仍是 18 个，不能将两次重复当成 36 道独立题。这些题目已用于验证，探索性区间未做多臂校正，不支持独立测试集泛化结论。Astra 仅为 Luna 编写了一份技能，未评测 Astra 执行能力，也不证明其提案能力更强。

**实现边界：** 上述结果从原始研究 harness 导入。本包便携适配器已提供成功／失败配比、现代工具摘要、论文契约辅助模块及提示词转录；默认 CLI 仍保留旧提案传输格式，**不是产生这些结果的完整隔离研究运行端**。

[最终方法、结果与限制](docs/research-final-20260907.md) · [仅分数证据及 manifest](src/wikiskill/resources/research/final-20260907) · [冻结 Spreadsheet 技能](src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) · [论文提示词资源](src/wikiskill/resources/paper_alignment)

链接中的技能是供检查的实验工件，发布它不会自动安装或启用它。

```bash
# 离线重算及完整性检查，不调用模型
python scripts/check_research_final_20260907.py
```

<details>
<summary>9月7日较早观察——保留各自冻结技能与协议</summary>

此前 Luna/high 的 OfficeQA 与 Spreadsheet 研究均为统计结论不确定：

| 较早研究 | 无技能 → 冻结技能 | 净差 | 改善 / 退化题 | 证据 |
|---|---:|---:|---:|---|
| OfficeQA V1，论文文档工具 | 98/172 → 104/172 | +3.49pp | 19 / 13 | p=0.377；95% CI [−2.91，+9.88]pp |
| Spreadsheet，隔离 Python 扩展 | 221/278 → 227/278 | +2.16pp | 16 / 10 | p=0.327；95% CI [−1.44，+5.76]pp |

这些观察按原始条件保留。上方修正后的 Spreadsheet 重跑使用不同的冻结技能与协议；更大的净差不能识别某一项修复的独立因果效果。

24 题、六条件 effort 筛查未证明技能收益随推理档位递增：medium **15→17**、high **16→18**、max **20→19**。这是探索性验证。此前 Sol V1→V2 和 LiveMath 原始观察保留在[9月6日记录](docs/research-update-20260906.md)，LiveMath 的无工具条件违例没有撤销。

论文对照发现：旧 Maintainer 初始样本可能全是失败题，内联摘要漏掉现代工具事件，Spreadsheet 又没有得到合法的目标区域元数据。修正后的研究路径恢复成功／失败配比、论文增量编辑与技能适用条件契约、Spreadsheet 合法输入，并统一 train/val/test 工具。OfficeQA 使用 glob/grep/read；Spreadsheet 使用隔离 bash，可进行公式重算。各项修复的独立效果尚未通过消融实验测量。

[较早检查点及对齐记录](docs/research-update-20260907.md) · [较早分数工件](src/wikiskill/resources/research/update-20260907)

论文对齐模块的 Wiki 契约兼容无害的文件名差异：缺少 `.md` 时自动归一化，支持下划线、连字符和 Unicode 名称，索引路径随存储名对应。路径越界和歧义覆盖仍会报错；历史冻结快照保持不变。

</details>

<details>
<summary>展开9月5日历史验证快照——保留受污染检索观察用于追溯</summary>

### 历史验证记录

2026-09-05 09:05 UTC 快照共记录 **12 次 ACCEPT，涉及 9 个任务设置×模型单元**。

| 设置 | 模型 | 无技能 | 当前保留 val 分数 | 增量 |
|---|---|---:|---:|---:|
| OfficeQA 全库检索 | Sol | 18/24 · 75.0% | **23/24 · 95.8%** | **+20.8pp** |
| OfficeQA 全库检索 | 5.5 | 19/24 · 79.2% | **21/24 · 87.5%** | **+8.3pp** |
| SpreadsheetBench | 5.5 | 30/40 · 75.0% | **33/40 · 82.5%** | **+7.5pp** |
| SpreadsheetBench | Sol | 33/40 · 82.5% | **34/40 · 85.0%** | **+2.5pp** |

以上是单条演化轨迹中反复选择得到的验证集分数，尚不是独立 test 上确认的收益，也不代表统计显著。这些状态对应9月5日历史快照，当前研究另行报告。完整表保留无改善、未完成和未运行单元。

这些分数来自本包抽取前的原始实验 harness。本包新增了统一入口、尝试归档与恢复处理，并完成离线检查；没有为了发布重新调用模型跑一遍成绩。具体差异见复跑说明。


当前隔离审计、历史实验限制与修正复现范围见[泛化研究状态](docs/generalization-status.md)。


</details>

## 工作原理

![WikiSkill 技能演化循环](assets/wikiskill-evolution.svg)

- **原始经验：** 每次推理都有独立目录，以及成功结果或失败记录。
- **Wiki：** 从训练轨迹中提取的模式会跨接受和拒绝持续保留。
- **技能：** 当前技能会原样注入任务提示。
- **门控：** 只有完整验证分严格高于当前最佳分时才保留候选；平局也拒绝。`no_action` 会在不评测候选的情况下结束该轮。
- **恢复：** 已完成结果可复用；基础设施失败会保留并显式报告。工作区锁防止多个写者同时运行。

## 快速开始

新增可选的 macOS `wikiskill spreadsheet-study` 入口，用于隔离的单轮 Spreadsheet 开发验证，冻结调用方提供的数据，保留旧 CLI 路径。见[配置与范围](docs/isolated-spreadsheet-study.md)。这条新路径不是历史公开分数的来源。


主程序需要 Python 3.11+，支持 macOS/Linux；ALFWorld 需另配环境。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
wikiskill demo runs/demo
wikiskill status runs/demo
wikiskill results
python -m pytest -q
```

`demo` 用合成确定性结果演示接受、拒绝与 no_action，不调用模型、不产生 API 费用。`results` 从附带逐题元数据重新计算研究快照。源码分发名是 `wikiskill-research`，命令与 Python 包名是 `wikiskill`；请从本仓库安装。

## 真实实验

单独安装并登录 Codex CLI，按上游条款取得数据：

```bash
wikiskill init runs/officeqa-sol \
  --domain officeqa-retrieval --model gpt-5.6-sol \
  --optimizer-model gpt-5.6-sol \
  --csv data/officeqa/officeqa_full.csv \
  --corpus data/officeqa/corpus --iterations 4 --workers 4
wikiskill evolve runs/officeqa-sol
```

`evolve` 会调用模型；同一命令再次执行时复用已完成题目。manifest 固定模型、预算参数与提示；候选验证不完整或模型身份检查失败时不晋升。每次推理写入新的尝试目录，错误也保留。

## 定位与边界

- 框架层是任务无关的，新增任务需要数据 loader、执行器、评分器与领域提示；“能打分”本身不保证技能会改善。
- 当前随包提供 Codex 后端；默认便携执行路径尚不是研究环境中的加固隔离后端，不能把它当作确认性隔离保证。本次加入了严格JSONL读取与AST审计工具，完整研究runner仍单独维护。OpenClaw/ArXivMath 是独立的在研实验，未混入本快照或冒充已支持的后端。
- 全库检索与预配文档分开报告；前者不同于原论文提供 oracle 参考页的设置。
- 当前没有宣称 Wiki 独立因果贡献、普遍正迁移、跨独立演化稳定性，或所有未见任务均不退步。
- LiveMath 上游固定选项捷径、ALFWorld val 天花板、长度限制修订及基础设施恢复均记录在限制说明中。

框架采用 MIT；保留源自 BriefLoop 的版权信息。OfficeQA 评分器保留 Databricks Apache-2.0 许可证；数据遵守各上游条款。本仓库不是论文作者官方实现。

## 引用原论文

使用 WikiSkill 方法时，请引用原论文：

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
