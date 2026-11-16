# Stage 1 reviewer instructions

Interpret only the literal questions in your assigned questions.json. Do not answer
them, calculate values or use remembered benchmark reference answers. Do not browse,
search the repository or read any other artifacts. Do not inspect another review.
Disclose any recognition/prior knowledge; do not claim that masking removes it.

For every case produce a JSON object with:
- `case_id`: exact neutral ID.
- `literal_request`: concise description of what the question asks.
- `output_contract`: requested type, precision and units when specified.
- `interpretations`: one or more objects, each with `id`, `description`,
  `required_facts` (list of distinct facts/context/relationships needed),
  `assumptions` (explicit, not silently adopted), and `ambiguities`.
- `well_defined`: `yes`, `conditional` or `no`, with `reason`.
- `recognition_or_prior_knowledge`: disclosure, including `none recalled` if applicable.

At the top level return `stage: "interpretation"`, your `reviewer` ID,
`questions_sha256`, `cases`, and `outside_access` (an empty list if none).

Distinguish facts necessary to answer from preferred reporting style. Preserve
material uncertainty: do not invent a threshold, definition, financial convention,
period alignment or currency assumption that the question does not establish.
Multiple plausible interpretations should remain separate. Do not alter required
facts to fit evidence: no evidence is supplied at this stage.
