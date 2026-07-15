"""WSGI adapter for the provider-neutral Product API application."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from .application import ProductAPIRequest
from .auth import ProductAPIHandler

StartResponse = Callable[[str, list[tuple[str, str]]], object]

_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def _request_headers(environ: Mapping[str, object]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in environ.items():
        if not isinstance(value, str):
            continue
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").title()
            if name == "X-Request-Id":
                name = "X-Request-ID"
            elif name == "X-Correlation-Id":
                name = "X-Correlation-ID"
            headers[name] = value
    if isinstance(environ.get("CONTENT_TYPE"), str):
        headers["Content-Type"] = str(environ["CONTENT_TYPE"])
    return headers


def _request_body(environ: Mapping[str, object]) -> bytes:
    stream = environ.get("wsgi.input")
    if stream is None or not hasattr(stream, "read"):
        return b""
    raw_length = environ.get("CONTENT_LENGTH")
    try:
        length = int(str(raw_length)) if raw_length not in (None, "") else 0
    except ValueError:
        length = 0
    return stream.read(length) if length > 0 else b""


class ProductAPIWSGI:
    """Expose a Product API handler through a synchronous WSGI boundary."""

    def __init__(self, application: ProductAPIHandler) -> None:
        self.application = application

    def __call__(self, environ: Mapping[str, object], start_response: StartResponse) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        response = self.application.handle(
            ProductAPIRequest(
                method=method,
                path=path,
                headers=_request_headers(environ),
                body=_request_body(environ),
            )
        )
        status_text = _STATUS_TEXT.get(response.status_code, "Unknown")
        headers = list(response.headers.items())
        headers.append(("Content-Length", str(len(response.body))))
        start_response(f"{response.status_code} {status_text}", headers)
        return [response.body]
