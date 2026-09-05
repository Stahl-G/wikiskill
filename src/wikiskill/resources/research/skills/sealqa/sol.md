# Reconstruct the Cited Record Before Answering

Answer one factual question from the URLs packaged with the item. Your final response must be exactly `<answer>VALUE</answer>`, with no explanation inside or outside the tags.

## 1. Convert the question into a record request

Before researching, write a silent extraction card:

- answer type: name, title, integer, date, age, place, or quantity;
- subject and requested relation;
- every qualifier, including gender, status, geography, threshold, rank, edition, and negation;
- operation: lookup, filter, intersection, difference, count, ranking, or date calculation;
- time frame implied by the question and cited source.

A candidate is invalid if it violates even one card field. Familiarity or prominence cannot override the wording.

## 2. Treat `web_search.sh` as an index, not a search engine

Run `./web_search.sh` once and inspect every returned URL. Changing its query does not provide new evidence when the URLs remain unchanged.

Open the packaged pages themselves. If ordinary retrieval fails, try another representation of the same source: page-local search, printable or mobile view, raw source, MediaWiki API/raw revision, or an official table/download endpoint. Do not replace an inaccessible packaged record with an uncited remembered fact.

## 3. Reconstruct the answer-bearing record

Identify the exact passage, infobox field, table row, column, or finite list that answers the extraction card. In silent notes, record:

`URL | section/table | row or items | relevant fields | derived value`

Do not accept a reasoning note such as “confirmed” unless the underlying record has actually been inspected.

For counts, list every included item before counting and separately list borderline exclusions. For intersections, form both sets and count their normalized intersection. For rankings or thresholds, inspect the ordered boundary rows. For negated questions, explicitly compute the complement rather than counting the named property.

## 4. Freeze the source-time meaning

Words such as `current`, `latest`, and `this year` refer to the evidence state that produced the question, not automatically to the execution date. Separate publication date, event date, season/year, page-update date, and today.

Use explicit years and dated clues in the question first. On changing pages, inspect revision history or dated records to find the source state consistent with those clues. Do not calculate a present-day age, membership, activity status, ranking, or latest event unless the question and evidence explicitly anchor it to today.

## 5. Require a proof certificate

Before answering, silently complete:

- `candidate = ...`
- `direct record = ...`
- `derivation = ...`
- `time anchor = ...`
- `all qualifiers satisfied = yes`
- `nearest rival rejected because = ...`

If any field is missing, continue retrieving or reconstructing the packaged source. A search snippet, page title, generic knowledge, or unsupported inference cannot fill a missing field.

Finally emit only the requested value in the required tags. Preserve the source’s spelling and use a plain integer for count questions unless the question requests another form.