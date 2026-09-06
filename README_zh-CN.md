# WikiSkill

**面向可评测 Agent 任务的技能自进化框架。**

> **研究更新（2026-09-06）：** 修正实验已有两项完整 held-out 观察，统计上均不确定；其中 LiveMath 的一条 test 使用了 JavaScript，违反无工具条件，只作为原始观察报告。历史 OfficeQA 检索增益仍属受污染记录。本次增加可复算配对分数和运行恢复修复，见[最新证据与限制](docs/research-update-20260906.md)。

基于 **[WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://huggingface.co/papers/2608.27454)**（Liyan Tang 等，2026）。本仓库是该论文方法的独立实现，原始方法贡献归属论文作者。

[Hugging Face 论文页](https://huggingface.co/papers/2608.27454) · [arXiv 原文](https://arxiv.org/abs/2608.27454)

WikiSkill 将执行经验整理为持久知识，再将知识转化为可复用的程序性指导：Agent 执行任务，Wiki Maintainer 整理模式，Skill Proposer 提出修改，确定性验证门控决定是否保留。技能被拒绝时，Wiki 中的经验继续保存。

本仓库是独立研究实现，当前提供 Codex runtime 与文档问答、表格操作、数学、检索、具身交互五类任务适配器。框架可扩展到具有可靠评分、可重复执行、独立训练/选择/测试数据的任务。

[English](README.md) · [完整结果](docs/results.md) · [复跑说明](docs/reproduction.md) · [数据准备](docs/datasets.md)

## 最新研究观察

快照时间：**2026-09-06 15:50 UTC**。这些实验使用原始研究环境中的隔离 runner，没有冒充由本包的便携 CLI 重跑。

| 研究 | 模型 / effort | Held-out 无技能 → 技能 | 变化 | 证据状态 |
|---|---|---:|---:|---|
| OfficeQA V1 → Pro V2，解析文本全库检索 | Sol / medium | 48/90 → 52/90 | **+4.44pp** | 运行时扩展实验；p=0.454，统计不确定 |
| LiveMath 清理后的子集 | Luna / high | 81/124 → 87/124 | **+4.84pp** | **仅原始观察：** 一条 test 通过 JavaScript 计算违反无工具协议；p=0.307 |

两项配对95%区间都跨0，**尚不能宣称统计上成立的干净正向复现**。LiveMath 的协议偏离不能靠事后删除一对题目消除；原始数据、协议与审计继续保留。

Luna/high 自演化在 OfficeQA（19/24→22/24）和 LiveMath（9/18→12/18）保留了验证集增益，但它们仍是验证选优结果。OfficeQA 新的172对test使用论文的 glob/grep/read 工具集，结果待完成。SealQA、Spreadsheet 扩展线在修复两处后处理问题后继续运行，已完成的模型答案没有重新采样。

[研究细节与配置差异](docs/research-update-20260906.md) · [可复算配对工件](src/wikiskill/resources/research/update-20260906) · [运行恢复设计](docs/runtime-recovery.md)

```bash
# 离线重算新配对观察并检查工件哈希，不调用模型
python scripts/check_research_update.py
```

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
