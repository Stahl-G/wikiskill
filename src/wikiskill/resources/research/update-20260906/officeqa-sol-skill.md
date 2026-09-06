# Reconstruct Treasury Tables Before Extracting Values

Treat a search match as a locator, not as a value source. Reconstruct the table’s structure before copying any number.

## Capture the whole table

Read from the table title through its headers, body, continuation sections, units, notes, and revision markers. Include the bulletin issue and the table’s stated as-of date; do not equate either one with an observation date unless the table says so.

Expand stacked or merged headers into one leaf label per numeric column. Combine every applicable level, such as fiscal year, month, measure, fund coverage, and preliminary or revised status.

Split side-by-side page panels into independent tables. Carry blank dates or labels downward only within their original panel. Preserve blank cells, dashes, and `nan` placeholders so later values do not shift left.

If extraction joins footnote markers and adjacent numbers, repeats a sequence, or produces a row with a different number of cells than the reconstructed header, stop using that row. Resolve it from a continuation, an overlapping bulletin, or another rendering of the same table.

## Prove the column alignment

Render at least one relevant row as explicit `full column label = value` pairs. Check that:

- annual totals are not being read as monthly observations or fiscal-year-to-date figures;
- calendar-year and fiscal-year columns are not interchanged;
- components, subtotals, and combined-funds totals retain their exact labels;
- issue date, as-of date, maturity date, and reporting period remain distinct;
- quoted units and scaling apply to the selected column.

Test an available table identity, such as total equaling its components, cumulative value matching its displayed periods, or the same observation agreeing in an overlapping release. Treat a failed identity as evidence of a shifted column, missing panel, or changed vintage—not as harmless rounding.

When overlapping releases disagree, inspect revision markers and notes. Use the issue named by the question; otherwise use one coherent stated vintage and never splice conflicting versions silently.

## Extract by labels

Translate every requested qualifier into a title, row, or full column label that must be present in the reconstructed table. Extract values by those labels rather than by visual position or the nearest year-looking number. Begin calculations only after every selected value survives the alignment checks.