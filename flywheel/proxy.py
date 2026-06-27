"""The model proxy. OpenAI-compatible, pinned to gemini-3-flash-preview server-side.

Your FLYWHEEL_KEY goes in the Authorization header. The model and temperature are fixed on
the server (you can't swap them, that's the point), so never send `model` or `max_tokens`.
Function-calling (`tools`) and structured output (`response_format`) both work. See docs/proxy.md.
"""
import json
import urllib.error
import urllib.request

TIMEOUT = 120


def chat(url, key, messages, tools=None, response_format=None, tool_choice=None, retries=2):
    """One call to /v1/chat/completions. Returns (data, remaining_tokens).

    `data` is the raw OpenAI-shaped response dict; on a hard failure it is {"error": "..."}.
    `remaining_tokens` is the x-flywheel-tokens-remaining header (your metered budget), or None.
    """
    payload = {"messages": messages}
    if tools:
        payload["tools"] = tools
    if tool_choice:
        payload["tool_choice"] = tool_choice
    if response_format:
        payload["response_format"] = response_format
    body = json.dumps(payload).encode()
    headers = {"content-type": "application/json", "authorization": f"Bearer {key}"}
    endpoint = url.rstrip("/") + "/chat/completions"
    last_err = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(endpoint, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read())
                remaining = r.headers.get("x-flywheel-tokens-remaining")
                return data, (int(remaining) if remaining is not None else None)
        except urllib.error.HTTPError as e:
            last_err = f"http {e.code}: {e.read()[:300]!r}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = str(e)
    return {"error": last_err or "proxy call failed"}, None


def content_of(data):
    """Pull the assistant text out of an OpenAI response, '' if absent."""
    if not isinstance(data, dict) or data.get("error"):
        return ""
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
