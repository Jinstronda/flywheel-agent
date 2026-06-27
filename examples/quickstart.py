"""Minimal AppWorld interaction to unstick you on the mechanics. NOT a solver: it logs in,
reads one API doc, pings the model, does a trivial action, calls complete_task, and prints
world.evaluate(). It will not necessarily PASS the task (that's your job in agent.py) -- it
proves the loop runs end to end.

  cp .env.example .env   # put your FLYWHEEL_KEY in, set APPWORLD_ROOT
  python examples/quickstart.py

What to copy into your agent: the login flow (the #1 gotcha) and that you MUST call
apis.supervisor.complete_task for the oracle to see anything. See docs/appworld.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flywheel.appworld_env import AppWorldEnv, load_task_ids
from flywheel.proxy import chat, content_of

PROXY_URL = os.environ.get("FLYWHEEL_URL", "https://homodeus-flywheel.fly.dev") + "/v1"


def main():
    os.environ.setdefault("APPWORLD_ROOT", os.environ.get("APPWORLD_ROOT", "./aw"))
    tid = load_task_ids("dev")[0]
    env = AppWorldEnv(tid, experiment_name="quickstart")
    t = env.task
    print(f"task {tid}")
    print(f"  instruction: {t.instruction}")
    print(f"  supervisor : {t.supervisor.first_name} {t.supervisor.last_name} <{t.supervisor.email}>")

    # 1) THE LOGIN FLOW: passwords + profile, then log into an app and read one of its docs.
    out = env.execute(
        "pw = {p['account_name']: p['password'] for p in apis.supervisor.show_account_passwords()}\n"
        "me = apis.supervisor.show_profile()\n"
        "tok = apis.spotify.login(username=me['email'], password=pw['spotify'])['access_token']\n"
        "print('logged in:', bool(tok))\n"
        "print('a spotify api:', apis.api_docs.show_api_descriptions(app_name='spotify')[0]['name'])"
    )
    print(f"\n[login + doc]\n{out.strip()}")

    # 2) the fixed model through the proxy (skipped if you haven't set FLYWHEEL_KEY)
    key = os.environ.get("FLYWHEEL_KEY", "")
    if key:
        data, remaining = chat(PROXY_URL, key, [{"role": "user", "content": "Reply with the single word: ready"}])
        print(f"\n[model] {content_of(data).strip()!r}  (tokens remaining: {remaining})")
    else:
        print("\n[model] skipped (set FLYWHEEL_KEY in .env to exercise the proxy)")

    # 3) trivial action + the MANDATORY finish. complete_task is what the oracle reads; without
    #    it you score 0 even with the right answer in stdout. (A throwaway answer here just shows
    #    the call shape -- a real agent computes the right one.)
    env.execute("apis.supervisor.complete_task(answer='quickstart')")

    # 4) the deterministic oracle. Expect False here (we didn't actually solve it).
    print(f"\n[evaluate] success = {env.evaluate()}")
    env.close()
    print("\nquickstart ran end to end. now build agent.py.")


if __name__ == "__main__":
    main()
