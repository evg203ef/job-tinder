# Job Tinder

A Tinder-style job discovery app for developers.

Swipe **right** to like a vacancy, **left** to pass, and keep a personal queue of matches. Each card shows a transparent match score based on the user's skills.

## What this project demonstrates

- Python + FastAPI backend
- REST endpoints
- SQLite persistence
- HTTP/API integration
- JSON normalization from multiple job sources
- HTML parsing with BeautifulSoup
- Personalized skill matching
- Browser-based drag / swipe interactions
- Frontend state management with vanilla JavaScript
- Basic automated tests

## Data sources

The MVP integrates two public job feeds:

- **Arbeitnow Job Board API** — no API key is required; the API includes a `remote` field and aggregates postings from multiple ATS platforms.
- **Remote OK JSON feed** — Remote OK exposes a JSON feed for remote job listings.

See the source documentation before production use and respect each provider's terms and rate limits.

## Core UX

1. Sync job data.
2. Browse one job card at a time.
3. Drag left/right or press Pass/Like.
4. Open the original vacancy from the card.
5. Review liked jobs in **Matches**.
6. Change your skill profile in **Skills** and the Match Score recalculates.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Project structure

```text
job-tinder/
├── app/
│   ├── main.py
│   └── static/
│       ├── app.js
│       ├── index.html
│       └── styles.css
├── tests/
│   └── test_app.py
├── requirements.txt
└── README.md
```

## Roadmap

- AI-generated job summaries
- Resume upload and semantic matching
- Better duplicate detection across sources
- Filters for salary, country and timezone overlap
- Undo last swipe
- Application tracking (`saved → applied → interview → rejected`)
- Authentication and per-user profiles
- Embedding-based semantic matching

## Portfolio note

This is a personal learning project built with AI-assisted development. The goal is to use AI coding tools while progressively improving the underlying Python, HTTP, data-handling and debugging fundamentals.
