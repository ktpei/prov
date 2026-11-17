# Model/effort comparison infrastructure protocol

2026-11-16 · frozen before implementation · baseline `404bdc1`

The user authorized model and effort comparisons. This infrastructure cycle makes
no paid requests and selects no heldout or new issuer content. The live task/cap
protocol remains unfrozen until capability/account reconciliation and checks pass.

Implement a small single-request OpenRouter comparison adapter using the existing
bounded, no-retry HTTP transport. This directly retains gateway usage/cost/provider
metadata without adding a framework. It is tool-free and does not implement
continuing reasoning/tool conversations. Legacy LangChain and H1 behavior stay
unchanged. This replaces the proposal to first extend the full-agent adapter;
it is a shared comparison transport for every initial arm, not a historical-run
replication. Later full-agent comparisons need separate adapter acceptance.

Every arm binds exact model, provider endpoint tag/name, accepted response model
IDs, explicit effort, optional temperature, common output ceiling, capability
snapshot/hash, and conservative per-token reservation rates. Validate effort and
parameters against pinned capability metadata; temperature omission is explicit.
Request only the pinned provider, disable fallback, require parameter support,
and set gateway max-price constraints. No tools or provider-default effort.

Construct and retain the exact nonsecret JSON request and its hash before dispatch.
Keep endpoint, instructions, task input and policy identities. Caller mutation must
not change the dispatched request after receipt creation. Credentials are passed
only in the Authorization header, never in receipts or error text.

Use the existing Budget reservation control with the request UTF-8 byte bound plus
8,192 protocol allowance and full output ceiling. Reject oversized or unaffordable
requests before dispatch. Retain reservations on unknown billing/network failure,
including process interruption. Settle a valid provider-reported usage.cost once;
reasoning tokens are a subset of output tokens, never another charge. Preserve
the full usage object, counts including cache/reasoning breakdowns, request ID,
actual model/provider and finish reason. Rate-derived estimate remains separate.

Invalid/missing cost is unknown billing, not zero. Preserve known billed failures
and truncated/empty outputs. A provider/model mismatch or malformed accounting
stops comparison dispatch even if financial charge is known. Do not trust routing
intent as confirmation of the actual provider. No automatic retries or fallback.

Required offline checks: exact effort/temperature/routing payload; capability and
request mutation; unsupported settings before dispatch; receipt identity; reasoning
not double-billed; cache cost capture; truncation with known cost; missing cost,
malformed usage, route drift, interrupts and preflight limits; sanitized errors.
Independent read-only review plus `yarn lint`, `yarn test` and clean-code checks.

An aggregate comparison runner remains required before live experiments: one
durable inventory for all task×arm attempts, interleaving, common inputs, complete
denominators, pending reservations, stop-on-uncertainty, per-arm/attempt/global caps,
and no automatic resume/retry. Record adapter acceptance separately from runner
and live comparison acceptance. No accuracy claim follows from mocked tests.

Primary documentation checked before implementation:
[OpenAI Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[OpenRouter reasoning](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
[usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting),
[routing](https://openrouter.ai/docs/guides/routing/provider-selection).
Reverify actual endpoint metadata/rates and account usage before freezing paid work.
