# Treasury Bulletin source-and-calculation discipline

- Inventory the corpus with a broad glob, then resolve concrete filenames before reading them. Treat wildcard paths as discovery patterns, not as readable filenames.
- Search the concrete file with the table title, row label, abbreviations, synonyms, and date forms. If a search fails, broaden retrieval; never infer from a nearby table, issue, or historical knowledge.
- Read surrounding lines until the table heading, column headers, units, date basis, and footnotes are visible. A matching line is not evidence unless it contains the requested series and observation.
- Build a source map for every operand: bulletin issue, table identifier, row or category, column, observation date, calendar versus fiscal basis, units, sign convention, and revision vintage.
- Treat each subquestion independently. Do not substitute a total for a filtered category, an endpoint difference for an aggregate share, or a nearby date for the requested date.
- For quarterly or repeated tables, use the requested reporting issue. Compare adjacent or later issues only to identify revisions, and do not silently replace the requested vintage.
- Before calculating, write the requested statistic symbolically and preserve the operand order. State the denominator, weighting order, return definition, volatility convention, quantile, sign, and currency conversion when applicable.
- Distinguish rates from growth factors, logarithmic differences from percentage changes, pooled shares from differences of shares, and population from sample standard deviation. Apply chronological weights in the specified order.
- Track units through every operation; perform currency or million/billion conversions explicitly and round only after the specified final operation.
- Run a small hand-check or bounds/sign check against the extracted rows. If the source slice or formula remains unresolved, continue retrieval and verification rather than answering with a plausible-looking value.