# DPO component retrieval — fixed development experiment

This is an exploratory improvement on three already-inspected development tasks,
not an unseen benchmark or generalization test. Visual review established that
Walmart's operands are present but its two required pages are missed by the
existing document-scoped top-five search. The implementation and protocol must
be committed before this challenger searches the real corpus. Preserve failures;
no query edits, retries or default promotion based on this run.

## Question-only policy

Only the full phrase “days payable outstanding” triggers expansion. Preserve the
original question exactly, then search four fixed families: accounts payable /
trade payables; purchases / credit purchases; cost of sales / cost of goods sold;
inventory / inventories. Append only distinct four-digit 19xx/20xx years found
in the question, in their original order. Other questions use one unchanged
search. Original and generated queries must fit the 500-character search limit;
reject the full plan before dispatch if any query exceeds it. The permitted document is declared model-input metadata, never gold.

Each search returns at most five candidates. Merge by round-robin per-query rank,
original query first, deduplicating exact source/start/end passages, then retain
five. Do not compare BM25 scores across queries. Keep complete individual search
responses in the challenger trace. Passage identity does not merge overlapping
windows; page coverage is evaluated separately. No additional source reads or
model calls occur.

This increases Walmart's search budget from one to five calls and the three-task
budget from three to seven. Report that resource difference explicitly; it is
not an isolated scoring-formula comparison. Keep the same selected documents,
extraction, BM25 implementation, original questions and fixed top-1/3/5 metrics.
Run the original-question document-scoped baseline once for exact comparison.

## Financial scope and risks

The planner supplies candidate terms, not a calculation or verified operand role.
[CFA Institute](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/programs/cfa/cfa_program_level_ii_financial_ratio_list.pdf)
uses average trade payables and purchases; [OpenStax](https://openstax.org/books/principles-finance/pages/19-1-what-is-working-capital)
uses a COGS turnover convention. [ACCA](https://www.accaglobal.com/africa/en/student/exam-support-resources/fundamentals-exams-study-resources/f7/technical-articles/appraisal-questions.html)
discusses credit purchases with cost-of-sales fallback. [CPA Australia](https://www.cpaaustralia.com.au/-/media/project/cpa/corporate/documents/become-a-cpa/cpa-program/faar-study-guide-eighth-edition.pdf?rev=bb5869fc0fd54e57b8dbb9bd7d8fd445)
illustrates inventory-adjusted purchases and closing-payables variants; these are
not universal interchangeable definitions.

The current Walmart question explicitly supplies its formula; it remains intact.
No formula is inferred for other questions. Component searches do not invent a
fiscal end date, scale, day-count convention or answer. Purchases can retrieve
capital expenditure; current liabilities and cash-flow working-capital changes
are not substitutes for stock balances. A page hit does not establish period,
unit, sign, header, snippet, complete-support or answer correctness.

## Fixed outputs

Keep all three tasks and all four annotated page keys in the denominator. Report
pooled and macro top-1/3/5 page coverage, whole-task page coverage, per-task paired
changes, query counts and underlying report hashes. Gold remains evaluator-only.
The frozen bundle predates the latest Ulta reference-review flag; do not rewrite
it. Report that known period-convention issue alongside results. Source evidence
concordance and all existing scores remain unchanged. The default graph and
retrieval policy stay unchanged regardless of this small development result.
