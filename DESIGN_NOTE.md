# Design Note

## 1. Failure Modes

Three realistic failure modes for this system in production:

**LLM API unavailability or rate-limiting** — during development, we encountered this directly: a model became deprecated overnight, and free-tier rate limits caused request failures. In production, this is detected via HTTP error codes (429, 503, 404) and mitigated with automatic retry logic (implemented in this project) plus a fallback to a secondary model/provider if the primary fails repeatedly.

**Malformed JSON output** — LLMs occasionally produce output that doesn't parse as valid JSON, especially with longer or more complex prompts. This is detected via JSON parsing exceptions and mitigated with automatic retries plus a safe fallback structure, so the system degrades gracefully instead of crashing (implemented in the triage agent).

**Hallucinated or overconfident classifications** — since urgency/category decisions directly affect customer response times, an incorrect P1 classification could cause under-response to a real emergency, while false alarms waste engineering time. This is harder to detect automatically; mitigation would involve human-in-the-loop review for P1 classifications specifically, plus continuous evaluation against a growing set of human-labeled tickets over time.

## 2. Latency vs. Quality Trade-off

We used a single LLM call per ticket rather than a multi-step reasoning chain (classify, then separately verify against the knowledge base, then separately draft a response). A multi-step approach would likely improve accuracy for ambiguous tickets, but roughly triples latency and API cost per ticket. We chose the single-call approach because ticket triage needs to feel near-instant to support agents, and testing showed single-call accuracy was already strong (rule-based checks passed 100% of test cases, with LLM-judge quality scores averaging 0.9/1.0). If latency were a hard constraint, we would use a smaller/faster model for initial triage and reserve larger models only for ambiguous or high-stakes (P1) cases.

## 3. Data Sensitivity

Ticket and account data in this assessment is synthetic mock data, so no real PII was at risk. However, in a real production deployment, ticket bodies and account notes would likely contain real customer names, emails, and business details — sending this directly to a third-party LLM API (as this project does) means that data leaves our infrastructure and is subject to the provider's data handling policies.

To handle this safely in production, we would: (1) redact or mask obvious PII (names, emails, phone numbers) using a preprocessing step before sending ticket text to the LLM, (2) use an LLM provider with a data processing agreement (DPA) and zero-retention guarantees for enterprise customers, rather than a free/consumer-tier API, and (3) avoid sending full account financial details (like ARR) to the LLM unless strictly necessary for the task — only the fields actually needed for classification or summarization should be included in the prompt, following a data-minimization principle.

Our `.env`-based API key management (keeping credentials out of version control) is a first step toward this kind of security-conscious design, though production systems would need a proper secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) rather than a local `.env` file.

## 4. Scaling

At 10x ticket volume (5,000 tickets instead of 500), the first thing to break would be **API rate limits** — we directly experienced this during development with Google Gemini's free tier, and even Groq's generous free tier (a few thousand requests/day) would be insufficient at that scale processed in real-time.

The second bottleneck would be **cost** — every ticket triggers at least one LLM API call; at 10x volume this could become a meaningful line-item expense, especially if using larger/more expensive models.

To handle this scale, we would: (1) move to a paid tier with higher rate limits, or batch-process tickets asynchronously rather than requiring instant real-time responses for every single ticket, (2) introduce a caching layer so near-duplicate tickets (common issues reported by many users) don't each trigger a fresh, redundant LLM call, (3) use a smaller/cheaper model for the initial triage pass, reserving larger models only for ambiguous cases the smaller model flags as low-confidence, and (4) add a message queue (e.g., RabbitMQ, AWS SQS) between ticket ingestion and the triage agent, so spikes in ticket volume are smoothed out over time rather than overwhelming the system all at once.