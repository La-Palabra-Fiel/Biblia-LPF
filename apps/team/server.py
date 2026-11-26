#!/usr/bin/env python3
"""Serve the local LPF named-human chapter review desk."""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk  # noqa: E402

PUBLIC = Path(__file__).resolve().parent / "public"
HOST = os.environ.get("LBF_TEAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("LBF_TEAM_PORT", "1435"))
MAX_REQUEST_BYTES = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "LPFReview"
    sys_version = ""

    def version_string(self):
        return self.server_version

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
        self.end_headers()
        self.wfile.write(data)

    def read_value(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as exc:
            raise ValueError("The request length is invalid.") from exc
        if length > MAX_REQUEST_BYTES:
            raise ValueError("The request is too large.")
        try:
            value = json.loads(self.rfile.read(length).decode() or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("The request was not valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("The request must be a JSON object.")
        return value

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
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
        if parsed.path in {"/revision-libros", "/revision-libros.html"}:
            return self.send_value(200, body=(PUBLIC / "revision-libros.html").read_bytes(), content_type="text/html; charset=utf-8")
        return self.send_value(404, {"error": "Not found"})

    def do_POST(self):  # noqa: N802
        actions = {
            "/api/claim": lambda p: desk.claim(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/release": lambda p: desk.release(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/prepare-estimate": lambda p: desk.prepare_estimate(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/prepare": lambda p: desk.prepare(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("costConfirmed"), confirmed_maximum_usd=p.get("confirmedMaximumUsd")),
            "/api/prepare-verse-estimate": lambda p: desk.prepare_estimate(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("verse")),
            "/api/prepare-verse": lambda p: desk.prepare(p.get("name"), p.get("book"), p.get("chapter"), p.get("token"), p.get("costConfirmed"), p.get("verse"), p.get("confirmedMaximumUsd")),
            "/api/stop": lambda p: desk.stop(p.get("name"), p.get("book"), p.get("chapter"), p.get("token")),
            "/api/build-nt-syntax": desk.build_nt_syntax_candidate,
            "/api/audit-verse-estimate": desk.audit_verse_estimate,
            "/api/audit-verse": desk.audit_verse,
            "/api/reopen-verse": desk.reopen_verse,
            "/api/cancel-revision": desk.cancel_revision,
            "/api/approve-verse": desk.approve_verse,
            "/api/approve-clean-chapter": desk.approve_clean_chapter,
            "/api/finish-chapter": desk.finish_chapter,
            "/api/revision-libros/libro": lambda p: desk.peer_review_book(p.get("accessKey"), p.get("book")),
            "/api/revision-libros/firmar": desk.sign_peer_review,
        }
        action = actions.get(urlparse(self.path).path)
        if not action:
            return self.send_value(404, {"error": "Not found"})
        try:
            result = action(self.read_value())
            return self.send_value(200, result if isinstance(result, dict) else desk.board())
        except ValueError as exc:
            return self.send_value(400, {"error": str(exc)})
        except Exception as exc:
            return self.send_value(500, {"error": str(exc)})


def main():
    desk.secure_private_storage()
    desk.recover_interrupted_preparations()
    threading.Thread(target=desk.warm_totals, daemon=True).start()
    threading.Thread(target=desk.warm_nt_syntax_board, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"LPF chapter review http://{HOST}:{PORT}/ model={desk.model_name()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
