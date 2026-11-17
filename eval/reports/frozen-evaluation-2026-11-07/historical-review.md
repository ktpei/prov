# Independent coding-agent audit of the four targeted cloud reruns

Read-only review performed before this evaluation's fresh inference. This is a
separate coding agent's textual evidence audit, not independent human financial
review, a new model trial, or a prespecified strict historical success score.
The original reports remain unchanged. All 28 historical mechanical pass/fail
flags reproduce under offline trace replay; see `historical-regrade.json`.

| Task | Core response | Additional defects found |
| --- | --- | --- |
| packet-04 | Correctly attributes slower large-customer expansion, pool-of-funds effects, and price-increase anniversary to management, with consistently low churn. Transcript L210-L215 and L70-L74 support it. | Optional structured claim treats **nearly 10%** of new ACV as exactly 10%. Removing the qualifier overstates precision. |
| packet-06 | Correctly distinguishes 77.7% GAAP from 78.8% non-GAAP; call L53-L54 gives the accounting basis and release L51/L239-L240 corroborates the margins. | Release unit header L225 and period/column headers L227-L228 are absent from **all recorded reads and search snippets**, not just citations. Precise addback scale/column attribution therefore lacks retrieved header context. The mechanical failure also contains a formatting false negative: `77.7 | %` does not match `77.7%`. |
| packet-08 | Correct packet-scoped abstention for actual FY2025 revenue, with no structured claims. | Narrative adds uncited, unstructured FY2024 guidance numbers. They are factually supported by its release L62-L63 read, but violate the number-to-claim/citation contract. The claim that these are the **only** forward-looking revenue figures is not established by its bounded search. |
| packet-09 | Correctly dates the deck May 30, 2024 and explains why it cannot establish actual Q3 2024 results; cites deck L1-L3 and release L43-L47. | “Actuals were **only** reported” overstates what the release proves. A supplementary deck-as-of assertion omits “Except as otherwise set forth in this presentation” from deck L7. “Anything in it about Q3” needs the Q3 **2024 financial results** scope. |

Historical measures remain **4/4 completed**, **3/4 mechanical passes**, and
**4/4 supported core responses under coding-agent review**. The last figure
cannot be relabeled strict task accuracy: every response has an additional
claim, qualification, or evidence-context defect under the stricter review.
No historical strict rubric was registered before these outputs were observed.
Combining selected successes from different iterations would create a post hoc
development view, not a fresh nine-task evaluation or heldout result.

Evidence: frozen transcript, release, and investor-deck extracted text under
`data/cloudflare-2024-q3`; original answers/traces under
`eval/reports/live/finalization`. Chart semantics and original PDF table geometry
were not independently validated by this textual audit.
