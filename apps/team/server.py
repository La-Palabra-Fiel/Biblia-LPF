#!/usr/bin/env python3
"""Serve the authenticated LPF named-human review desk."""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk  # noqa: E402

PUBLIC = Path(__file__).resolve().parent / "public"
ENVIRONMENT = os.environ.get("LBF_TEAM_ENV", "development").casefold()
PRODUCTION = ENVIRONMENT == "production"
HOST = os.environ.get("LBF_TEAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("LBF_TEAM_PORT", "1435"))
MAX_REQUEST_BYTES = min(max(1024, int(os.environ.get("LBF_TEAM_MAX_REQUEST_BYTES", "1048576"))), 4 * 1024 * 1024)
ALLOWED_ORIGINS = {value.strip().rstrip("/") for value in os.environ.get("LBF_TEAM_ALLOWED_ORIGINS", "").split(",") if value.strip()}
ALLOWED_HOSTS = {value.strip().casefold() for value in os.environ.get("LBF_TEAM_ALLOWED_HOSTS", "").split(",") if value.strip()}
TRUST_PROXY = os.environ.get("LBF_TEAM_TRUST_PROXY", "").casefold() in {"1", "true", "yes"}
GATEWAY_SECRET = os.environ.get("LBF_TEAM_GATEWAY_SECRET", "")
AUTH_FAILURE_LIMIT = 10
AUTH_FAILURE_WINDOW = 15 * 60
_auth_failures: dict[str, deque[float]] = defaultdict(deque)
_auth_lock = threading.Lock()


def production_configuration_errors() -> list[str]:
    """Refuse production startup when a security invariant is missing."""
    errors: list[str] = []
    if not PRODUCTION:
        return errors
    if not os.environ.get("LBF_TEAM_DATA_DIR"):
        errors.append("LBF_TEAM_DATA_DIR must point at a private persistent volume")
    elif any(path.is_symlink() for path in (desk.VAR, *desk.VAR.rglob("*"))):
        errors.append("LBF_TEAM_DATA_DIR must not contain symbolic links")
    if not ALLOWED_ORIGINS or any(urlparse(origin).scheme != "https" for origin in ALLOWED_ORIGINS):
        errors.append("LBF_TEAM_ALLOWED_ORIGINS must contain only explicit https:// origins")
    if not ALLOWED_HOSTS:
        errors.append("LBF_TEAM_ALLOWED_HOSTS must list the public host name(s)")
    if len(GATEWAY_SECRET) < 32:
        errors.append("LBF_TEAM_GATEWAY_SECRET must be a random value of at least 32 characters")
    people = desk.load_people()
    plaintext = [name for name, value in people.items() if not desk.credential_is_hashed(value)]
    if plaintext:
        errors.append("plaintext reviewer credentials remain: " + ", ".join(plaintext))
    if not people:
        errors.append("at least one reviewer must be configured")
    return errors


def client_ip(handler) -> str:
    if TRUST_PROXY:
        forwarded = str(handler.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return str(handler.client_address[0])


def auth_rate_limited(key: str) -> bool:
    cutoff = time.monotonic() - AUTH_FAILURE_WINDOW
    with _auth_lock:
        attempts = _auth_failures[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        return len(attempts) >= AUTH_FAILURE_LIMIT


def record_auth_failure(key: str) -> None:
    with _auth_lock:
        _auth_failures[key].append(time.monotonic())


def clear_auth_failures(key: str) -> None:
    with _auth_lock:
        _auth_failures.pop(key, None)


class Handler(BaseHTTPRequestHandler):
    server_version = "LPFReview"
    sys_version = ""

    def version_string(self):
        return self.server_version

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, fmt, *args):
        return

    def send_value(self, code, value=None, body=None, content_type="application/json"):
        data = body if body is not None else json.dumps(value or {}, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        if PRODUCTION:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.end_headers()
        self.wfile.write(data)

    def read_value(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as exc:
            raise ValueError("The request length is invalid.") from exc
        if length > MAX_REQUEST_BYTES:
            raise OverflowError("The request is too large.")
        try:
            value = json.loads(self.rfile.read(length).decode() or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("The request was not valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("The request must be a JSON object.")
        return value

    def host_allowed(self):
        return not PRODUCTION or str(self.headers.get("Host") or "").casefold() in ALLOWED_HOSTS

    def origin_allowed(self):
        return not PRODUCTION or str(self.headers.get("Origin") or "").rstrip("/") in ALLOWED_ORIGINS

    def gateway_allowed(self):
        submitted = str(self.headers.get("X-LBF-Gateway") or "")
        return not PRODUCTION or secrets.compare_digest(submitted, GATEWAY_SECRET)

    def do_GET(self):  # noqa: N802
        if not self.host_allowed():
            return self.send_value(400, {"error": "Unrecognized request host."})
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            return self.send_value(200, {"status": "ok"})
        if not self.gateway_allowed():
            return self.send_value(401, {"error": "Private gateway authentication is required."})
        if parsed.path == "/api/board":
            return self.send_value(200, desk.board())
        if parsed.path == "/api/nt-syntax-board":
            try:
                return self.send_value(200, desk.nt_syntax_board())
            except ValueError as exc:
                return self.send_value(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                return self.send_value(503, {"error": str(exc)})
        if parsed.path == "/api/nt-syntax":
            query = parse_qs(parsed.query)
            try:
                return self.send_value(200, desk.nt_syntax_view((query.get("book") or [""])[0], (query.get("chapter") or [""])[0]))
            except ValueError as exc:
                return self.send_value(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                return self.send_value(503, {"error": str(exc)})
        if parsed.path == "/api/chapter":
            query = parse_qs(parsed.query)
            try:
                return self.send_value(200, desk.chapter_view((query.get("book") or [""])[0], (query.get("chapter") or [""])[0]))
            except ValueError as exc:
                return self.send_value(400, {"error": str(exc)})
        if parsed.path in {"/", "/index.html"}:
            return self.send_value(200, body=(PUBLIC / "index.html").read_bytes(), content_type="text/html; charset=utf-8")
        if parsed.path in {"/peer-review", "/peer-review.html"}:
            return self.send_value(200, body=(PUBLIC / "peer-review.html").read_bytes(), content_type="text/html; charset=utf-8")
        return self.send_value(404, {"error": "Not found"})

    def do_POST(self):  # noqa: N802
        key = client_ip(self)
        if not self.host_allowed():
            return self.send_value(400, {"error": "Unrecognized request host."})
        if not self.gateway_allowed():
            return self.send_value(401, {"error": "Private gateway authentication is required."})
        if not self.origin_allowed():
            return self.send_value(403, {"error": "Request origin is not allowed."})
        if auth_rate_limited(key):
            return self.send_value(429, {"error": "Too many failed sign-in attempts. Try again later."})
        if not str(self.headers.get("Content-Type") or "").casefold().startswith("application/json"):
            return self.send_value(415, {"error": "Requests must use application/json."})
        actions = {
            "/api/claim": lambda p: desk.claim(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/release": lambda p: desk.release(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/prepare-estimate": lambda p: desk.prepare_estimate(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/prepare": lambda p: desk.prepare(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("costConfirmed"), confirmed_maximum_usd=p.get("confirmedMaximumUsd")),
            "/api/prepare-verse-estimate": lambda p: desk.prepare_estimate(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("verse")),
            "/api/prepare-verse": lambda p: desk.prepare(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("costConfirmed"), p.get("verse"), p.get("confirmedMaximumUsd")),
            "/api/stop": lambda p: desk.stop(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/build-nt-syntax": desk.build_nt_syntax_candidate,
            "/api/audit-verse": desk.audit_verse,
            "/api/reopen-verse": desk.reopen_verse,
            "/api/cancel-revision": desk.cancel_revision,
            "/api/approve-verse": desk.approve_verse,
            "/api/approve-clean-chapter": desk.approve_clean_chapter,
            "/api/finish-chapter": desk.finish_chapter,
            "/api/peer-review/home": lambda p: desk.peer_review_home(p.get("name"), p.get("token")),
            "/api/peer-review/book": lambda p: desk.peer_review_view(p.get("name"), p.get("token"), p.get("book")),
            "/api/peer-review/sign": desk.sign_peer_review,
        }
        action = actions.get(urlparse(self.path).path)
        if not action:
            return self.send_value(404, {"error": "Not found"})
        try:
            result = action(self.read_value())
            clear_auth_failures(key)
            return self.send_value(200, result if isinstance(result, dict) else desk.board())
        except OverflowError as exc:
            return self.send_value(413, {"error": str(exc)})
        except ValueError as exc:
            if "Name or token does not match" in str(exc):
                record_auth_failure(key)
            return self.send_value(400, {"error": str(exc)})
        except Exception as exc:
            message = "Internal server error." if PRODUCTION else str(exc)
            return self.send_value(500, {"error": message})


def main():
    desk.secure_private_storage()
    try:
        desk.load_people()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Private reviewer data is invalid: {desk.PEOPLE}: {exc}") from exc
    errors = production_configuration_errors()
    if errors:
        raise SystemExit("Unsafe production configuration:\n- " + "\n- ".join(errors))
    threading.Thread(target=desk.warm_totals, daemon=True).start()
    threading.Thread(target=desk.warm_nt_syntax_board, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"LPF review desk http://{HOST}:{PORT}/ model={desk.model_name()} env={ENVIRONMENT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
