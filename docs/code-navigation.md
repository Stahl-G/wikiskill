# Code navigation

Start from the user action being changed:

| Change | Owner |
|---|---|
| Agent setup, task preparation, following the improvement loop | `skills/wikiskill/SKILL.md`, `references/workflow.md` |
| CLI arguments and command routing | `cli.py`, `product_cli.py` |
| Product work requests, journal, Wiki submissions, proposals and recovery | `product.py` |
| Product readiness, readable status and journal-derived reports | `product_views.py` |
| Explicit local skill installation and undo | `product_install.py` |
| External command authorization | `scorer_trust.py` |
| Finite numeric scores and strict improvement | `score_rules.py` |
| Legacy research evolution and experiment manifests | `engine.py` |
| Dataset parsing, task execution, domain scoring | Domain directories such as `officeqa/`, `spreadsheet/` |
| Paper prompt resources and contracts | `paper_alignment/` |

Product execution is performed by the calling agent. The research engine invokes its documented executor. These entrypoints retain distinct journals and protocols. Shared pure score rules do not make their experimental conditions equivalent.

## Rule review for the product usability update

- Both paths now reject missing/non-finite numeric scores. The research mean previously converted missing scores to zero; that behavior is corrected for future execution, without rewriting historical records.
- Both use the shared strict-improvement rule. Research keeps maximize/zero margin; product retains its declared direction and margin.
- New product task sets bind input file contents; changed inputs block dispatch/recording but not status/reporting. Older journals are not migrated.
- Product scoring failures preserve outputs for explicit retry. A changed checker after successful scores requires a new comparison; approving a command does not authorize mixing grading conditions.
- Research and product retain their existing storage and recovery mechanisms. No frozen snapshot or old workspace schema was migrated.
- Wiki topic labels and proposal input filenames in the product path are already unrestricted: labels become safe generated filenames, and the submitted skill is copied as SKILL.md. No new naming filter was added.

Add checks around observable boundaries, not exact generated wording. Do not consolidate the two engines solely to shorten the file list.
