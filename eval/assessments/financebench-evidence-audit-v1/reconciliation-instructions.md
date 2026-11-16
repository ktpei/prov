# Stage 1 independent reconciliation instructions

Reconcile all six questions using only the literal question packet and the two
locked independent interpretation reviews. You have no source evidence, benchmark
reference, original rubric, retrieval outcome or policy attribution. Do not obtain
those items or answer the questions. Do not browse or use remembered reference
answers. Disclose recognition and any access outside your assigned inputs.

For each case:
1. Compare the two interpretations and separate substantive agreement, harmless
   wording differences and material differences in assumptions or required facts.
2. Produce one or more distinct, defensible interpretations. Consolidate true
   duplicates; retain materially different conventions or unresolved ambiguity.
   Do not force a single interpretation or prefer the one needing less evidence.
3. For each interpretation define the minimal necessary facts, context and
   relationships. Assign stable local interpretation IDs I01, I02, etc. and stable
   requirement IDs R01, R02, etc. Identify whether each requirement follows directly
   from wording, follows from a stated convention, or resolves an ambiguity through
   an explicit assumption. Preferred presentation style is not an evidence role.
4. Explain which reviewer proposals support or conflict with the reconciliation.
   Record rejected proposals and reasons. If a financial threshold or convention
   is unstated, keep it conditional instead of inventing one.
5. Classify whether the question itself is well-defined, independently of whether
   the unavailable documents actually contain the required information.

Output one JSON object with `stage: "interpretation_reconciliation"`,
`reviewer: "C"`, `input_sha256` mapping the three data input filenames to hashes,
`cases`, `outside_access`, and `recognition_or_prior_knowledge`.

Each case must contain `case_id`, `agreements`, `material_disagreements`,
`interpretations`, `rejected_or_merged_proposals`, `well_defined` (yes/conditional/no)
and `reason`. Each interpretation contains `id`, `description`, `assumptions`,
`unresolved_ambiguities`, `required_facts` (objects with `id`, `description`,
`basis` and `rationale`), and `reviewer_provenance`.

Preserve all six cases in question-packet order. This reconciliation is a coding-agent
judgment, not human financial validation. It is frozen before evidence is supplied;
any later change must be recorded as a rubric revision, not silently folded into
an equivalent-location addition.
