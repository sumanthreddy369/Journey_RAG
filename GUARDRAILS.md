# Journey RAG Guardrails

## Enforced in the local API

- **Input validation:** rejects empty and oversized questions.
- **Prompt-injection screening:** blocks obvious attempts to override instructions or request hidden prompts.
- **In-memory rate limiting:** limits each local client to 20 requests per 60 seconds.
- **Grounding gate:** answers and learning responses require complete retrieved citations before they are returned.
- **Schema validation:** Pydantic validates learning requests, quiz structure, quiz submissions, and evaluation output.
- **Answer-key isolation:** local quiz sessions keep answer keys server-side rather than returning them in learner-facing quiz output.
- **Safe failures:** guardrail blocks return controlled HTTP errors instead of continuing into model generation.

## Guardrails planned before real learner data or enterprise deployment

- Authentication and authorization for learners, instructors, and administrators.
- Microsoft Entra OAuth consent, least-privilege Microsoft Graph permissions, and tenant/site allow lists.
- Encryption, retention/deletion rules, audit logging, and consent controls for learner-progress data.
- Persistent rate limits and quotas backed by a reviewed deployment datastore.
- Centralized structured logging, alerting, and trace review.
- Versioned adversarial, grounding, citation, and quiz-quality evaluation sets.
- Human review/appeal handling for learner evaluation outcomes.

## Boundaries

These local controls are intentionally deterministic and testable. They are not a substitute for production authentication, network security, data-governance review, or institutional privacy approval.
