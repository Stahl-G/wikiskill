# September 7 final research record

The corrected Spreadsheet study observed **213/278 → 237/278 (+8.63 percentage points)** when Luna/high received one frozen skill. The paired exact test remains below 0.001 after a four-domain Bonferroni correction. This is evidence of a benefit for that skill under the recorded task and scoring conditions. Researchers had seen earlier results from the same test split, so this is a **fixed-split rerun**, not a completely unseen confirmatory test.

SealQA's original frozen skill produced an inconclusive **41/85 → 44/85** difference. A separate repeated mathematics validation screen found mixed skill effects on 18 reused task IDs. Neither result should be merged with the corrected Spreadsheet run as evidence of general improvement across domains.

These observations were imported from the originating research harness. The portable CLI in this repository did not generate them and is not the complete isolated research harness. The record closes these reported observations; it is not a claim that every planned experiment has been completed or that the original paper has been fully reproduced.

## Corrected Spreadsheet: one frozen skill, 278 fresh pairs

The `feedback-v3` candidate was selected on validation, from **28/40 to 32/40**, and frozen before these fresh paired test executions. Both no-skill and skill arms use Luna/high. The 278 task IDs belong to the existing local test split; “fresh” describes the executions, not previously unseen tasks or researcher-blind development.

| Measure | No skill | Frozen skill |
|---|---:|---:|
| Correct tasks | 213/278 | 237/278 |
| Accuracy | 76.6187% | 85.2518% |
| Mean recorded attempt seconds | 94.1057 | 121.0540 |
| Cumulative recorded tool calls | 1,287 | 1,766 |

The net difference is **24 tasks, +8.6331 pp**. Paired outcomes are **31 wins, 7 losses, 206 both correct, and 34 both wrong**. The two-sided exact McNemar p-value is **0.00011616700794547796**; multiplying by four for the four-domain Bonferroni correction gives **0.00046466803178191185**. The paired percentile bootstrap 95% interval is **[+4.6763, +12.9496] pp**, using 10,000 resamples and seed `2026090715`.

The frozen skill SHA256 is:

```text
7876c7ecb4b2aad0e55d7623335bd3781512247a1723815c2deec0036e1cc0bf
```

[Read the frozen Spreadsheet skill](../src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md). This is the experimental artifact, published for inspection; it is not automatically installed or enabled by the package. Its observed score does not establish that it is suitable for every business workbook.

The corrected research condition supplies the legal target-region and instruction-type metadata to both arms and supports isolated bash, Python/openpyxl, and formula recalculation. The scorer compares **cached values in the designated target cells**. A correct target-cell score does not prove preserved whole-workbook formatting, correct dynamic formula behavior after subsequent edits, or correct content outside the target region. The measured outcome should be described at that scope.

Four transport failures were each retried once, with the original failed attempts retained in the source archive. The reported mean latency and cumulative tool calls cover the sealed completed attempts and do not include the full overhead of all failed attempts. The observed mean-time increase is **28.636%**; it is not a complete end-to-end cost estimate. No monetary cost comparison is established by these figures.

This result supports a within-setting comparison of no skill with this selected frozen skill. It does not isolate the Wiki's causal contribution, compare the Wiki against matched alternative optimizers, demonstrate that each evolution succeeds, or establish performance across independent evolutionary seeds. The larger difference than the earlier Spreadsheet study cannot identify the causal effect of an individual alignment repair because the protocol and frozen skill both changed.

## SealQA: original frozen skill, 85 pairs

The completed paired observation uses the original frozen skill with SHA256:

```text
bcbfd2bb685f0127d2ec3372e6dcf4fa5037b1ba7b6f1963bdc83990350dfffc
```

This is **not the later candidate with a 7/10 validation score**. A new candidate's validation result must not be attributed to a test of another skill.

| Measure | Result |
|---|---:|
| No skill → frozen skill | 41/85 → 44/85 |
| Accuracy | 48.2353% → 51.7647% |
| Difference | +3.5294 pp |
| Wins / losses | 10 / 7 |
| Both correct / both wrong | 34 / 34 |
| Two-sided exact McNemar p | 0.629058837890625 |
| Four-domain Bonferroni p | 1.0 |
| Paired bootstrap 95% interval | [−5.8824, +12.9412] pp |

The interval uses 10,000 paired percentile bootstrap resamples and seed `2026090606`. The result is **inconclusive**: the data are compatible with either a negative or a positive effect in this setting.

Two disclosed amendments matter to interpretation:

- One skill-arm timeout was scored as zero under a user-authorized protocol amendment appended **after the timeout occurred, before the remaining test tasks completed**. This convention was not fixed prospectively and must remain visible alongside the paired statistics.
- In a separate episode, an actual `view_image` call treated an HTTPS URL as a local path. It returned `ENOENT` and supplied no data. An audit amendment limited to that observed evidence recovered the original model completion without resampling. A failed data read is distinct from successful access; the amendment does not authorize other tool activity or retrospectively make the entire protocol unchanged.

The source records retain the failures, original completion, and amendments. The public export supplies score-level outcomes and provenance, not complete private trajectories. Earlier tool-setting limitations also remain: this SealQA extension uses OpenAI live search over a fixed union of public source domains, rather than the paper's Google Search API, and does not provide per-item source URL lists.

## Mathematics: repeated validation, not independent test confirmation

This separate exploratory screen uses **18 validation task IDs, four arms, and two repetitions**, for **144 fresh model calls**. Every execution arm uses **Luna/high**, and the recorded executions contain **zero tool calls**. The arms are no skill, the old Luna-authored skill, the new Luna-authored skill, and one Astra-authored skill delivered to Luna.

| Repetition | No skill | Old Luna skill | New Luna skill | Astra-authored skill |
|---|---:|---:|---:|---:|
| 1, out of 18 | 11 | 13 | 12 | 10 |
| 2, out of 18 | 9 | 12 | 12 | 10 |
| Mean accuracy | 55.56% | 69.44% | 66.67% | 55.56% |
| Mean difference from no skill | — | +13.89 pp | +11.11 pp | 0.00 pp |
| Task-cluster bootstrap 95% interval for difference | — | [+2.78, +27.78] pp | [−2.78, +27.78] pp | [−11.11, +13.89] pp |

The bootstrap resamples task IDs as intact clusters, keeping both repetitions and all four arms together. **There are 18 task clusters, not 36 independent tasks.** The intervals are exploratory and have not been corrected for comparisons across multiple skill arms. In particular, the old skill's nominal interval excluding zero should not be presented as a multiplicity-adjusted confirmatory finding.

These same 18 tasks were used in validation development and selection. Fresh executions on them do not convert them into a new independent test set. Two repetitions do not establish stable effects across task populations or independent evolutions.

Astra authored **one** skill; Luna was the recipient and executor. This study does not compare Astra and Luna as executors and does not establish the superiority of one proposer model. The Astra-authored skill's zero mean difference is an observation about this skill in this small screen, not a general conclusion about Astra.

This zero-tool screen is distinct from the older LiveMath raw test with a disclosed no-tools violation. It does not erase or repair that historical violation.

## Earlier observations and unchanged limitations

The earlier [September 7 checkpoint](research-update-20260907.md) records OfficeQA V1 **98/172 → 104/172 (+3.49 pp, inconclusive)** and Spreadsheet under the former scoped-Python condition **221/278 → 227/278 (+2.16 pp, inconclusive)**. Those remain separate observations with their original frozen skills and setting limitations. The corrected Spreadsheet result above supplements them rather than overwriting them.

The earlier effort screen, Sol V1→V2 observation, and raw LiveMath test retain their original labels in the [September 6 record](research-update-20260906.md) and the September 7 checkpoint. Historical compromised OfficeQA retrieval observations remain compromised. A later positive result or audit repair does not retrospectively certify an older run.

Across this research program, production models, the Codex runtime and native base system, developer-level role injection, existing local splits, prior researcher exposure, and the number of independent evolutions remain differences from an exact reproduction of the paper. Sampling and contract alignment improve the correspondence of the implementation; their individual causal contributions have not been measured by ablation. No general positive-transfer, proposer-superiority, universal non-regression, or independent Wiki-causality claim follows from this record.

## Public evidence and offline verification

The [final evidence directory](../src/wikiskill/resources/research/final-20260907) contains:

| File | Purpose |
|---|---|
| [spreadsheet-pairs.json](../src/wikiskill/resources/research/final-20260907/spreadsheet-pairs.json) | Paired Spreadsheet score records |
| [sealqa-pairs.json](../src/wikiskill/resources/research/final-20260907/sealqa-pairs.json) | Paired SealQA score records |
| [math-episodes.json](../src/wikiskill/resources/research/final-20260907/math-episodes.json) | Mathematics arm and repetition score records |
| [spreadsheet-SKILL.md](../src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md) | Original frozen Spreadsheet skill bytes |
| [summary.json](../src/wikiskill/resources/research/final-20260907/summary.json) | Aggregate results, statistical settings, and validity notes |
| [manifest.json](../src/wikiskill/resources/research/final-20260907/manifest.json) | Export provenance and integrity hashes |

The export excludes task questions, gold answers, model answers, workbooks, private filesystem paths, and full trajectories. A frozen skill hash identifies the compared artifact; by itself it does not prove a run's isolation or protocol compliance.

From the repository root:

```bash
# Offline only: no model calls, credentials, or new experiments
python scripts/check_research_final_20260907.py
```

The checker verifies the public artifact hashes and recomputes the published paired scores and statistics from the exported records. Recomputing an imported result establishes numerical consistency of that public record. It does not constitute a new model run, an independent replication, or an audit of private runtime evidence.

The portable adapter has balanced success/failure sampling, modern tool summaries, and separately importable paper-alignment contracts. Its default CLI still uses legacy single-skill proposal transport. The full source research harness and these imported observations must not be presented as behavior already demonstrated by the portable CLI.

Proposed follow-up work is separated from completed observations in [next research and practical milestones](research-next-steps.md). Those directions have not been launched or measured.

Method attribution: [WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution](https://arxiv.org/abs/2608.27454), Liyan Tang, Cyrus Rashtchian, Chun-Sung Ferng, Andrew Tomkins, Da-Cheng Juan, and Tu Vu (2026). This repository is an independent implementation; the original authors retain credit for the method. See the [README citation](../README.md#cite-the-original-paper).
