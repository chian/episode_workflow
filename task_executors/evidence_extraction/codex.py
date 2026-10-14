"""Text-only Codex Responses client using the current Codex CLI login.

The CLI owns refresh-token rotation. This client reads only its current access
token and fails closed if it expires, so it cannot invalidate the CLI session.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .._http import ProviderError, _http_error_detail


_CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def _access_token() -> tuple[str, dict]:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    try:
        auth = json.loads((home / "auth.json").read_text(encoding="utf-8"))
        if auth.get("auth_mode") != "chatgpt":
            raise ValueError("Codex is not signed in with ChatGPT")
        token = auth["tokens"]["access_token"]
        if not isinstance(token, str) or not token:
            raise ValueError("Codex access token is missing")
        encoded = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if float(claims.get("exp", 0)) <= time.time() + 120:
            raise ValueError("Codex access token has expired; refresh the Codex login")
        account = claims.get("https://api.openai.com/auth", {})
        if not isinstance(account, dict):
            raise ValueError("Codex access token has invalid account claims")
        return token, account
    except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Codex login is unavailable: {exc}") from exc


@dataclass(frozen=True)
class CodexOAuthClient:
    model: str
    timeout: float = 300.0
    reasoning_effort: str = "medium"

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Codex model must be a non-empty string")
        if (isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float))
                or not math.isfinite(self.timeout) or self.timeout <= 0):
            raise ValueError("Codex timeout must be positive and finite")
        if self.reasoning_effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Codex reasoning effort is invalid")

    def call(self, prompt: str, system_prompt: str | None = None, *,
             model: str | None = None, reasoning_effort: str | None = None) -> str:
        model = model or self.model
        effort = reasoning_effort or self.reasoning_effort
        if effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Codex reasoning effort is invalid")
        token, account = _access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "episodic-workflow/0.1",
            "originator": "episodic-workflow",
        }
        if account.get("chatgpt_account_id"):
            headers["ChatGPT-Account-ID"] = account["chatgpt_account_id"]
        residency = account.get("chatgpt_data_residency") or account.get("chatgpt_compute_residency")
        if residency:
            headers["x-openai-internal-codex-residency"] = residency
        payload = {
            "model": model,
            "instructions": system_prompt or "Return a direct text answer to the user's request.",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            "store": False,
            "stream": True,
            "reasoning": {"effort": effort},
        }
        request = Request(_CODEX_RESPONSES_URL,
            data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
            headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                chunks, completed = [], False
                deadline = time.monotonic() + self.timeout
                stream_bytes = 0
                for line in response:
                    stream_bytes += len(line)
                    if time.monotonic() >= deadline:
                        raise ProviderError("Codex response exceeded the request time limit")
                    if stream_bytes > 4 * 1024 * 1024:
                        raise ProviderError("Codex response stream exceeded 4 MiB")
                    if not line.startswith(b"data: "):
                        continue
                    try:
                        event = json.loads(line[6:])
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ProviderError("Codex returned an invalid response event") from exc
                    kind = event.get("type")
                    if kind == "response.output_text.delta":
                        delta = event.get("delta")
                        if not isinstance(delta, str):
                            raise ProviderError("Codex returned a non-text output delta")
                        chunks.append(delta)
                    elif kind == "response.completed":
                        completed = event.get("response", {}).get("status") == "completed"
                        break
                    elif kind in {"response.failed", "response.incomplete"}:
                        raise ProviderError(f"Codex response did not complete: {kind}")
        except HTTPError as exc:
            detail = _http_error_detail(exc, token)
            raise ProviderError(f"Codex returned HTTP {exc.code}" + (f": {detail}" if detail else "")) from exc
        except (URLError, OSError) as exc:
            raise ProviderError(f"Codex connection failed: {exc}") from exc
        if not completed:
            raise ProviderError("Codex response stream ended without completion")
        result = "".join(chunks)
        if not result.strip():
            raise ProviderError("Codex response contained no text")
        return result

    async def call_async(self, prompt: str, system_prompt: str | None = None) -> str:
        return await asyncio.to_thread(self.call, prompt, system_prompt)
