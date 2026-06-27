"""Export AppWorld's API docs to ./api_docs_dump/ so you can build a retriever over them.
You cannot fit 457 API docs in context; RAG the right ones per task. This is the source.

  python tools/dump_api_docs.py

Writes, under api_docs_dump/:
  <app>.json           all of one app's APIs (dict keyed by api_name -> full doc)
  apis/<app>__<api>.txt   one file per API (name, description, params, response schema) -- a
                          ready-made RAG chunk; index these.

Prefers the on-disk docs at $APPWORLD_ROOT/data/api_docs/standard; if that's missing it boots
one task and reads world.task.api_docs. Each doc has: app_name, api_name, path, method,
description, parameters[], response_schemas. Set APPWORLD_ROOT first (see .env.example).
"""
import json
import os
import sys

OUT = os.path.join(os.getcwd(), "api_docs_dump")


def from_disk(root):
    """Read the per-app json files. Returns {app: {api_name: doc}} or None if absent."""
    stdd = os.path.join(root, "data", "api_docs", "standard")
    if not os.path.isdir(stdd):
        return None
    apps = {}
    for fn in sorted(os.listdir(stdd)):
        if fn.endswith(".json"):
            apps[fn[:-5]] = json.load(open(os.path.join(stdd, fn)))
    return apps


def from_appworld():
    """Fallback: boot one task and read its api_docs collection."""
    from flywheel.appworld_env import AppWorldEnv, load_task_ids
    env = AppWorldEnv(load_task_ids("dev")[0], experiment_name="dump")
    coll = env.task.api_docs
    apps = {app: dict(coll[app]) for app in coll.keys()}
    env.close()
    return apps


def render(doc):
    """One API -> a flat text chunk for retrieval."""
    lines = [f"{doc['app_name']}.{doc['api_name']}  [{doc['method']} {doc['path']}]",
             doc.get("description", "")]
    for p in doc.get("parameters", []):
        req = "required" if p.get("required") else "optional"
        lines.append(f"  - {p['name']} ({p.get('type', '?')}, {req}): {p.get('description', '')}")
    schema = doc.get("response_schemas", {}).get("success")
    if schema is not None:
        lines.append("  response: " + json.dumps(schema)[:600])
    return "\n".join(lines)


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root = os.environ.get("APPWORLD_ROOT", "./aw")
    apps = from_disk(root) or from_appworld()

    os.makedirs(os.path.join(OUT, "apis"), exist_ok=True)
    n = 0
    for app, doc_map in apps.items():
        with open(os.path.join(OUT, f"{app}.json"), "w") as f:
            json.dump(doc_map, f, indent=1)
        for api_name, doc in doc_map.items():
            with open(os.path.join(OUT, "apis", f"{app}__{api_name}.txt"), "w") as f:
                f.write(render(doc))
            n += 1
    print(f"dumped {n} APIs across {len(apps)} apps -> {OUT}/")


if __name__ == "__main__":
    main()
