# Research update — 2026-09-06

Snapshot exported at **15:50 UTC**. The paired scores, skill bytes and hashes are
in `src/wikiskill/resources/research/update-20260906/`. All previously published
snapshots remain unchanged. Questions, gold answers, model answers, workbooks
and complete trajectories are not distributed.

## Completed observations

| Study | S0 | Frozen skill | Delta | Exact McNemar p | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|---:|
| Sol/medium, OfficeQA V1 → Pro V2 | 48/90 (53.33%) | 52/90 (57.78%) | +4.44pp | 0.4545 | [−4.44, +13.33]pp |
| Luna/high, LiveMath cleaned subset — **raw only** | 81/124 (65.32%) | 87/124 (70.16%) | +4.84pp | 0.3075 | [−2.42, +12.90]pp |

These are not statistically established positive results. The Sol study is a
single-run parsed-text, full-corpus runtime extension with prior researcher
exposure; its local document-plus-Python interface differs from the original
OfficeQA tool list.

The LiveMath study has an additional **no-tools protocol deviation**. In test
episode `202606-102/sk`, Code Mode executed JavaScript polynomial calculations:
two invocations returned complete numeric outputs, one returned partial numeric
output before an error, and one failed at console output. No external file or
answer-key read was found in those calls. Nevertheless, actual computation
violates the declared direct-reasoning condition, so the run is not a clean
no-tools confirmation.

That task is correct in both arms. A post-hoc exclusion gives 80/123 vs 86/123,
still six net wins; this shows the single task did not directly create the net
six-task margin. It does **not** restore preregistered validity or justify replacing
the original table. The original 124 pairs remain the published raw observations.

Paired outcomes are Sol: wins 10, losses 6, both correct 42, both wrong 32;
Luna/LiveMath: wins 15, losses 9, both correct 72, both wrong 28. The original
two-domain correction for Luna gives p=0.6149; a supplemental four-domain
correction gives p=1. Neither changes the interpretation.

## Development and active studies

Luna/high self-evolution starts with an empty Wiki and skill; executor,
Maintainer and Proposer all use Luna/high.

| Domain | Development observation | Status at export |
|---|---|---|
| OfficeQA V1 retrieval | 19/24 → 22/24 selected val | User ended development after two full iterations; 20 unused it3 train records retained. Frozen it1 skill is in a 172-pair test. |
| LiveMath cleaned subset | 9/18 → 12/18 selected val | K=4 completed; held-out raw observation above has the disclosed tool deviation. |
| SealQA extension | Fresh S0 val 6/10 | it1 validation after recovery; test result pending. |
| Spreadsheet extension | Fresh S0 val 31/40 | it1 training after recovery; test result pending. |

The development values are adaptively selected validation observations, not
independent evidence of generalization. They do not establish that a Wiki has
an independent causal advantage over other optimization procedures.

## Original paper tools and implementation differences

WikiSkill Appendix B / Table 6 specifies OfficeQA `glob/grep/read`, LiveMath no
external tools, SealQA Google Search API plus file reading, and Spreadsheet bash.
The new OfficeQA test uses direct `glob/grep/read` calls with the JavaScript host
disabled. Its frozen skill was developed with an extra Python tool, so its result
must be described as transfer into the paper tool condition. Full-corpus retrieval
without oracle initial pages remains a deliberate input extension.

The current SealQA run uses OpenAI live search within a fixed union of public
source domains, not the paper's Google backend. It does not receive its per-item
source URL list. The Spreadsheet run uses scoped Python/openpyxl with concrete
values, not the full paper bash/formula environment; 398 usable local tasks remain
after two documented malformed items are excluded. These deviations stay visible
and must not be relabeled as an exact tool-matched paper reproduction.

## Reliability repair

Two completed model calls were stopped by postprocessing bugs: Unicode JSONL
record splitting and a regex false positive on Python formula evaluation.
Both original outputs were recovered without querying the model again. New
versioned code, request/completion checks and immutable compatibility manifests
preserve prior records. See [runtime recovery](runtime-recovery.md).

A tool catalog remaining visible is different from a successful file read. The
earlier audit therefore distinguishes failed shell API attempts, tool discovery,
preflight residue reads, actual calculation and successful external access. The
LiveMath calculation deviation remains disclosed after the reliability fixes.

The historical September 5 OfficeQA retrieval gains remain compromised by
confirmed cross-run/answer access. None of the new observations retrospectively
certifies those historical runs.

## Recompute

```bash
python scripts/check_research_update.py
```

The checker verifies the new artifact hashes and recomputes paired counts,
differences, exact McNemar and seeded bootstrap intervals. A successful software
recomputation verifies the published numbers; it does not erase runtime validity
limitations or constitute an independent model rerun.
