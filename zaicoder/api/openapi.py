"""Deterministic OpenAPI contract for the initial Product API surface."""

from __future__ import annotations

from typing import Any, Dict


def build_openapi_schema(product_version: str = "1.23.0") -> Dict[str, Any]:
    success_response = {
        "200": {
            "description": "Successful response",
            "headers": {
                "X-Request-ID": {"schema": {"type": "string"}},
                "X-Correlation-ID": {"schema": {"type": "string"}},
                "X-API-Version": {"schema": {"type": "string"}},
            },
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    }
    paths: Dict[str, Any] = {}
    for path, summary in (
        ("/v1/health", "Health check"),
        ("/v1/live", "Liveness check"),
        ("/v1/ready", "Readiness check"),
        ("/v1/version", "Product and API version"),
        ("/v1/models", "Provider-neutral model catalog"),
    ):
        paths[path] = {
            "get": {
                "summary": summary,
                "operationId": path.removeprefix("/v1/").replace("/", "_") if hasattr(str, "removeprefix") else path[4:].replace("/", "_"),
                "responses": success_response,
            }
        }
    paths["/v1/ready"]["get"]["responses"] = {
        **success_response,
        "503": {"$ref": "#/components/responses/ProductError"},
    }
    paths["/v1/models"]["get"].update(
        {
            "security": [{"bearerAuth": []}],
            "responses": {
                **success_response,
                "401": {"$ref": "#/components/responses/ProductError"},
                "403": {"$ref": "#/components/responses/ProductError"},
            },
        }
    )
    generation_request = {
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GenerationRequest"}}},
    }
    generation_errors = {
        "401": {"$ref": "#/components/responses/ProductError"},
        "403": {"$ref": "#/components/responses/ProductError"},
        "422": {"$ref": "#/components/responses/ProductError"},
        "502": {"$ref": "#/components/responses/ProductError"},
        "503": {"$ref": "#/components/responses/ProductError"},
    }
    paths["/v1/messages"] = {
        "post": {
            "summary": "Generate an assistant message",
            "operationId": "create_message",
            "security": [{"bearerAuth": []}],
            "requestBody": generation_request,
            "responses": {**success_response, **generation_errors},
        }
    }
    paths["/v1/messages:stream"] = {
        "post": {
            "summary": "Stream canonical message events",
            "operationId": "stream_message",
            "security": [{"bearerAuth": []}],
            "requestBody": generation_request,
            "responses": {
                "200": {
                    "description": "Canonical server-sent event stream",
                    "content": {"text/event-stream": {"schema": {"type": "string"}}},
                },
                **generation_errors,
            },
        }
    }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "ZAI Coder Product API",
            "version": product_version,
            "description": "Provider-neutral Product API contract.",
        },
        "servers": [{"url": "/"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "opaque product access token",
                }
            },
            "schemas": {
                "GenerationRequest": {
                    "type": "object",
                    "required": ["model", "messages"],
                    "properties": {
                        "model": {"type": "string", "minLength": 1},
                        "messages": {"type": "array", "minItems": 1, "items": {"type": "object"}},
                        "max_output_tokens": {"type": "integer", "minimum": 1, "default": 1024},
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                },
                "ProductError": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {
                            "type": "object",
                            "required": ["code", "message", "request_id", "correlation_id", "retryable", "details"],
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "request_id": {"type": "string"},
                                "correlation_id": {"type": "string"},
                                "retryable": {"type": "boolean"},
                                "details": {"type": "object", "additionalProperties": True},
                            },
                        }
                    },
                },
            },
            "responses": {
                "ProductError": {
                    "description": "Typed Product API error",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProductError"}}},
                }
            },
        },
    }
