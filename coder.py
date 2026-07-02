"""
coder.py — Claude API integration core
AI Model Coder CLI v1.7.0
"""
import os
import json
import urllib.request
import urllib.error
from config import Config
from utils import sampling_kwargs


class Coder:
    def __init__(self, api_key=None, model=None, temperature=0.3, max_tokens=4096,
                 provider=None, personality_style=None,
                 service_tier=None, inference_geo=None, fast_mode=False):
        self.config = Config()
        self.api_key = api_key or self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or self.config.get("model") or "claude-sonnet-5"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider or "anthropic"
        self.personality_style = personality_style
        # service_tier: "auto" (use Priority Tier if committed, else fall
        # back to standard) or "standard_only". Not sent unless set — most
        # accounts have no Priority Tier commitment (they're no longer
        # purchasable, only existing commitments still work) and it's
        # rejected outright on Sonnet 5 / Mythos-tier models.
        self.service_tier = service_tier
        # inference_geo: "us" (US-only inference, 1.1x pricing) or "global"
        # (default). Only Opus 4.6+/Sonnet 4.6+ and later accept this param
        # at all — earlier models 400 if it's set.
        self.inference_geo = inference_geo
        # fast_mode: sends speed:"fast" — reduced-latency mode, currently a
        # research-preview feature restricted to certain Opus models and
        # billed at a premium rate. See claude_models.py FAST_MODE_SUPPORTED.
        self.fast_mode = fast_mode

    def generate(self, prompt, system=None, file_content=None, history=None):
        """Generate a response from the AI model."""
        if not self.api_key:
            return "[ERROR] No API key configured. Set ANTHROPIC_API_KEY or run --setup."

        messages = list(history or [])

        user_content = prompt
        if file_content:
            user_content = f"File content:\n```\n{file_content}\n```\n\n{prompt}"

        if self.personality_style:
            try:
                from personalities import PersonalityManager
                pm = PersonalityManager()
                addition = pm.build_prompt_addition(self.personality_style)
                if addition and system:
                    system = system + "\n\n" + addition
                elif addition:
                    system = addition
            except Exception:
                pass

        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
            # Was accepted in __init__ but never sent — dead code. Now sent,
            # guarded by sampling_kwargs() since Sonnet 5/Fable 5/Mythos 5
            # 400 on any explicit sampling param.
            **sampling_kwargs(self.model, temperature=self.temperature),
        }
        if system:
            payload["system"] = system
        if self.service_tier:
            payload["service_tier"] = self.service_tier
        if self.inference_geo:
            payload["inference_geo"] = self.inference_geo
        if self.fast_mode:
            payload["speed"] = "fast"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                # Was `data["content"][0]["text"]` — broke (wrong text, or a
                # KeyError/IndexError outright) whenever content[0] wasn't a
                # plain text block: thinking-capable models (Sonnet 5, Opus
                # 4.8, Fable 5/Mythos 5 — Fable 5 has thinking on by default,
                # see claude_fable5.py) can return a thinking block first,
                # and any response with >1 text block silently dropped every
                # block after the first. Concatenate every text block instead,
                # matching the pattern already used in claude_models.py /
                # claude_fable5.py / claude_mythos5.py.
                content = data.get("content", [])
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
                if not text and data.get("stop_reason") == "refusal":
                    return "[REFUSED] Model declined this request."
                return text
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return f"[API ERROR {e.code}] {body}"
        except Exception as e:
            return f"[ERROR] {e}"