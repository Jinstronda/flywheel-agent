"""The MCP tool surface. On the graded run the real AppWorld APIs reach your agent through five
JSON-RPC tools at FLYWHEEL_MCP_URL:

  search_apis(query)
  api_doc(app, api)
  call_api(app, api, arguments)
  run_code(code)              run python with `apis` in scope (loops/pagination/bulk); see ctx.run_code
  complete_task(answer=None)

You log in in-band: use call_api on supervisor.show_account_passwords and supervisor.show_profile,
then call_api on the target app's login API and thread the returned access_token through authed
calls.

Every tools/call is traced by the gateway, and that is what the gate counts,
so acting through here (not hardcoded HTTP) is load-bearing.
"""
import json
import urllib.request


class MCP:
    def __init__(self, url, trace):
        self.url = (url or "").rstrip("/")
        self._t = trace
        self._id = 0

    def _rpc(self, method, params):
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.url, data=body,
                                     headers={"content-type": "application/json", "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def list(self):
        return self._rpc("tools/list", {}).get("result", {}).get("tools", [])

    def call(self, name, args=None):
        self._t("tool", name=name)
        return self._rpc("tools/call", {"name": name, "arguments": args or {}}).get("result")
