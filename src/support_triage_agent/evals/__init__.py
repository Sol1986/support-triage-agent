"""Offline evaluation harness: golden dataset, deterministic and LLM-judge
evaluators, and metric aggregation.

Runs against `pipeline.process_ticket()` in CI/offline contexts only — it is
never wired into the production graph, so evaluation cost and latency never
affect a live request. See docs/EVALS_GUARDRAILS_PLAN.md for the full design.
"""
