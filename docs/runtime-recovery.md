# Recover completed work without resampling answers

Two September 6 failures came from postprocessing, after the model had already
finished. They were not missing model answers, failed workbooks, or evidence of
answer-key access. The source experiments preserve both failed attempts and the
subsequent repair records.

## JSONL is separated by physical newline

Python's `str.splitlines()` recognizes Unicode separators such as U+2028 and
U+2029. Those characters may occur legally inside a JSON string. Splitting there
turns one valid record into apparently truncated fragments.

The new `wikiskill.jsonl` reader splits on physical LF and preserves string
content. Genuine malformed records raise an error identifying the source,
physical line and column. They are not silently skipped. The portable engine,
resume readers and relevant identity/trace readers now use physical record
boundaries.

## Audit the outer program, not words inside its arguments

A Spreadsheet episode called the permitted Python tool and used `eval()` on an
arithmetic formula in the supplied workbook. A broad regex searched the entire
JavaScript wrapper, including the embedded Python string, and misclassified it
as an outer JavaScript API violation.

`wikiskill.tool_audit` uses a vendored Acorn 8.15.0 parser. It walks the outer
JavaScript syntax tree; string literals, comments and Python payload text are
data. Real JavaScript inside template interpolation is still inspected. Named
forbidden APIs, computed dispatch and host-access hazards remain distinguishable
from calls rejected because the function is unavailable.

This utility needs Node.js when auditing Code Mode scripts. It parses model code
without evaluating it. It supplements runtime permission enforcement; it is not
a proof that arbitrary JavaScript is safe or a replacement for an OS sandbox.
Acorn's MIT license is included under `third_party/acorn/`.

## Recovery in the originating experiment runner

The versioned experimental recovery driver separates model execution from
postflight audit, output export and scoring:

1. Verify the original completion, session, event and final-output hashes.
2. Verify actual model, effort and the exact request binding.
3. Recover the existing answer or generated workbook.
4. Run corrected postprocessing and deterministic scoring.
5. Seal a result that explicitly records **zero new model calls for recovery**.

A compatibility manifest pins all previously sealed records to their original
protocols. Older raw files, erroneous audit findings and frozen snapshots are
retained. New revisions describe code changes while preserving model, effort,
questions, skills, scoring and the statistical plan.

The actual SealQA completion (`seal0-39`) and Spreadsheet completion (`53994`)
were both recovered this way. True missing completions, altered hashes, identity
changes or genuine unapproved data-access calls still require attention; the
repair does not create an unlimited model-retry loop or convert failures to zero.

The public package includes the reusable readers/audit utilities and regression
fixtures. Full isolated research-driver recovery is still implemented in the
originating experimental environment. Do not imply that the portable default
backend automatically supplies all those isolation and recovery guarantees.

## Checks

```bash
python -m pytest -q tests/test_runtime_records.py tests/test_engine.py
python scripts/check_research_update.py
```

The fixtures cover Unicode JSON strings, true truncation, embedded Python eval,
template interpolation, comments, constant tool aliases and actual forbidden
calls. No paid model experiment is needed for these checks.
