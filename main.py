import json
import logging
import os
import re
import smtplib
import time
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SERVICE_NAME = "svc-product-description-v2"
SERVICE_TITLE = "AI Productbeschrijving & SEO Generator"
VERSION = "2.0.0"

_genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Rate Limiting ─────────────────────────────────────────────────────────────
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 60


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


# ── Database ──────────────────────────────────────────────────────────────────

def _db_connect():
    return pymysql.connect(
        host=os.getenv("MARIADB_PRIVATE_HOST", "mariadb.railway.internal"),
        port=int(os.getenv("MARIADB_PRIVATE_PORT", "3306")),
        user=os.getenv("MARIADB_USER", "railway"),
        password=os.getenv("MARIADB_PASSWORD", ""),
        database=os.getenv("MARIADB_DATABASE", "railway"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


@contextmanager
def db():
    conn = _db_connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_INIT_SQL = [
    """CREATE TABLE IF NOT EXISTS requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        service VARCHAR(100),
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        input TEXT,
        result TEXT,
        score INT,
        rounds INT,
        duration_ms INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS `usage` (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        request_count INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        tier VARCHAR(50) NOT NULL DEFAULT 'per_use',
        amount INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS checkouts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        service VARCHAR(100),
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
]

_MIGRATIONS = [
    "ALTER TABLE payments ADD COLUMN tier VARCHAR(50) NOT NULL DEFAULT 'per_use'",
    "ALTER TABLE payments ADD COLUMN amount INT NOT NULL DEFAULT 0",
    "ALTER TABLE payments DROP COLUMN IF EXISTS name",
    "ALTER TABLE payments DROP COLUMN IF EXISTS stripe_session_id",
    "ALTER TABLE payments DROP COLUMN IF EXISTS amount_cents",
    "ALTER TABLE payments DROP COLUMN IF EXISTS status",
    "ALTER TABLE requests ADD COLUMN service VARCHAR(100)",
    "ALTER TABLE requests ADD COLUMN duration_ms INT",
]


def init_db():
    try:
        with db() as conn:
            with conn.cursor() as cur:
                for sql in _INIT_SQL:
                    cur.execute(sql)
                for sql in _MIGRATIONS:
                    try:
                        cur.execute(sql)
                    except Exception:
                        pass
        logger.info("Database tables initialised")
    except Exception as e:
        logger.error(f"DB init failed: {e}", exc_info=True)


def get_usage(email: str) -> int:
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT request_count FROM `usage` WHERE email = %s", (email,))
                row = cur.fetchone()
                return row["request_count"] if row else 0
    except Exception as e:
        logger.error(f"DB get_usage error: {e}")
        return 0


def increment_usage(email: str):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO `usage` (email, request_count) VALUES (%s, 1)
                       ON DUPLICATE KEY UPDATE request_count = request_count + 1""",
                    (email,),
                )
    except Exception as e:
        logger.error(f"DB increment_usage error: {e}")


def has_unlimited(email: str) -> bool:
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM payments WHERE email = %s AND tier = 'unlimited'", (email,))
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"DB has_unlimited error: {e}")
        return False


def has_per_use_payment(email: str, use_number: int) -> bool:
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as cnt FROM payments WHERE email = %s AND tier = 'per_use'", (email,))
                row = cur.fetchone()
                return (row["cnt"] if row else 0) >= use_number
    except Exception as e:
        logger.error(f"DB has_per_use_payment error: {e}")
        return False


def save_payment_record(email: str, tier: str, amount: int):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO payments (email, tier, amount) VALUES (%s, %s, %s)", (email, tier, amount))
    except Exception as e:
        logger.error(f"DB save_payment error: {e}")


def save_request(email: str, name: str, inp: str, result: str, score: int, rounds: int, duration_ms: int):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO requests (service, email, name, input, result, score, rounds, duration_ms)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (SERVICE_NAME, email, name, inp, result, score, rounds, duration_ms),
                )
    except Exception as e:
        logger.error(f"DB save_request error: {e}")


def save_checkout(email: str, name: str):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO checkouts (service, email, name) VALUES (%s, %s, %s)", (SERVICE_NAME, email, name))
    except Exception as e:
        logger.error(f"DB save_checkout error: {e}")


def get_total_generations() -> int:
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as cnt FROM requests WHERE service = %s", (SERVICE_NAME,))
                row = cur.fetchone()
                return row["cnt"] if row else 0
    except Exception as e:
        logger.error(f"DB get_total_generations error: {e}")
        return 0


def check_pricing(email: str):
    request_count = get_usage(email)
    if request_count == 0:
        return None
    elif request_count <= 2:
        if not has_per_use_payment(email, request_count):
            return {"requires_payment": True, "tier": "per_use", "price": 0.99, "request_count": request_count}
        return None
    else:
        if not has_unlimited(email):
            return {"requires_payment": True, "tier": "unlimited", "price": 4.99, "request_count": request_count}
        return None


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=f"RoboServe {SERVICE_TITLE}", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.roboserve.eu", "https://roboserve.eu",
        "http://localhost", "http://localhost:3000", "http://localhost:8080",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(ip):
            return JSONResponse(status_code=429, content={"error": "Te veel verzoeken. Probeer het over een minuut opnieuw."})
    return await call_next(request)


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


# ── Prompts ───────────────────────────────────────────────────────────────────

PRODUCT_DESCRIPTION_PROMPT = """Je bent een expert copywriter gespecialiseerd in het schrijven van overtuigende productbeschrijvingen.

Productnaam: {product_name}
Productkenmerken: {product_features}
Doelgroep: {target_audience}
Tone-of-voice: {tone}

Schrijf een gedetailleerde en wervende productbeschrijving die de kernwaarden en voordelen benadrukt voor de opgegeven doelgroep en tone-of-voice. De beschrijving moet tussen de 150 en 250 woorden zijn.

BELANGRIJK: Gebruik GEEN markdown opmaak. Geen sterretjes, geen hashes, geen underscores voor opmaak. Alleen platte tekst met alinea's.

Geef ALLEEN de productbeschrijving terug, zonder extra tekst of aanhalingstekens."""

SEO_TITLE_PROMPT = """Je bent een expert SEO specialist.

Productnaam: {product_name}
Productkenmerken: {product_features}
Doelgroep: {target_audience}
Tone-of-voice: {tone}
Productbeschrijving: {description}

Schrijf EEN SEO-titel (max 60 tekens) die relevante zoekwoorden bevat en aantrekkelijk is voor de doelgroep.

BELANGRIJK: Geen markdown opmaak. Alleen platte tekst.

Geef ALLEEN de SEO-titel terug, zonder extra tekst of aanhalingstekens."""

SEO_META_PROMPT = """Je bent een expert SEO specialist.

Productnaam: {product_name}
Productkenmerken: {product_features}
Doelgroep: {target_audience}
Tone-of-voice: {tone}
Productbeschrijving: {description}
SEO Titel: {seo_title}

Schrijf EEN SEO meta-beschrijving (max 160 tekens) die gebruikers aanmoedigt om te klikken.

BELANGRIJK: Geen markdown opmaak. Alleen platte tekst.

Geef ALLEEN de SEO meta-beschrijving terug, zonder extra tekst of aanhalingstekens."""

QUALITY_PROMPT = """Je bent een kritische kwaliteitsbeoordelaar voor marketingteksten.

Productnaam: {product_name}
Productkenmerken: {product_features}
Doelgroep: {target_audience}
Tone-of-voice: {tone}

Gegenereerde tekst: {draft}

Beoordeel op relevantie, kwaliteit, tone-of-voice consistentie en effectiviteit.

Geef je antwoord EXACT in dit formaat:
SCORE: [getal 1-10]
FEEDBACK: [één zin met concrete verbeterpunten]"""

IMPROVE_PROMPT = """Je bent een expert copywriter. Verbeter de volgende productbeschrijving op basis van de feedback.

Productnaam: {product_name}
Productkenmerken: {product_features}
Doelgroep: {target_audience}
Tone-of-voice: {tone}

Huidige beschrijving: {draft}
Feedback: {feedback}

Schrijf een verbeterde versie (150-250 woorden).
BELANGRIJK: Gebruik GEEN markdown opmaak. Alleen platte tekst.

Geef ALLEEN de nieuwe tekst terug, zonder extra tekst of aanhalingstekens."""


# ── Gemini helpers ────────────────────────────────────────────────────────────

def call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    response = _genai_client.models.generate_content(model=model, contents=prompt)
    return strip_markdown(response.text.strip())


def parse_quality_response(response: str) -> tuple[int, str]:
    score = 5
    feedback = "Geen specifieke feedback beschikbaar."
    for line in response.splitlines():
        line = line.strip()
        if line.startswith("SCORE:"):
            try:
                score = max(1, min(10, int(line.replace("SCORE:", "").strip())))
            except ValueError:
                score = 5
        elif line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()
    return score, feedback


# ── Models ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    name: str
    email: str
    product_name: str
    product_features: str
    target_audience: str
    tone: str


class PaymentRequest(BaseModel):
    email: str
    name: str
    tier: str
    result: str = ""


class CheckoutRequest(BaseModel):
    email: str
    name: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}


@app.get("/api/v1/stats")
def stats():
    return {"total_generations": get_total_generations(), "service": SERVICE_NAME}


@app.post("/api/v1/checkout")
def checkout(req: CheckoutRequest):
    save_checkout(req.email, req.name)
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Welkom bij RoboServe — {SERVICE_TITLE}"
        msg["From"] = smtp_from
        msg["To"] = req.email
        msg.attach(MIMEText(f"Welkom bij RoboServe!\n\nU heeft zich aangemeld voor {SERVICE_TITLE}.\n\nMet vriendelijke groet,\nRoboServe", "plain", "utf-8"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo(); server.starttls(); server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [req.email], msg.as_string())
    except Exception as e:
        logger.error(f"Checkout email failed: {e}", exc_info=True)
    return {"status": "ok", "message": "Gelukt! U ontvangt een bevestiging per email."}


@app.post("/api/v1/generate")
def generate(req: GenerateRequest):
    user_input = f"{req.product_name} - {req.product_features}"
    logger.info(f"Generate request from {req.email} for: {user_input[:80]}")

    pricing = check_pricing(req.email)
    if pricing:
        return pricing

    start_time = time.time()
    try:
        description = ""
        score = 0
        feedback = ""
        rounds = 0

        for round_num in range(1, 4):
            rounds = round_num
            if round_num == 1:
                prompt = PRODUCT_DESCRIPTION_PROMPT.format(
                    product_name=req.product_name, product_features=req.product_features,
                    target_audience=req.target_audience, tone=req.tone,
                )
            else:
                prompt = IMPROVE_PROMPT.format(
                    product_name=req.product_name, product_features=req.product_features,
                    target_audience=req.target_audience, tone=req.tone,
                    draft=description, feedback=feedback,
                )
            description = call_gemini(prompt)
            quality_response = call_gemini(QUALITY_PROMPT.format(
                product_name=req.product_name, product_features=req.product_features,
                target_audience=req.target_audience, tone=req.tone, draft=description,
            ))
            score, feedback = parse_quality_response(quality_response)
            logger.info(f"Round {round_num}: score={score}")
            if score >= 7:
                break

        seo_title = call_gemini(SEO_TITLE_PROMPT.format(
            product_name=req.product_name, product_features=req.product_features,
            target_audience=req.target_audience, tone=req.tone, description=description,
        ))
        seo_description = call_gemini(SEO_META_PROMPT.format(
            product_name=req.product_name, product_features=req.product_features,
            target_audience=req.target_audience, tone=req.tone,
            description=description, seo_title=seo_title,
        ))

        duration_ms = int((time.time() - start_time) * 1000)
        result_json = json.dumps({"description": description, "seo_title": seo_title, "seo_description": seo_description}, ensure_ascii=False)
        save_request(req.email, req.name, user_input, result_json, score, rounds, duration_ms)
        increment_usage(req.email)

        return {
            "description": description, "seo_title": seo_title,
            "seo_description": seo_description, "score": score,
            "rounds": rounds, "name": req.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/v1/generate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generatie mislukt: {str(e)}")


@app.post("/webhook/stripe")
def webhook_stripe(req: PaymentRequest):
    logger.info(f"Payment webhook for {req.email}, tier={req.tier}")
    if req.tier == "per_use":
        save_payment_record(req.email, "per_use", 99)
    elif req.tier == "unlimited":
        save_payment_record(req.email, "unlimited", 499)
    else:
        raise HTTPException(status_code=400, detail="Ongeldig tier")

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "RoboServe — Betaling bevestigd"
        msg["From"] = smtp_from
        msg["To"] = req.email
        body = f"Beste {req.name},\n\nUw {'onbeperkt toegang is geactiveerd' if req.tier == 'unlimited' else 'betaling van EUR 0.99 is ontvangen'}.\n\nMet vriendelijke groet,\nRoboServe"
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo(); server.starttls(); server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [req.email], msg.as_string())
    except Exception as e:
        logger.error(f"Payment email failed: {e}", exc_info=True)
    return {"status": "paid", "tier": req.tier}
