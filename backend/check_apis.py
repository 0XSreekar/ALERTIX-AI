"""
Quick connectivity check for all Alertix external services.
Run from backend/: python check_apis.py
"""
import os
import sys

# Load .env from project root
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

DB_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "")
REDIS_URL = os.getenv("REDIS_URL", "")
NASA_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "")
RESEND_KEY = os.getenv("RESEND_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
SENTRY_DSN = os.getenv("SENTRY_DSN_BACKEND", "")

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
SKIP = "\033[93m SKIP\033[0m"


def check_postgres():
    label = "Supabase Postgres"
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(DB_URL_SYNC, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version()")).scalar()
            ext = conn.execute(
                sqlalchemy.text("SELECT extname FROM pg_extension WHERE extname='postgis'")
            ).fetchone()
        postgis = "PostGIS=YES" if ext else "PostGIS=MISSING"
        print(f"{PASS} {label}: {result[:40]}... | {postgis}")
        return ext is not None
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_redis():
    label = "Upstash Redis"
    try:
        import redis as redis_lib
        r = redis_lib.from_url(REDIS_URL, socket_connect_timeout=10, decode_responses=True)
        r.ping()
        info = r.info("server")
        print(f"{PASS} {label}: Redis {info.get('redis_version','?')}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_nasa_firms():
    label = "NASA FIRMS"
    if not NASA_KEY:
        print(f"{SKIP} {label}: key not set")
        return False
    try:
        import urllib.request
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{NASA_KEY}/VIIRS_SNPP_NRT/68.1,6.7,97.4,37.3/1/2026-05-24"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "alertix-check/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            first_line = resp.read(200).decode("utf-8").split("\n")[0]
        print(f"{PASS} {label}: {first_line[:80]}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_resend():
    label = "Resend Email"
    if not RESEND_KEY:
        print(f"{SKIP} {label}: key not set")
        return False
    try:
        import json
        import urllib.request
        req = urllib.request.Request(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {RESEND_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        print(f"{PASS} {label}: authenticated, {len(data.get('data', []))} domain(s)")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_groq():
    label = "Groq LLM"
    if not GROQ_KEY:
        print(f"{SKIP} {label}: key not set")
        return False
    try:
        import json
        import urllib.request
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        models = [m["id"] for m in data.get("data", [])[:3]]
        print(f"{PASS} {label}: {models}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_gemini():
    label = "Gemini API"
    if not GEMINI_KEY:
        print(f"{SKIP} {label}: key not set")
        return False
    try:
        import json
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])[:2]]
        print(f"{PASS} {label}: {models}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        return False


def check_sentry():
    label = "Sentry DSN"
    if not SENTRY_DSN:
        print(f"{SKIP} {label}: DSN not set")
        return False
    # Just validate format — don't actually send an event
    parts = SENTRY_DSN.split("@")
    if len(parts) == 2 and "ingest" in parts[1]:
        print(f"{PASS} {label}: DSN format valid ({parts[1].split('/')[0]})")
        return True
    print(f"{FAIL} {label}: unexpected DSN format")
    return False


if __name__ == "__main__":
    print("\n=== Alertix API Connectivity Check ===\n")
    results = {
        "Postgres": check_postgres(),
        "Redis": check_redis(),
        "NASA FIRMS": check_nasa_firms(),
        "Resend": check_resend(),
        "Groq": check_groq(),
        "Gemini": check_gemini(),
        "Sentry": check_sentry(),
    }
    print("\n=== Summary ===")
    for name, ok in results.items():
        status = "\033[92mOK\033[0m" if ok else "\033[91mFAIL\033[0m"
        print(f"  {name:15} {status}")

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
