# Project notes

This MVP is intentionally small enough to understand end-to-end.

## Architecture

FastAPI serves the API and static frontend. SQLite stores jobs, swipe decisions and one local skill profile. External public job feeds are normalized into one internal schema.

## First technical challenges to study

- HTTP status codes and timeouts
- JSON schema differences between providers
- database constraints and upserts
- frontend pointer events for swipe gestures
- keeping the scoring function deterministic and explainable
