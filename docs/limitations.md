# Method and measurement limitations

- **Validation selection:** the retained score is selected on reused val tasks. It is not an independent estimate of future performance. One task's percentage-point step is score resolution, not a noise band or confidence interval.
- **Per-task regressions:** a net improvement can include newly wrong answers. Strictly increasing `r_best` is an algorithm property, not a safety or non-regression proof.
- **Evidence modes:** OfficeQA staged documents and full-corpus retrieval are separate settings. Neither should be presented as identical to the paper's oracle-reference-page protocol.
- **LiveMath shortcut:** the upstream `option_sub()` replaces a correct option with a recognizable fixed meta-option. The source local val split contains affected items; an independent OpenClaw experiment learned the rule. The local accepted skills were audited separately. Do not equate a benchmark-score increase with better mathematical reasoning. See [upstream generator](https://github.com/LinyangHe/LiveMathematicianBench/blob/main/pipeline/scripts/generate_qa_az.py) and [prior public issue](https://github.com/microsoft/SkillOpt/issues/192). This is not a first-discovery claim.
- **ALFWorld ceiling:** Sol/5.5 reached 18/18 on the sampled valid_seen validation tasks. This does not establish perfect performance on valid_unseen or all embodied tasks.
- **Skill-length history:** source non-audit experiments initially used 80-line/60-diff limits, then moved to 200/150. Failed attempts and a partially evaluated abandoned Spreadsheet candidate remain historical deviations; no cap-causal claim is made.
- **Recovery history:** the source logs include missing dependencies, usage limits and scoring exceptions. Cleared aggregates do not mean incidents never occurred. Historic gate metadata include superseded/invalid attempts; do not count all log entries as independent experiments.
- **Model identity:** some older Terra records lack echoed model metadata. Missing identity evidence is not fabricated during export.
- **Generality:** score availability is necessary but insufficient. The task must have meaningful feedback, enough variation, repeatable execution and a valid holdout. Low-level control failures or exploitable answer conventions can dominate the result.
- **Transfer and ablation:** no broad positive-transfer, unique-first-implementation, or independent-Wiki causal claim follows from this snapshot. Separate studies are ongoing and will report their own settings and outcomes.
- **Runtime portability:** this extracted package is offline-validated. Historical paid model runs came from the source harness; library extraction and lifecycle changes have not been validated by rerunning that whole matrix.

Negative and inconclusive findings belong in future result releases. New datasets, scorer repairs and test protocol changes require explicit new versions, not rewritten history.
