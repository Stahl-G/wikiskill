---
name: recalculate_and_validate_formula_workbooks
description: Use when editing formulas in an XLSX and the delivered workbook must contain correct cached results, not merely formula strings.
---

## When to Apply

Apply this workflow whenever the task inserts, replaces, or fills formulas, especially when the evaluator may read cached values with `data_only=True`, the workbook uses dynamic arrays or structured references, or the requested result depends on displayed text, locale, or numeric type.

## When NOT to Apply

Do not add a recalculation cycle for purely literal edits or formatting-only tasks with no formula-dependent target cells. Still preserve the original workbook structure and validate the exact requested range.

## Instructions

1. Inspect the source workbook, target range, neighboring formulas, and the final requirement. Determine whether each target must be a number, text, blank, Boolean, or error label. Derive criteria from the final requirement and target layout; do not inherit contextual filters that the requested result does not require.

2. Prefer formulas that the available recalculator supports. If a dynamic-array formula or structured reference produces a blank/error cache, replace it with a compatible classic formula, helper-cell approach, or static result only when the task does not require a formula. Do not treat `fullCalcOnLoad` flags as proof that values were calculated.

3. Avoid locale-dependent output when the requested text is fixed. For example, use an explicit mapping such as `CHOOSE(WEEKDAY(date,2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun")` for English weekday labels instead of relying on localized `TEXT` output. If the requested result is text, concatenate it explicitly; a number format suffix does not change a numeric cell into text.

4. Save the edited workbook, enable automatic/full calculation, and recalculate it with the permitted headless spreadsheet engine into a workspace-local temporary directory and isolated user profile. Require the converted file to exist, then copy or move that converted file over the exact final output path. Never deliver the pre-recalculation workbook while inspecting only a temporary copy.

5. Reopen that exact final output twice: once with formulas visible (`data_only=False`) and once with cached results (`data_only=True`). For every requested target cell, verify that the formula is present when required, the cached result is nonblank when a result is expected, no unexpected error remains, and the value has the required semantic type and text. Check representative edge cases such as missing matches, blanks, duplicate keys, negative values, and boundary conditions.

6. If cached results are missing or differ semantically after recalculation, diagnose the formula or compatibility/locale issue and revise it before reporting completion. Inspect floating-point mismatches separately from business-value errors; use consistent coercion and apply `ROUND` only when the task specifies a precision.

7. Report the exact final output path only after the final-path formula and cached-value checks pass.