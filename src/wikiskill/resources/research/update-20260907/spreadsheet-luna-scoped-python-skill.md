# SpreadsheetBench Workbook Editing with Concrete Values

## Contract

- Use the scoped documents tools and Python/openpyxl; locate `input.xlsx` and save the finished workbook as `output.xlsx`.
- Write concrete Python values into every requested answer cell. Never place a formula string or formula object in the answer region.
- Load with `data_only=False` when saving so unrelated formulas remain intact. Formula cells outside the answer region are not to be replaced by cached values.

## Inspect before editing

1. Find the input workbook with the documents file tool.
2. Load with `data_only=False`; record exact sheet names, dimensions, merged ranges, hidden sheets, tables, and named ranges. Resolve sheet names literally, including spaces and punctuation.
3. Print relevant rows and columns, headers, existing formulas, data types, number formats, and styles. Use a second `data_only=True` load only to inspect cached results.
4. Determine the answer coordinates and complete boundaries from the request and workbook structure. Build an explicit target-coordinate list, including cells whose expected result is blank. Do not infer a smaller range from the first populated rows or a reference-looking sheet.
5. Separate output coverage from source eligibility. A source row with one missing field is not automatically a blank or invalid record; apply the task’s stated rule. In particular, do not discard open-ended interval rows merely because an endpoint is missing.

## Derive results deterministically

- Follow the stated row and column rules exactly, including repeated blocks and all required source sheets.
- Exclude headers and wholly blank records. Deduplicate only when requested, using the specified composite identity key; retain original row position for stable tie handling.
- Apply the requested ordering explicitly. Preserve helper-list order or source order when specified.
- If rows must be rearranged, snapshot complete row values and needed styles before writing; never sort or rewrite from live cell references that can overwrite later source rows.
- Normalize values only for comparisons, and only as requested. Preserve original values where no match or transformation is requested. Make case, whitespace, date, numeric, and exact-match semantics explicit.
- Do not silently choose the first or last duplicate lookup match unless the task specifies that rule. Resolve duplicate keys using the stated priority and stable source order.
- For missing or open-ended bounds, derive the intended unbounded, next-boundary, or sentinel behavior from the instructions, labels, neighboring ranges, and formula logic; do not invent an exclusion rule.
- Use formulas and neighboring formula patterns as read-only evidence of intended logic. Recompute the logic in Python and materialize its result as a number, date, boolean, string, `None`, or other concrete value.
- Treat `None`, empty text, numeric zero, `False`, dates, and sentinels such as `NA` or `M` as distinct. Apply the task’s blank/zero/sentinel policy exactly. Clean only text cells; do not stringify existing numeric or date cells.

## Write conservatively

- Change only the named answer range and any structural changes explicitly requested. Do not add, delete, or rename sheets; do not overwrite unrelated content.
- Assign `.value` only for answer cells unless the task explicitly requires row insertion, deletion, sorting, or formatting. Never write to a `MergedCell`.
- Preserve existing styles and number formats. If new rows are explicitly required, copy formatting from the appropriate neighboring/template row without copying formulas into the answer region.

## Verify after saving

Reopen `output.xlsx` with `data_only=False` and assert:

- the file opens and the sheet list and required structure are retained;
- every requested target coordinate is covered, including expected blanks, with the expected concrete value and type;
- no answer cell contains a formula string beginning with `=` or an `f`/`ArrayFormula` object;
- blanks, zeros, booleans, dates, sentinels, number formats, and rounding are correct;
- expected keys, row counts, ordering, source boundaries, and populated limits are complete; and
- no cell outside the explicitly permitted target/structural area changed, including formulas, array-formula metadata, styles, and number formats.

If a check fails, fix the workbook and save again before reporting completion.