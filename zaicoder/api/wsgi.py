"""WSGI adapter for the provider-neutral Product API application."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Mapping, Tuple

from .application import ProductAPIApplication, ProductAPIRequest

StartResponse = Callable[[str, List[Tuple[str, str]]], object]

_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def _request_headers(environ: Mapping[str, object]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for key, value in environ.items():
        if not isinstance(value, str):
            continue
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").title()
            headers[name] = value
    if isinstance(environ.get("CONTENT_TYPE"), str):
        headers["Content-Type"] = str(environ["CONTENT_TYPE"])
    return headers


class ProductAPIWSGI:
    """Expose :class:`ProductAPIApplication` through a synchronous WSGI boundary."""

    def __init__(self, application: ProductAPIApplication) -> None:
        self.application = application

    def __call__(self, environ: Mapping[str, object], start_response: StartResponse) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        response = self.application.handle(
            ProductAPIRequest(method=method, path=path, headers=_request_headers(environ))
        )
        status_text = _STATUS_TEXT.get(response.status_code, "Unknown")
        headers = list(response.headers.items())
        headers.append(("Content-Length", str(len(response.body))))
        start_response(f"{response.status_code} {status_text}", headers)
        return [response.body]
