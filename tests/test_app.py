import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

main = importlib.import_module("app.main")


def test_strip_html():
    assert main.strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_make_id_is_stable():
    assert main.make_id("x", "https://example.com", "Python") == main.make_id("x", "https://example.com", "Python")


def test_score_rewards_remote_and_skill_overlap():
    job = {
        "title": "Junior Python Automation Engineer",
        "description": "Python Playwright API Git automation",
        "tags": "python,playwright,api",
        "remote": True,
    }
    score, matched, gaps = main.score_job(job, ["python", "playwright", "api"])
    assert score == 100
    assert set(["python", "playwright", "api"]).issubset(set(matched))


def test_normalize_arbeitnow():
    raw = {
        "url": "https://example.com/job",
        "title": "Python Developer",
        "company_name": "Example",
        "location": "Remote",
        "remote": True,
        "description": "<p>Python and API</p>",
        "tags": ["Python", "API"],
    }
    result = main.normalize_arbeitnow(raw)
    assert result["title"] == "Python Developer"
    assert result["remote"] is True
    assert "Python and API" in result["description"]
