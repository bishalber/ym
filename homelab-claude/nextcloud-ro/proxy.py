#!/usr/bin/env python3
"""nextcloud-ro: a READ-ONLY door from claude-box to your Nextcloud files.

Nextcloud app passwords cannot be limited to read-only, so the password lives here, in a
separate container, and never inside claude-box. This proxy exposes only three read operations
and adds the credentials itself:

  PROPFIND /files/<path>              list a folder or stat a file (Depth: 0 or 1 only)
  GET|HEAD /files/<path>              download a file (Nextcloud decrypts server-side encryption)
  GET      /find?q=<text>[&path=<p>]  search file names under <path> (max 200 results)

Everything else (PUT, DELETE, MOVE, COPY, MKCOL, PROPPATCH, LOCK, other URLs) gets 405/404.
"""
import base64
import http.client
import os
import posixpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit
from xml.sax.saxutils import escape

UPSTREAM = urlsplit(os.environ.get("NC_UPSTREAM", "http://host.docker.internal:8080"))
HOST_HEADER = os.environ.get("NC_HOST_HEADER", "localhost:8080")  # must be in trusted_domains
USER = os.environ.get("NC_USER", "")
PASSWORD = os.environ.get("NC_APP_PASSWORD", "")
PORT = int(os.environ.get("PORT", "8080"))
CHUNK = 64 * 1024
DAV_FILES = f"/remote.php/dav/files/{quote(USER)}"
PROPS = ("<d:displayname/><d:getcontentlength/><d:getlastmodified/>"
         "<d:resourcetype/><d:getcontenttype/>")
PROPFIND_BODY = f'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop>{PROPS}</d:prop></d:propfind>'
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
       "proxy-authenticate", "proxy-authorization", "set-cookie", "www-authenticate"}


def safe_path(raw: str) -> str | None:
    """Return a normalized, URL-encoded path below the user's root, or None if it escapes."""
    decoded = unquote(raw)
    if "\x00" in decoded or any(seg == ".." for seg in decoded.split("/")):
        return None
    norm = posixpath.normpath("/" + decoded.lstrip("/"))
    return "" if norm == "/" else quote(norm)


class Handler(BaseHTTPRequestHandler):
    server_version = "nextcloud-ro/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[nextcloud-ro] {self.command} {self.path.split('?')[0][:120]} {args[1] if len(args) > 1 else ''}",
              flush=True)

    def _error(self, code: int, msg: str):
        body = (msg + "\n").encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _upstream(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
        cls = http.client.HTTPSConnection if UPSTREAM.scheme == "https" else http.client.HTTPConnection
        conn = cls(UPSTREAM.hostname, UPSTREAM.port, timeout=120)
        h = {"Host": HOST_HEADER, "Authorization": "Basic " + base64.b64encode(
            f"{USER}:{PASSWORD}".encode()).decode(), "OCS-APIRequest": "true"}
        h.update(headers or {})
        conn.request(method, path, body=body, headers=h)
        return conn, conn.getresponse()

    def _relay(self, conn, resp):
        try:
            self.send_response(resp.status)
            length = resp.getheader("Content-Length")
            for k, v in resp.getheaders():
                if k.lower() not in HOP and k.lower() != "content-length":
                    self.send_header(k, v)
            if length is not None:
                self.send_header("Content-Length", length)
                self.end_headers()
                if self.command != "HEAD":
                    while chunk := resp.read(CHUNK):
                        self.wfile.write(chunk)
            else:  # no length (e.g. multistatus XML): buffer, it is small
                data = resp.read() if self.command != "HEAD" else b""
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        finally:
            conn.close()

    def _files_path(self) -> str | None:
        parts = urlsplit(self.path)
        if parts.path != "/files" and not parts.path.startswith("/files/"):
            return None
        return safe_path(parts.path[len("/files"):])

    def _guard(self) -> bool:
        if not (USER and PASSWORD):
            self._error(503, "NC_USER / NC_APP_PASSWORD not configured")
            return False
        if int(self.headers.get("Content-Length") or 0) > 0:
            self._error(400, "request bodies are not accepted")
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        parts = urlsplit(self.path)
        if parts.path == "/healthz":
            return self._error(200, "ok")
        if parts.path == "/find":
            return self._find(parse_qs(parts.query))
        p = self._files_path()
        if p is None:
            return self._error(404, "use /files/<path> or /find?q=")
        fwd = {k: self.headers[k] for k in ("Range", "If-None-Match", "If-Modified-Since") if self.headers.get(k)}
        self._relay(*self._upstream(self.command, DAV_FILES + p, headers=fwd))

    do_HEAD = do_GET

    def do_PROPFIND(self):
        if not self._guard():
            return
        p = self._files_path()
        if p is None:
            return self._error(404, "use /files/<path>")
        depth = self.headers.get("Depth", "1")
        if depth not in ("0", "1"):
            return self._error(400, "Depth must be 0 or 1")
        self._relay(*self._upstream("PROPFIND", DAV_FILES + (p or "/"), PROPFIND_BODY.encode(),
                                    {"Depth": depth, "Content-Type": "application/xml; charset=utf-8"}))

    def _find(self, qs: dict):
        q = (qs.get("q") or [""])[0].strip()
        if not q or len(q) > 200:
            return self._error(400, "q is required (max 200 chars)")
        scope = safe_path((qs.get("path") or [""])[0])
        if scope is None:
            return self._error(400, "bad path")
        like = escape(f"%{q}%")  # % and _ in q act as wildcards; they still match themselves
        href = escape(f"/files/{USER}" + unquote(scope or ""))
        body = (f'<?xml version="1.0" encoding="UTF-8"?><d:searchrequest xmlns:d="DAV:"><d:basicsearch>'
                f'<d:select><d:prop>{PROPS}</d:prop></d:select>'
                f'<d:from><d:scope><d:href>{href}</d:href><d:depth>infinity</d:depth></d:scope></d:from>'
                f'<d:where><d:like><d:prop><d:displayname/></d:prop><d:literal>{like}</d:literal></d:like></d:where>'
                f'<d:orderby/><d:limit><d:nresults>200</d:nresults></d:limit>'
                f'</d:basicsearch></d:searchrequest>')
        self._relay(*self._upstream("SEARCH", "/remote.php/dav/", body.encode(),
                                    {"Content-Type": "text/xml; charset=utf-8"}))

    def _deny(self):
        self._error(405, "read-only: only GET, HEAD and PROPFIND are allowed")

    do_PUT = do_POST = do_DELETE = do_MOVE = do_COPY = do_MKCOL = do_PROPPATCH = _deny
    do_LOCK = do_UNLOCK = do_PATCH = do_SEARCH = do_REPORT = do_OPTIONS = _deny


if __name__ == "__main__":
    print(f"[nextcloud-ro] :{PORT} -> {UPSTREAM.geturl()} as {USER or '(unset)'} (read-only)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
