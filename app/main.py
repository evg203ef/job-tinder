from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DB_PATH = ROOT_DIR / "job_tinder.db"
STATIC_DIR = BASE_DIR / "static"

DEFAULT_SKILLS = [
    "python", "playwright", "automation", "api", "json", "git", "github",
    "fastapi", "web scraping", "ai", "llm", "sql", "requests"
]

SOURCES = {
    "arbeitnow": "https://www.arbeitnow.com/api/job-board-api",
    "remoteok": "https://remoteok.com/api",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Tinder", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ProfileUpdate(BaseModel):
    skills: list[str] = Field(default_factory=list)


class SwipeRequest(BaseModel):
    job_id: str
    decision: str


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                remote INTEGER NOT NULL DEFAULT 1,
                salary TEXT,
                description TEXT,
                url TEXT NOT NULL,
                tags TEXT,
                published_at TEXT,
                fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS swipes (
                job_id TEXT PRIMARY KEY,
                decision TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                skills TEXT NOT NULL
            );
            INSERT OR IGNORE INTO profile (id, skills) VALUES (
                1,
                'python,playwright,automation,api,json,git,github,fastapi,web scraping,ai,llm,sql,requests'
            );
            """
        )


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def make_id(source: str, url: str, title: str) -> str:
    raw = f"{source}|{url}|{title}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def normalize_arbeitnow(item: dict[str, Any]) -> dict[str, Any]:
    url = str(item.get("url") or "")
    title = str(item.get("title") or "Untitled")
    return {
        "id": make_id("arbeitnow", url, title),
        "source": "arbeitnow",
        "title": title,
        "company": str(item.get("company_name") or "Unknown company"),
        "location": str(item.get("location") or "Remote / unspecified"),
        "remote": bool(item.get("remote")),
        "salary": "",
        "description": strip_html(item.get("description")),
        "url": url,
        "tags": ",".join(str(x) for x in (item.get("tags") or [])),
        "published_at": str(item.get("created_at") or item.get("created") or ""),
    }


def normalize_remoteok(item: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(item, dict) or not item.get("position"):
        return None
    url = str(item.get("url") or "")
    title = str(item.get("position") or "Untitled")
    location = str(item.get("location") or "Worldwide")
    salary = ""
    if item.get("salary_min") or item.get("salary_max"):
        salary = f"{item.get('salary_min', '')}–{item.get('salary_max', '')}"
    return {
        "id": make_id("remoteok", url, title),
        "source": "remoteok",
        "title": title,
        "company": str(item.get("company") or "Unknown company"),
        "location": location,
        "remote": True,
        "salary": salary,
        "description": strip_html(item.get("description")),
        "url": url,
        "tags": ",".join(item.get("tags") or []),
        "published_at": str(item.get("date") or ""),
    }


def fetch_jobs() -> list[dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    headers = {"User-Agent": "Job-Tinder/0.1 (+portfolio project)"}

    for source, url in SOURCES.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            continue

        items = payload.get("data", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            continue

        for item in items:
            job = (
                normalize_arbeitnow(item)
                if source == "arbeitnow"
                else normalize_remoteok(item)
            )
            if not job:
                continue
            normalized[job["id"]] = job

    fetched_at = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        for job in normalized.values():
            conn.execute(
                """
                INSERT INTO jobs (
                    id, source, title, company, location, remote, salary,
                    description, url, tags, published_at, fetched_at
                )
                VALUES (
                    :id, :source, :title, :company, :location, :remote, :salary,
                    :description, :url, :tags, :published_at, :fetched_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    location=excluded.location,
                    remote=excluded.remote,
                    salary=excluded.salary,
                    description=excluded.description,
                    tags=excluded.tags,
                    published_at=excluded.published_at,
                    fetched_at=excluded.fetched_at
                """,
                {**job, "fetched_at": fetched_at},
            )
    return list(normalized.values())


def get_profile_skills() -> list[str]:
    with db() as conn:
        row = conn.execute("SELECT skills FROM profile WHERE id = 1").fetchone()
    if not row:
        return DEFAULT_SKILLS
    return [x.strip().lower() for x in row["skills"].split(",") if x.strip()]


def score_job(
    job: sqlite3.Row | dict[str, Any], skills: list[str]
) -> tuple[int, list[str], list[str]]:
    text = " ".join(
        str(job.get(key, "") if isinstance(job, dict) else job[key])
        for key in ("title", "description", "tags")
    ).lower()
    matched = sorted({skill for skill in skills if skill in text})
    must_have = [
        "python", "api", "git", "sql", "playwright",
        "fastapi", "web scraping", "automation", "ai"
    ]
    gaps = [skill for skill in must_have if skill not in matched]
    score = round(min(100, (len(matched) / max(1, len(skills))) * 100))
    if (job.get("remote", 0) if isinstance(job, dict) else job["remote"]):
        score = min(100, score + 10)
    return score, matched, gaps


def row_to_dict(row: sqlite3.Row, skills: list[str]) -> dict[str, Any]:
    item = dict(row)
    score, matched, gaps = score_job(item, skills)
    item["match_score"] = score
    item["matched_skills"] = matched
    item["skill_gaps"] = gaps[:4]
    item["remote"] = bool(item["remote"])
    return item


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/profile")
def profile() -> dict[str, Any]:
    return {"skills": get_profile_skills()}


@app.put("/api/profile")
def update_profile(payload: ProfileUpdate) -> dict[str, Any]:
    skills = sorted({x.strip().lower() for x in payload.skills if x.strip()})
    if not skills:
        skills = DEFAULT_SKILLS
    with db() as conn:
        conn.execute("UPDATE profile SET skills = ? WHERE id = 1", (",".join(skills),))
    return {"skills": skills}


@app.post("/api/sync")
def sync() -> dict[str, Any]:
    jobs = fetch_jobs()
    return {"synced": len(jobs)}


@app.get("/api/jobs")
def jobs(limit: int = Query(30, ge=1, le=100), mode: str = Query("new")) -> dict[str, Any]:
    skills = get_profile_skills()
    with db() as conn:
        if mode == "liked":
            rows = conn.execute(
                """
                SELECT j.*
                FROM jobs j
                JOIN swipes s ON s.job_id=j.id
                WHERE s.decision='like'
                ORDER BY j.fetched_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT j.*
                FROM jobs j
                LEFT JOIN swipes s ON s.job_id=j.id
                WHERE s.job_id IS NULL
                ORDER BY j.fetched_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return {"jobs": [row_to_dict(row, skills) for row in rows]}


@app.post("/api/swipe")
def swipe(payload: SwipeRequest) -> dict[str, str]:
    if payload.decision not in {"like", "pass"}:
        raise HTTPException(status_code=400, detail="decision must be 'like' or 'pass'")
    with db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM jobs WHERE id = ?", (payload.job_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="job not found")
        conn.execute(
            "INSERT INTO swipes(job_id, decision, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(job_id) DO UPDATE SET decision=excluded.decision, created_at=excluded.created_at",
            (payload.job_id, payload.decision, datetime.now(timezone.utc).isoformat()),
        )
    return {"status": "ok", "decision": payload.decision}


@app.delete("/api/swipe/{job_id}")
def undo_swipe(job_id: str) -> dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM swipes WHERE job_id = ?", (job_id,))
    return {"status": "ok"}


@app.get("/api/stats")
def stats() -> dict[str, int]:
    with db() as conn:
        liked = conn.execute(
            "SELECT COUNT(*) FROM swipes WHERE decision='like'"
        ).fetchone()[0]
        passed = conn.execute(
            "SELECT COUNT(*) FROM swipes WHERE decision='pass'"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    return {"liked": liked, "passed": passed, "total": total}
