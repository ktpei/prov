# Frozen comparison: exact ranked-parent reads

Run the original-question, DPO-component and statement-context saved reports on
the same three exposed FinanceBench cases and unchanged corpus. Use the existing
posthoc packets in `../evidence-components-2026-11-16/packets.json` unchanged.
No new annotation, query, source, model inference or default promotion is planned.

The read policy is `ranked-parent-once-v1`: one attempt for each selected parent,
at most five per task, exact bounds, ordered slots, no replacement/continuation.
Read execution receives only the replay-verified source/range projection. Search
replay uses the existing reference-aware source diagnostic, so the overall runner
is not described as gold-free. References and packet annotations are never inputs
to the reading policy. Packet bytes are first opened by the separate grader only
after exact search/result/journal replay.

Freeze each saved report, projected plan, prepared files, corpus manifest/binding,
packet hash and runtime in a protocol before execution. Persist all case slots
before dispatch; preserve aborted/interrupted runs and ordinary read failures.
Use new output directories only. Read errors consume their rank slots; no manual
rerun or task replacement. A failed execution remains a failed attempt.

Compute top-1/3/5 prefixes from a single five-slot trace. Record actual returned
lines, truncation, calls, text characters, JSON bytes and overlap separately from
requested lines. Separate replay repeats deterministic offline tool calls solely
for verification; report original attempts and replay calls distinctly.

Grade read responses alone, separately from parent opportunity and the earlier
snippet results. Keep union versus single-response completeness and all three
cases. Preserve incomplete alternatives, failed slots and the Ulta fiscal-year
convention issue. Check that returned-read coverage never exceeds parent coverage,
that complete faithful reads reproduce parent opportunity, and that prefix union
coverage is nondecreasing. Preserve every outcome, including failures.

This is a development evidence-delivery diagnostic. It does not simulate the
agent's prompt/context projection, measure answer accuracy, establish semantic
sufficiency, validate the annotations or provide unseen generalization evidence.
No paid calls or holdout exposure. Research rationale and implementation review
are in design.md; later results must be recorded separately from this frozen plan.
