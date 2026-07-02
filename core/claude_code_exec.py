"""
claude_code_exec.py — Code Execution Tool (beta)
AI Model Coder CLI v1.8.0

Let Claude write AND run Python code in a secure Anthropic-hosted sandbox.
Results (stdout, files, images) are returned inline.

Claude can:
  • Generate data, process CSVs, run calculations
  • Create files (Excel, PDFs, charts) returned as file_id
  • Debug code by running it
  • Build and test algorithms on the fly

CLI flags:
  --code-exec PROMPT       Ask Claude to write and run code for this task
  --code-exec-file FILE    Attach a file to the code execution sandbox
  --code-exec-lang LANG    Hint the programming language (default: python)
  --code-exec-output DIR   Save any output files to this directory
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


ENDPOINT    = "https://api.anthropic.com/v1/messages"
BETA_HEADER = "code-execution-2025-05-22"

CODE_EXEC_TOOL = {
    "type": "code_execution_20250522",
    "name": "code_execution",
}


class CodeExecutionCoder:
    """Claude client with server-side code execution."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
                 max_tokens: int = 8192):
        self.api_key    = api_key
        self.model      = model
        self.max_tokens = max_tokens

    def _post(self, payload: dict) -> dict:
        headers = {
            "Content-Type":      "application/json",
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    BETA_HEADER,
        }
        req = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode(), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def execute(
        self,
        prompt: str,
        system: Optional[str] = None,
        file_ids: list[str] = None,
        output_dir: Optional[str] = None,
    ) -> dict:
        """
        Ask Claude to write and run code.
        Returns {"text": str, "outputs": list, "files": list}
        """
        content = [{"type": "text", "text": prompt}]

        # Attach uploaded files to the sandbox
        for fid in (file_ids or []):
            content.append({
                "type":    "document",
                "source":  {"type": "file", "file_id": fid},
            })

        messages = [{"role": "user", "content": content}]
        payload: dict = {
            "model":      self.model,
            "max_tokens": self.max_tokens,
            "tools":      [CODE_EXEC_TOOL],
            "messages":   messages,
        }
        if system:
            payload["system"] = system

        data  = self._post(payload)
        if "error" in data:
            return {"text": f"[ERROR] {data['error']}", "outputs": [], "files": []}

        text    = ""
        outputs = []
        files   = []

        for block in data.get("content", []):
            btype = block.get("type", "")

            if btype == "text":
                text += block.get("text", "")

            elif btype == "tool_use" and block.get("name") == "code_execution":
                outputs.append({
                    "type":  "code",
                    "input": block.get("input", {}).get("code", ""),
                })

            elif btype == "tool_result":
                for sub in block.get("content", []):
                    st = sub.get("type", "")
                    if st == "text":
                        outputs.append({"type": "stdout", "text": sub.get("text", "")})
                    elif st == "image":
                        img_data = sub.get("source", {}).get("data", "")
                        img_type = sub.get("source", {}).get("media_type", "image/png")
                        files.append({"type": "image", "data": img_data, "media_type": img_type})
                        outputs.append({"type": "image_output", "media_type": img_type})

            elif btype == "server_tool_use":
                # code_execution block
                code = block.get("input", {}).get("code", "")
                if code:
                    outputs.append({"type": "executed_code", "code": code})

            elif btype == "server_tool_result":
                for sub in block.get("content", []):
                    st = sub.get("type", "")
                    if st == "text":
                        outputs.append({"type": "stdout", "text": sub.get("text", "")})
                    elif st == "image":
                        img_data = sub.get("source", {}).get("data", "")
                        img_mt   = sub.get("source", {}).get("media_type", "image/png")
                        files.append({"type": "image", "data": img_data, "media_type": img_mt})
                        if output_dir:
                            ext = img_mt.split("/")[-1]
                            p   = Path(output_dir) / f"output_{len(files)}.{ext}"
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_bytes(base64.b64decode(img_data))
                            print(f"  \033[92m✓ Image saved: {p}\033[0m")

        return {"text": text, "outputs": outputs, "files": files,
                "usage": data.get("usage", {})}

    def debug_code(self, code: str, language: str = "python") -> dict:
        """Ask Claude to debug and fix code by running it."""
        prompt = (
            f"Debug this {language} code. Run it, find errors, fix them, "
            f"and show the working version:\n\n```{language}\n{code}\n```"
        )
        return self.execute(prompt, system="You are an expert debugger. Run the code and fix all errors.")

    def analyse_data(self, csv_path: str, question: str) -> dict:
        """Upload a CSV and analyse it with code execution."""
        code = Path(csv_path).read_text()
        prompt = (
            f"Analyse this CSV data and answer: {question}\n\n"
            f"CSV content:\n```\n{code[:10000]}\n```\n\n"
            "Write Python code to load and analyse the data, then answer the question."
        )
        return self.execute(prompt)


# ── CLI entry points ───────────────────────────────────────────────────────

def cmd_code_exec(prompt: str, api_key: str, model: str,
                  file_ids: list[str] = None, output_dir: str = None):
    print(f"\033[94mℹ Code Execution Tool (Anthropic sandbox)\033[0m\n")
    cec    = CodeExecutionCoder(api_key=api_key, model=model)
    result = cec.execute(prompt, file_ids=file_ids, output_dir=output_dir)

    print(result["text"])

    if result["outputs"]:
        print(f"\n\033[90m── Execution Trace ─────────────────────\033[0m")
        for out in result["outputs"]:
            ot = out.get("type", "")
            if ot in ("code", "executed_code"):
                print(f"\033[36m[code]\033[0m {out.get('code','')[:200]}")
            elif ot == "stdout":
                print(f"\033[37m[out]  {out.get('text','')[:200]}\033[0m")
            elif ot == "image_output":
                print(f"\033[35m[img]  {out.get('media_type','')}\033[0m")

    u = result.get("usage", {})
    if u:
        print(f"\n\033[90m[tokens] in={u.get('input_tokens',0)}  out={u.get('output_tokens',0)}\033[0m")

    return result


def cmd_code_debug(file_path: str, api_key: str, model: str):
    code = Path(file_path).read_text()
    lang = Path(file_path).suffix.lstrip(".") or "python"
    print(f"\033[94mℹ Debugging {file_path} with live execution…\033[0m\n")
    cec    = CodeExecutionCoder(api_key=api_key, model=model)
    result = cec.debug_code(code, lang)
    print(result["text"])
    return result
