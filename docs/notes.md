It's a deterministic quality score (4–10) computed by evaluate_response after each draft, checking 3 things about the response text:

- acknowledges_category — does it mention the ticket's category (e.g. "billing")?
- explains_next_step — does it contain the phrase "next step"?
- provides_reference — does it contain the phrase "reference number"?

Score = 4 baseline + 2 points per check passed, so it ranges 4 (none passed) → 10 (all three passed).

The graph uses this to decide whether to auto-revise: if the score is ≥ 8, it's good enough and the ticket finishes; if it's < 8, the draft goes back to revise_response for another attempt — up to MAX_REVISIONS (2) times, after which it finishes regardless of score. revision_count in the response tells you how many times that happened, and evaluation_feedback tells you which specific checks failed on the last pass.

In deterministic mode, the first draft template never includes "next step" or "reference number", so it always scores 6 and needs exactly one revision (the revised template hardcodes all three) — which is why you'll consistently see evaluation_score: 10 and revision_count: 1 on that mode. In LLM mode, Gemini has to actually earn the score in fewer/more revisions depending on what it writes.