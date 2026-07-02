"""
claude_fable5.py — Claude Fable 5 / Claude Mythos 5 support
AI Model Coder CLI v1.9.1

IMPORTANT — confidence note: the details below (pricing, context window,
refusal/fallback mechanics, availability) are taken from web search results
describing an Anthropic announcement (~June 9, 2026) of Claude Fable 5 and
Claude Mythos 5 as a new "Mythos-class" model generation. This CLI has no
independent way to verify pricing or availability against Anthropic's live
systems beyond what the API itself reports at call time, and this module's
constants can go stale exactly like claude_models.py's offline fallback
list already does for earlier model generations. Before relying on any
number below for billing-sensitive decisions, confirm against
https://platform.claude.com/docs and your own Anthropic Console.

UPDATE (2026-07-02): access to both models was briefly suspended
2026-06-12 through 2026-06-30 to comply with US Department of Commerce
export controls, then restored 2026-07-01 once those controls were
lifted. If a call to either model ID returns an access-denied error,
that is now more likely an account/region permissions issue than a
typo — see https://www.anthropic.com/news/fable-mythos-access.

What this module adds, concretely:
  • Model ID constants + a small info table (context window, output cap,
    pricing, retention requirement) for claude-fable-5 / claude-mythos-5,
    following the same "known models" convention as claude_models.py.
  • Refusal-aware calling: Claude Fable 5 is documented to include safety
    classifiers that can decline a request via stop_reason == "refusal"
    (returned as a normal 200 response, not an HTTP error) rather than a
    silent failure. Claude Mythos 5 does not include these classifiers
    (limited-availability access only — most callers will not have it).
  • Optional client-side fallback: on a refusal, this module can retry the
    same prompt against a fallback model (default: claude-opus-4-8, since
    that's the most capable model this CLI's own static fallback list
    already lists — adjust via --fallback-model once you know your
    account's actual best available model).

CLI flags:
  --fable5-info                Show what's known about Fable 5 / Mythos 5
  --fable5 PROMPT               Call Claude Fable 5 with refusal/fallback handling
  --fable5-no-fallback           Disable automatic fallback on refusal (just report it)
  --fallback-model ID            Override the fallback model (default: claude-opus-4-8)
"""

import json
import urllib.request
import urllib.error
from typing import Optional

MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"

FABLE5_MODEL_ID = "claude-fable-5"
MYTHOS5_MODEL_ID = "claude-mythos-5"

# Mirrors claude_models.py's "known models" fallback pattern — a local
# cache for when the live Models API isn't consulted, not a source of truth.
FABLE_MYTHOS_INFO = {
    FABLE5_MODEL_ID: {
        "display_name": "Claude Fable 5",
        "class": "Mythos-class (publicly available)",
        "context_window": 1_000_000,
        "max_output_tokens": 128_000,
        "price_input_per_mtok_usd": 10.0,
        "price_output_per_mtok_usd": 50.0,
        "cache_write_discount_note": "90% input-token discount applies for prompt caching, per Anthropic's standard caching pricing",
        "data_retention": "30-day retention required for safety monitoring; not available under zero data retention",
        "has_safety_classifiers": True,
        "us_only_inference_multiplier": 1.1,
        "notes": "Refuses certain cybersecurity/biology/chemistry queries via stop_reason='refusal' "
                "and can fall back to a less-restricted model server-side (beta `fallbacks` param) "
                "or client-side (this module's call_with_fallback).",
    },
    MYTHOS5_MODEL_ID: {
        "display_name": "Claude Mythos 5",
        "class": "Mythos-class (limited availability — Project Glasswing)",
        "context_window": 1_000_000,
        "max_output_tokens": 128_000,
        "price_input_per_mtok_usd": 10.0,
        "price_output_per_mtok_usd": 50.0,
        "cache_write_discount_note": "90% input-token discount applies for prompt caching, per Anthropic's standard caching pricing",
        "data_retention": "30-day retention required; not available under zero data retention",
        "has_safety_classifiers": False,
        "us_only_inference_multiplier": None,
        "notes": "Same underlying capability as Fable 5 without the safety classifiers. "
                "Requires approved access via Project Glasswing — contact your Anthropic, "
                "AWS, or Google Cloud account team. Most callers will not have this and "
                "should use Fable 5 instead.",
    },
}


class RefusalError(Exception):
    """Raised when a Fable 5 call is refused and fallback is disabled/exhausted."""
    def __init__(self, message: str, category: Optional[str] = None, explanation: Optional[str] = None):
        super().__init__(message)
        self.category = category
        self.explanation = explanation


class Fable5Client:
    """Thin Messages API client with refusal detection and optional fallback,
    following the same _post() pattern used throughout this project's other
    claude_*.py modules for consistency."""

    def __init__(self, api_key: str, model: str = FABLE5_MODEL_ID,
                 fallback_model: str = "claude-opus-4-8", max_tokens: int = 4096):
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.max_tokens = max_tokens

    def _post(self, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        req = urllib.request.Request(
            MESSAGES_ENDPOINT, data=json.dumps(payload).encode(),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def _extract_text(self, data: dict) -> str:
        return "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )

    def call(self, prompt: str, system: Optional[str] = None,
             model: Optional[str] = None) -> dict:
        """One raw call. Returns the parsed response dict (caller inspects stop_reason)."""
        payload = {
            "model": model or self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        return self._post(payload)

    def call_with_fallback(self, prompt: str, system: Optional[str] = None,
                           allow_fallback: bool = True) -> dict:
        """
        Call the configured model; if the response is refused
        (stop_reason == 'refusal'), optionally retry against
        self.fallback_model, mirroring Anthropic's documented client-side
        retry pattern. Returns a dict:
          {text, stop_reason, refused: bool, fell_back: bool, category: str|None, explanation: str|None, raw}
        """
        data = self.call(prompt, system=system)
        if "error" in data:
            return {"text": f"[ERROR] {data['error']}", "stop_reason": None,
                   "refused": False, "fell_back": False, "category": None,
                   "explanation": None, "raw": data}

        stop_reason = data.get("stop_reason")
        refused = stop_reason == "refusal"
        
        # Extract stop_details
        stop_details = (data.get("stop_details") or {}) if refused else {}
        category = stop_details.get("category")
        explanation = stop_details.get("explanation")

        if refused and allow_fallback:
            fallback_data = self.call(prompt, system=system, model=self.fallback_model)
            if "error" in fallback_data:
                return {"text": f"[ERROR on fallback] {fallback_data['error']}",
                       "stop_reason": stop_reason, "refused": True, "fell_back": False,
                       "category": category, "explanation": explanation, "raw": data}
            return {"text": self._extract_text(fallback_data),
                   "stop_reason": fallback_data.get("stop_reason"),
                   "refused": True, "fell_back": True, "category": category,
                   "explanation": explanation, "raw": fallback_data}

        if refused:
            raise RefusalError(
                f"Claude Fable 5 declined this request (category: {category or 'unspecified'}, explanation: {explanation or 'none'}). "
                "Re-run with fallback enabled, or use claude-opus-4-8 directly.",
                category=category,
                explanation=explanation
            )

        return {"text": self._extract_text(data), "stop_reason": stop_reason,
               "refused": False, "fell_back": False, "category": None,
               "explanation": None, "raw": data}


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Rough cost estimate using the static table above. Returns None for unknown models."""
    info = FABLE_MYTHOS_INFO.get(model_id)
    if not info:
        return None
    return (input_tokens / 1_000_000 * info["price_input_per_mtok_usd"] +
            output_tokens / 1_000_000 * info["price_output_per_mtok_usd"])


def cmd_fable5_info():
    print("\n\033[94mClaude Fable 5 / Claude Mythos 5\033[0m")
    print("\033[93m⚠ Sourced from recent web search results, not this CLI's own bundled\033[0m")
    print("\033[93m  product data — verify at platform.claude.com/docs before relying on\033[0m")
    print("\033[93m  pricing/availability for anything billing-sensitive.\033[0m\n")
    for model_id, info in FABLE_MYTHOS_INFO.items():
        print(f"  \033[1m{info['display_name']}\033[0m  ({model_id})")
        print(f"    Class:            {info['class']}")
        print(f"    Context window:   {info['context_window']:,} tokens")
        print(f"    Max output:       {info['max_output_tokens']:,} tokens")
        print(f"    Pricing:          ${info['price_input_per_mtok_usd']}/MTok in, "
             f"${info['price_output_per_mtok_usd']}/MTok out")
        print(f"    Data retention:   {info['data_retention']}")
        print(f"    Safety classifiers: {'yes (can refuse, see fallback)' if info['has_safety_classifiers'] else 'no'}")
        print(f"    Notes:            {info['notes']}")
        print()


def cmd_fable5_call(prompt: str, api_key: str, fallback_model: str = "claude-opus-4-8",
                    allow_fallback: bool = True, system: Optional[str] = None):
    client = Fable5Client(api_key=api_key, fallback_model=fallback_model)
    try:
        result = client.call_with_fallback(prompt, system=system, allow_fallback=allow_fallback)
    except RefusalError as e:
        print(f"\033[91m✗ {e}\033[0m")
        return None

    if result["fell_back"]:
        print(f"\033[93mℹ Fable 5 declined this request (category: {result['category'] or 'unspecified'}, "
             f"explanation: {result['explanation'] or 'none'}); "
             f"showing the {fallback_model} response instead.\033[0m\n")
    print(result["text"])
    return result