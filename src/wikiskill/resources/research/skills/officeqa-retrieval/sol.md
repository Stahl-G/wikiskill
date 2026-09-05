# Treasury Bulletin Search and Reading Discipline

## Parse the request before searching

Write a private answer specification before opening a table:

- List every requested output in its required order.
- Name the measure, entity, period, and requested unit for each output.
- State whether the period is a calendar year, fiscal year, month, year-to-date interval, maturity year, or another convention.
- Translate each calculation into a formula before selecting numbers.
- Record the required precision and apply rounding only to the final result.

For a chained question, write the dependency explicitly. Finish identifying the first result before using its date, category, or value to retrieve the next result.

## Find the table by meaning

Search for distinctive phrases from the requested measure, likely table title, and row label. Treat a filename or bulletin date only as a lead.

Open enough surrounding lines to see:

- the full table title and number;
- every level of the column header;
- the row label and adjacent rows;
- the printed unit;
- continuation labels, footnotes, and revision markers.

Do not select a number merely because it appears near the requested words.

## Lock every source coordinate

Before transcribing a value, identify this complete coordinate:

- bulletin issue;
- table title or number;
- row label;
- column label;
- reporting period;
- printed unit.

Reject a candidate value if any coordinate is unresolved.

Take special care with flattened multi-level tables. Repeated month rows may belong to different year blocks, and repeated labels may sit under different parent headers. Recover the year and parent header from the surrounding table structure; do not infer them from column position alone.

Distinguish similarly named measures such as gross versus net, receipts versus expenditures, budget versus trust accounts, monthly versus cumulative, actual versus estimated, and total versus component.

When the same table appears in several bulletins, use one issue that directly and consistently reports the requested period. Use another issue only to check revisions or transcription; do not splice values from different revisions without a stated reason.

## Build and validate the input vector

Before copying a multi-observation series, declare its expected coordinate grid: start, end, frequency, category scope, and expected count. Expand the grid into explicit period or category labels.

Copy observations as label-value pairs, never as a bare numeric list. Preserve each printed row label, column label, sign, decimal point, and scale; do not relabel a source row to make it fit the requested range.

Before calculating, verify that every expected coordinate appears exactly once, every copied coordinate belongs to the requested grid, and the order matches the question. For monthly ranges, enumerate the exact month sequence across year boundaries. For schedules split across sections, reconcile the boundary and final count.

Re-open any small, zero, duplicated, discontinuous, or otherwise suspicious value in the raw table. Exclude continuation headers, subtotals, footnote markers, OCR fragments, and adjacent-column values rather than silently repairing them. A plausible aggregate or matching count does not prove complete coverage.

Interpret symbols and qualifiers from the table notes, including dashes, asterisks, preliminary or revised markers, estimates, and exclusions. Treat a row total as a diagnostic check, not as permission to shift a row or column to make the arithmetic fit.

Keep values in the table's printed unit during calculation. Convert units once, after the formula is evaluated, and verify the conversion direction. A value printed in millions becomes nominal dollars by multiplying by one million, not by changing the underlying table coordinate.

## Lock auxiliary inputs and transformation order

Give every auxiliary observation, such as CPI or an exchange rate, its own source coordinate. Record the exact series name and definition, adjustment status, frequency, reference period, date alignment, unit, and quote direction. Reject a similarly named series even when its values look plausible.

Write the transformation pipeline in execution order and label the unit after every step. Follow the question when choosing between deflating each dated level before aggregation and transforming an aggregate, or between an average of ratios and a ratio of averages. For exchange rates, state which currency is in the numerator before multiplying or dividing.

For convention-sensitive risk or statistical operations, record the return definition, tail, confidence level, quantile sign, dispersion convention, and whether the result is a signed outcome or loss magnitude. Finish with a dimensional check that independently reconstructs the requested output unit.

## Formalize the operation

For each requested output, record:

- the ordered observations used;
- any transformation applied;
- the exact formula;
- the number of observations and elapsed intervals;
- the population or sample convention when relevant;
- the output unit and rounding rule.

Distinguish percentage change from percentage-point difference, levels from changes, arithmetic change from logarithmic change, and standard deviation of levels from standard deviation of changes. For compound growth, derive the exponent from elapsed intervals rather than the number of observations. For baselines, z-scores, or forecasts, state whether the target observation is included.

## Verify with a fresh source pass

After computing a candidate result, start again from the question's entities and dates rather than from the copied numbers.

Re-open the table title, complete header, requested row, period labels, unit line, and applicable footnotes. Reconstruct the input vector independently and compare both the labels and values item by item with the calculation inputs.

Recomputing the same copied values is not verification. If the fresh pass exposes multiple plausible tables, series, year mappings, or revisions, resolve the ambiguity from the definitions and question wording before answering.

## Check the requested representation

Before returning the answer, confirm that every requested part is present and in order, units match the request, and rounding was applied exactly once. Do not replace a requested value with an intermediate date, category, subtotal, or converted representation.
