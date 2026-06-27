# The model proxy

The proxy exposes one fixed model, `gemini-3-flash-preview`, through an OpenAI-compatible API.
Everyone uses the same model. Your agent quality is the variable.

Connect with the OpenAI client or raw HTTP. Put `FLYWHEEL_KEY` in the Authorization header as a Bearer token.

## Endpoint

```bash
curl https://homodeus-flywheel.fly.dev/v1/chat/completions \
  -H "authorization: Bearer $FLYWHEEL_KEY" \
  -H "content-type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi"}]}'
```

On the graded run the base URL is `FLYWHEEL_PROXY_URL`, which already ends in `/v1`, so the full path is `$FLYWHEEL_PROXY_URL/chat/completions` (do not append another `/v1`). Locally you set `FLYWHEEL_URL` (no `/v1`) and the SDK appends `/v1` for you.

The proxy injects the model name. You can omit `model`; if you send one, the proxy replaces it.

Function calling (`tools`) and `response_format` are supported.

Gemini responses carry `extra_content.google.thought_signature`; in multi-turn function-calling, echo the assistant message (with its `tool_calls`) back verbatim and do not strip it, or the next turn can fail.

Do not send `max_tokens` or `max_completion_tokens`. The proxy strips token caps so every candidate gets the same model policy.

## Budget

Each key is metered. The response header `x-flywheel-tokens-remaining` tells you what is left after each call. When you are out, calls fail with HTTP 429.

The proxy is the only model endpoint. There is no other model.
