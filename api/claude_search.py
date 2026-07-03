"""
claude_search.py — Web Search & Web Fetch (Anthropic server tools)
AI Model Coder CLI v1.8.0

Enables Claude to search the web and fetch URLs in real-time.

CLI flags:
  --web-search            Enable web search tool
  --web-fetch             Enable web fetch tool
  --search-query Q        Shorthand: ask Claude about Q with web search on
  --fetch-url URL         Ask Claude to summarise a URL
  --max-searches N        Max web_search calls per turn (default 5)
  --citations             Show source citations in output
"""

import sys
import json
import anthropic
from typing import Optional


WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}

WEB_FETCH_TOOL = {
    "type": "web_fetch_20250124",
    "name": "web_fetch",
}


class SearchCoder:
    """Claude with web search and fetch tools."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
                 max_tokens: int = 4096):
        self.client     = anthropic.Anthropic(api_key=api_key)
        self.model      = model
        self.max_tokens = max_tokens

    def search(
        self,
        prompt: str,
        system: Optional[str] = None,
        web_search: bool = True,
        web_fetch: bool = False,
        max_searches: int = 5,
        show_citations: bool = True,
    ) -> dict:
        """Run prompt with web search / fetch tools enabled."""
        tools = []
        if web_search:
            t = dict(WEB_SEARCH_TOOL)
            t["max_uses"] = max_searches
            tools.append(t)
        if web_fetch:
            tools.append(WEB_FETCH_TOOL)

        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
        )
        if system:
            kwargs["system"] = system

        resp = self.client.messages.create(**kwargs)

        response_text = ""
        citations     = []
        searches_made = 0

        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                response_text += block.text
            elif btype == "server_tool_use" and block.name == "web_search":
                searches_made += 1
            elif btype == "web_search_tool_result":
                for item in getattr(block, "content", []):
                    if getattr(item, "type", "") == "web_search_result":
                        citations.append({
                            "title": getattr(item, "title", ""),
                            "url":   getattr(item, "url", ""),
                        })

        usage = resp.usage.model_dump() if hasattr(resp.usage, "model_dump") else {}

        return {
            "response":     response_text,
            "citations":    citations,
            "searches":     searches_made,
            "usage":        usage,
            "stop_reason":  resp.stop_reason,
        }

    def fetch_and_summarise(self, url: str, instruction: str = "") -> str:
        """Fetch a URL and summarise / answer from its content."""
        prompt = f"Please fetch and read this URL, then {instruction or 'summarise the key points'}: {url}"
        result = self.search(prompt, web_search=False, web_fetch=True)
        return result["response"]


# ── CLI entry points ───────────────────────────────────────────────────────

def cmd_web_search(prompt: str, api_key: str, model: str,
                   max_searches: int = 5, show_citations: bool = True,
                   web_fetch: bool = False):
    print(f"\033[94mℹ Web Search enabled | max_searches={max_searches}\033[0m\n")
    sc = SearchCoder(api_key=api_key, model=model)
    result = sc.search(
        prompt,
        web_search=True,
        web_fetch=web_fetch,
        max_searches=max_searches,
        show_citations=show_citations,
    )
    print(result["response"])
    if show_citations and result["citations"]:
        print(f"\n\033[90m── Sources ({'─'*30})\033[0m")
        for i, c in enumerate(result["citations"], 1):
            print(f"\033[90m[{i}] {c['title']}\n    {c['url']}\033[0m")
    u = result.get("usage", {})
    searches = result.get("searches", 0)
    print(f"\n\033[90m[searches={searches}  input={u.get('input_tokens',0)}  output={u.get('output_tokens',0)}]\033[0m")
    return result["response"]


def cmd_fetch_url(url: str, instruction: str, api_key: str, model: str):
    print(f"\033[94mℹ Fetching: {url}\033[0m\n")
    sc = SearchCoder(api_key=api_key, model=model)
    result = sc.fetch_and_summarise(url, instruction)
    print(result)
    return result