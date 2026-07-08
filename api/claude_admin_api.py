"""
claude_admin_api.py — Admin API: Usage & Cost reporting + API key management
AI Model Coder CLI v1.15.0

Two thin Admin API wrappers, combined into one module since both require
the same auth (an Admin API key, prefix sk-ant-admin..., created in the
Console — this is a different key type than the regular API key used
everywhere else in this CLI, and these calls will 401 with a normal key).

  1. Usage and Cost API — org-level historical spend/usage reporting.
     `claude_cost_optimizer.py` only ever *estimates* cost locally from
     token counts it's told about after the fact; it never calls a real
     usage/cost endpoint. This module is that missing live-data path —
     see claude_cost_optimizer.py's docstring for the cross-link the other
     direction.

  2. API key management — list/update organization API keys. Anthropic
     does not document a create-key endpoint: keys are created through
     the Console UI, where the secret is displayed exactly once, and
     that's intentional (creating a raw secret programmatically would be
     an exfiltration/security risk). So this module implements list,
     get, and update (e.g. changing status to revoke a key) — not create.
     `--admin-create-key` is deliberately not implemented; see
     cmd_admin_create_key() below for why, rather than silently no-op-ing.

CLI flags:
  --usage-report                 Print a usage report table (token counts)
  --usage-report-start DATE       Start date (YYYY-MM-DD), default: 30 days ago
  --usage-report-end DATE         End date (YYYY-MM-DD), default: today
  --usage-report-group-by FIELD   Group by field, e.g. model, api_key_id (default: model)
  --cost-report                   Print a cost report table (billed spend, not token counts)
  --cost-report-start DATE        Start date (YYYY-MM-DD), default: 30 days ago
  --cost-report-end DATE          End date (YYYY-MM-DD), default: today
  --cost-report-group-by FIELD    Group by field, e.g. model, api_key_id (default: model)
  --admin-list-keys               List organization API keys
  --admin-revoke-key ID           Revoke (set status=inactive) an API key by ID
  --admin-create-key NAME         Explains why this isn't supported (Console-only)
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

ADMIN_BASE = "https://api.anthropic.com/v1/organizations"


class AdminApiError(Exception):
    pass


class AdminApiClient:
    """Thin client for the Admin API, following the same _post()/_get()
    pattern used throughout this project's claude_*.py modules.

    admin_api_key must be an Admin API key (sk-ant-admin...), not a
    regular API key — regular keys don't have access to this endpoint
    family and will get a 401/403.
    """

    def __init__(self, admin_api_key: str):
        self.admin_api_key = admin_api_key

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.admin_api_key,
            "anthropic-version": "2023-06-01",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{ADMIN_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{ADMIN_BASE}{path}", data=json.dumps(payload).encode(),
            headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    # ── Usage and Cost API ──────────────────────────────────────────────

    def get_usage_report(self, start: str, end: str, group_by: str = "model") -> dict:
        """Wraps the usage_report endpoint. start/end are YYYY-MM-DD."""
        return self._get("/usage_report", params={
            "starting_at": start, "ending_at": end, "group_by": group_by,
        })

    def get_cost_report(self, start: str, end: str, group_by: str = "model") -> dict:
        """Wraps the cost_report endpoint — actual billed spend, distinct
        from the token-count usage_report above."""
        return self._get("/cost_report", params={
            "starting_at": start, "ending_at": end, "group_by": group_by,
        })

    # ── API key management ──────────────────────────────────────────────

    def list_api_keys(self, limit: int = 20) -> dict:
        return self._get("/api_keys", params={"limit": limit})

    def get_api_key(self, key_id: str) -> dict:
        return self._get(f"/api_keys/{key_id}")

    def update_api_key(self, key_id: str, status: Optional[str] = None,
                       name: Optional[str] = None) -> dict:
        """status: 'active' or 'inactive'. There is no documented delete
        endpoint either — revocation is done via status, not deletion."""
        payload = {}
        if status:
            payload["status"] = status
        if name:
            payload["name"] = name
        return self._post(f"/api_keys/{key_id}", payload)

    def revoke_api_key(self, key_id: str) -> dict:
        return self.update_api_key(key_id, status="inactive")


def _default_date_range() -> tuple:
    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()


def cmd_usage_report(admin_api_key: str, start: Optional[str] = None,
                     end: Optional[str] = None, group_by: str = "model"):
    default_start, default_end = _default_date_range()
    start = start or default_start
    end = end or default_end
    client = AdminApiClient(admin_api_key)
    data = client.get_usage_report(start, end, group_by=group_by)
    if "error" in data:
        print(f"\033[91m✗ Usage report failed: {data['error']}\033[0m")
        if data.get("status") in (401, 403):
            print("\033[93m  This endpoint requires an Admin API key (sk-ant-admin...), "
                 "not a regular API key.\033[0m")
        return None

    print(f"\n\033[94mUsage report — {start} to {end} (grouped by {group_by})\033[0m\n")
    rows = data.get("data", data.get("results", []))
    if not rows:
        print("  (no usage data returned for this range)")
    for row in rows:
        label = row.get(group_by, row.get("model", "?"))
        input_tok = row.get("input_tokens", row.get("uncached_input_tokens", "?"))
        output_tok = row.get("output_tokens", "?")
        print(f"  {label:<28} in={input_tok:<12} out={output_tok}")
    print()
    return data


def cmd_cost_report(admin_api_key: str, start: Optional[str] = None,
                    end: Optional[str] = None, group_by: str = "model"):
    """--cost-report: actual billed spend (cost_report), distinct from
    the token-count-based --usage-report above. Mirrors cmd_usage_report
    one-for-one; get_cost_report() already existed on AdminApiClient but
    had no CLI flag wired to it until now."""
    default_start, default_end = _default_date_range()
    start = start or default_start
    end = end or default_end
    client = AdminApiClient(admin_api_key)
    data = client.get_cost_report(start, end, group_by=group_by)
    if "error" in data:
        print(f"\033[91m✗ Cost report failed: {data['error']}\033[0m")
        if data.get("status") in (401, 403):
            print("\033[93m  This endpoint requires an Admin API key (sk-ant-admin...), "
                 "not a regular API key.\033[0m")
        return None

    print(f"\n\033[94mCost report — {start} to {end} (grouped by {group_by})\033[0m\n")
    rows = data.get("data", data.get("results", []))
    if not rows:
        print("  (no cost data returned for this range)")
    for row in rows:
        label = row.get(group_by, row.get("model", "?"))
        amount = row.get("amount", row.get("cost", "?"))
        currency = row.get("currency", "usd")
        print(f"  {label:<28} {amount} {currency}")
    print()
    return data


def cmd_admin_list_keys(admin_api_key: str, limit: int = 20):
    client = AdminApiClient(admin_api_key)
    data = client.list_api_keys(limit=limit)
    if "error" in data:
        print(f"\033[91m✗ Failed to list API keys: {data['error']}\033[0m")
        if data.get("status") in (401, 403):
            print("\033[93m  This endpoint requires an Admin API key (sk-ant-admin...), "
                 "not a regular API key.\033[0m")
        return None

    print("\n\033[94mOrganization API keys\033[0m\n")
    for key in data.get("data", []):
        print(f"  {key.get('id', '?')}  {key.get('name', '')}  status={key.get('status', '?')}")
    print()
    return data


def cmd_admin_revoke_key(admin_api_key: str, key_id: str):
    client = AdminApiClient(admin_api_key)
    data = client.revoke_api_key(key_id)
    if "error" in data:
        print(f"\033[91m✗ Failed to revoke key {key_id}: {data['error']}\033[0m")
        return None
    print(f"\033[92m✓ Key {key_id} set to inactive\033[0m")
    return data


def cmd_admin_create_key(name: str):
    """--admin-create-key deliberately does not call an API — there is no
    documented create-key endpoint. Anthropic API keys are generated
    through the Console UI, where the secret is displayed exactly once;
    creating them programmatically isn't supported, almost certainly so a
    raw secret is never returned to a script that could log or leak it.
    This prints that explanation instead of silently failing or faking
    a response."""
    print(f"\033[93mℹ Can't create API key {name!r} via the Admin API — there is no "
         "documented create-key endpoint.\033[0m")
    print("  API keys are generated through the Console UI (a secret is shown once, "
         "on purpose). Use --admin-list-keys / --admin-revoke-key for the parts of "
         "key management that are actually supported programmatically.")
    return None