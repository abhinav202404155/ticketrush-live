"""user-service: signup, login (JWT), and "who am I".
Passwords are NEVER stored; only a bcrypt hash (a one-way scrambled form)."""
import os
import time
from contextlib import asynccontextmanager

import bcrypt
import jwt  # PyJWT
from fastapi import FastAPI, Header, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .db import pool

JWT_SECRET = os.environ["JWT_SECRET"]
TOKEN_LIFETIME_SECONDS = 24 * 3600
AUTH_LIMIT = os.getenv("AUTH_RATE_LIMIT", "10/minute")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=30)
    yield
    pool.close()


app = FastAPI(title="TicketRush user-service", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
Instrumentator().instrument(app).expose(app)  # /metrics for Prometheus


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit = 72 bytes


def make_token(user_id: int, email: str) -> str:
    payload = {"sub": str(user_id), "email": email, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/users/signup", status_code=201)
@limiter.limit(AUTH_LIMIT)
def signup(request: Request, body: Credentials):
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                (body.email.lower(), hashed),
            ).fetchone()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Email already registered")
    return {"id": row["id"], "email": body.email.lower()}


@app.post("/api/users/login")
@limiter.limit(AUTH_LIMIT)
def login(request: Request, body: Credentials):
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = %s", (body.email.lower(),)
        ).fetchone()
    # Same error for "no such user" and "wrong password" so attackers learn nothing.
    if not user or not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": make_token(user["id"], user["email"]), "token_type": "bearer"}


@app.get("/api/users/me")
def me(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"id": int(payload["sub"]), "email": payload["email"]}
