# Product API Migration Feature Matrix

| Surface | Product API client | Provider credentials | Status | Evidence |
|---|---|---|---|---|
| `zai-coder-api` prompt | Yes | None | Delivered | `tests/test_product_api_cli.py` |
| `zai-coder-api` streaming | Yes | None | Delivered | `tests/test_product_api_cli.py`, `tests/test_live_stream_client.py` |
| `zai-coder-api` request context and diagnostics | Yes | None | Delivered | `tests/test_product_api_cli.py`, `tests/test_product_api_client.py` |
| TUI chat | Yes | None | Delivered | `tests/test_tui_product_api_migration.py` |
| Legacy `main.py` prompt/chat | No | Legacy provider configuration | Deferred | Phase 6.2b |
| Web and automation | Not yet | Not yet | Pending | Phase 6.3 |

The delivered Product API CLI paths import no provider SDK and read no
provider credential. Product API access tokens are configured server-facing
through `ZAICODER_ACCESS_TOKEN` and are never emitted by diagnostics.
