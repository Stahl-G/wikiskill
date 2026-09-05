# Spreadsheet Answer-Region Contract

## Objective
Produce `output.xlsx` by writing concrete, typed values into the intended answer region. Do not write formulas into answer cells. Treat answer correctness and workbook preservation as separate requirements.

## 1. Inspect before interpreting
- Open the input without mutating it. Inventory every sheet, used range, hidden row or column, merged range, table, defined name, formula, and styled blank area.
- Inspect raw values, displayed values, formulas, number formats, and Python types. Do not infer data boundaries from `max_row` or `max_column` alone because formatting and names can extend them.
- Locate the answer region from the instruction plus workbook evidence: labels, blank or highlighted cells, neighboring formulas, examples, and repeated layouts.
- Identify all source rows. Exclude titles, blank separators, subtotals, or repeated headers only when workbook evidence supports doing so.

## 2. Freeze an answer contract
Before editing, record a compact contract in scratch notes with:
- input file, target sheet, and exact target coordinates;
- source sheets, source ranges, and header rows;
- row eligibility and normalization rules;
- lookup or composite keys, duplicate policy, and stable ordering;
- inclusive or exclusive date, time, and numeric boundaries;
- blank, zero, text-marker, error, and unmatched-row behavior;
- expected output shape and every coordinate allowed to change.
Do not silently resolve conflicting instructions for convenience. Test each plausible reading against labels, examples, row integrity, and output shape. Select the reading consistent with the most workbook evidence, and never separate fields that form one record.

## 3. Derive expectations before writing
- Snapshot source data and non-target workbook state before mutation.
- Compute an expected value for every target coordinate with a pure read-only routine. Record `coordinate -> typed expected value -> supporting source rows`.
- Exercise adversarial rows explicitly: first and last eligible rows, exact endpoints, month and leap-day edges, duplicate keys, missing bounds, unmatched keys, repeated headers, text numbers, blanks, and the first complete rolling window.
- Reconcile expected row and column counts with the target shape. A plausible subset is not sufficient.

## 4. Make the smallest edit
- Copy the input to `output.xlsx`, then edit only the allowed coordinates.
- Write numbers, booleans, dates, and text using their proper types. Never write a formula string beginning with an equals sign into the answer region.
- Preserve existing styles and number formats in answer cells unless the task explicitly requests formatting changes.
- Clear stale values only inside the declared answer region when the expected result is blank.
- Do not add, delete, move, sort, hide, or resize rows, columns, sheets, or blocks unless the task explicitly requires that structural change.
- If structural change is required, first map affected formulas, merges, tables, validations, dimensions, hidden state, and styles. Preserve record order unless another order is explicit.

## 5. Verify with an independent oracle
Reopen `output.xlsx` from disk with formulas visible and run every check below:
1. Enumerate every target coordinate. Compare its value and type to the precomputed expectation and confirm that it contains no formula.
2. Recompute results through a second implementation that does not call the writer's transformation helper. Examples include a brute-force scan versus a lookup map, direct group totals versus a deduplication loop, or explicit window slices versus rolling state.
3. Confirm target dimensions, populated-cell count, and required blanks or markers exactly.
4. Compare input and output semantically outside the allowed change set: cell values, formulas, styles, merges, row and column dimensions, hidden state, tables, validations, defined names, sheet order, and calculation settings.
5. For authorized structural edits, compare against the mapped post-change contract and inspect every shifted dependency.
File existence, successful reopening, visual similarity, and an error-string scan are diagnostics, not proof that the requested values are correct.

## 6. Fail closed and deliver
- On any mismatch, stop, diagnose the contract or transformation, regenerate from the untouched input, and rerun all checks.
- Do not broaden the edit to make verification pass, and do not claim completion while target mismatches remain unresolved.
- Deliver exactly one final workbook named `output.xlsx` only after every target and preservation check passes.