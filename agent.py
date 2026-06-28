"""Flywheel agent: an engineered ReAct loop over the fixed model (gemini-3-flash-preview) and the
AppWorld world. The model and world are fixed; everything here is the engineering that moves the
number: discovery before calling, the login flow, pagination-to-empty, bulk work in one run_code,
verify-before-submit, self-correction on tracebacks, and a cross-task memory that is actually read.

The skeleton always reaches a final complete_task (the #1 documented zero is never submitting).
"""

import re

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

# Everything the docs say trips agents up, compressed into the standing instructions.
SYSTEM = (
    "You solve AppWorld tasks by writing Python that runs against an `apis` object in a stateful "
    "sandbox. Output EXACTLY ONE ```python``` block per turn. Sandbox STATE (logins, created "
    "records) persists across turns, but Python variables do NOT unless you keep them in one block "
    "or reprint them, so re-derive tokens/ids you need.\n\n"
    "DECIDE THE TASK KIND FIRST:\n"
    "  QUESTION (asks for a value)  -> compute it, then apis.supervisor.complete_task(answer=VALUE).\n"
    "  ACTION   (asks to change the world) -> mutate the world, then apis.supervisor.complete_task() "
    "with NO answer. Returning prose for an action scores 0; returning nothing for a question scores 0.\n\n"
    "THE LOOP:\n"
    "1) DISCOVER, never guess names: apis.api_docs.show_api_descriptions(app_name=APP) then "
    "apis.api_docs.show_api_doc(app_name=APP, api_name=API) for exact params + return shape before any write.\n"
    "2) LOG IN before authed calls:\n"
    "   me = apis.supervisor.show_profile()\n"
    "   pw = {p['account_name']: p['password'] for p in apis.supervisor.show_account_passwords()}\n"
    "   tok = apis.<app>.login(username=me['email'], password=pw['<app>'])['access_token']\n"
    "   thread access_token=tok through every authed call. For `phone`, login with me['phone_number']; "
    "if an email login fails, retry with the phone number.\n"
    "3) PAGINATE list/search APIs to the end: loop page_index=0,1,2,... (page_limit large) until a page "
    "comes back short or empty, aggregate in-process. Never read just page 0.\n"
    "4) DO THE BULK IN ONE run_code: a 'follow ALL / like ALL / comment each' task is ONE paginated loop "
    "that writes every item, not one turn per item. Inspect a record's keys with print(rec) before indexing; "
    "field names vary by app.\n"
    "5) VERIFY before finishing: re-read the world (re-list, re-query) and confirm every entity named in the "
    "instruction is in the goal state. Only mutate what the task asks for; extra writes are penalized.\n"
    "6) SELF-CORRECT: on a traceback, read it and fix the exact cause (wrong api name -> look it up; missing "
    "access_token -> add it; wrong field -> print keys). Never repeat an identical failing call.\n\n"
    "APP GOTCHAS: spotify song_ids live on albums/playlists too -- 'across libraries' = union of song_id from "
    "show_song_library + every album.song_ids + every playlist.song_ids, de-duped with a set; play_count/genre/"
    "title need apis.spotify.show_song(access_token=tok, song_id=sid). venmo search_users returns email, not "
    "user_id; transactions go by receiver_email. Answers must be EXACT: a number, a name, or a comma-separated "
    "list in stored casing.\n\n"
    "Always end by calling apis.supervisor.complete_task. No submit, no credit."
)

# Login recipe seeded into memory so it is read on task 1, not relearned.
LOGIN_RECIPE = (
    "me=apis.supervisor.show_profile(); "
    "pw={p['account_name']:p['password'] for p in apis.supervisor.show_account_passwords()}; "
    "tok=apis.<app>.login(username=me['email'], password=pw['<app>'])['access_token']; "
    "thread access_token=tok through authed calls; phone app uses me['phone_number']; "
    "retry email login with phone_number on failure."
)


def _code(text):
    """Pull the python from a reply: the last fenced block, else a bare apis.* snippet."""
    blocks = CODE_RE.findall(text or "")
    if blocks:
        return blocks[-1].strip()
    if text and "apis." in text and "```" not in text:
        return text.strip()
    return None


def _content(resp):
    if not isinstance(resp, dict) or resp.get("error"):
        return ""
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _retrieve(ctx, instr):
    """RAG over the 457 docs. One broad hit set on the instruction; cheap and traced."""
    try:
        return str(ctx.retrieve(instr))[:1800]
    except Exception:
        return ""


def solve(ctx):
    instr = ctx.instruction or ""

    # cross-task memory: read it, inject it, so a later task reuses earlier recipes
    try:
        mem = ctx.memory.read() or {}
    except Exception:
        mem = {}
    if "login_recipe" not in mem:
        try:
            ctx.memory.write("login_recipe", LOGIN_RECIPE)
            mem["login_recipe"] = LOGIN_RECIPE
        except Exception:
            pass
    recall = "\n".join(f"- {k}: {v}" for k, v in mem.items()) if mem else ""

    hits = _retrieve(ctx, instr)

    first = (
        f"TASK:\n{instr}\n\n"
        + (f"LEARNED FROM PRIOR TASKS (reuse, do not relearn):\n{recall}\n\n" if recall else "")
        + (f"RETRIEVED API HITS:\n{hits}\n\n" if hits else "")
        + "Decide QUESTION vs ACTION. Write your FIRST ```python``` block: discover the right apis and run "
        "the login flow (profile + show_account_passwords + app.login -> access_token), printing what you "
        "need to read back."
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": first},
    ]

    submitted = False
    verified = False
    empty_replies = 0
    # keep per-task wall-clock inside the grader's lease: fewer turns, leaner context
    turns = min(ctx.max_steps, 14)
    for turn in range(turns):
        reply = _content(ctx.model(messages))
        code = _code(reply)
        if not code:
            empty_replies += 1
            if empty_replies >= 3:
                break
            messages.append({"role": "user", "content": "Reply with EXACTLY one ```python``` block and nothing else."})
            continue
        empty_replies = 0
        messages.append({"role": "assistant", "content": reply})

        try:
            result = str(ctx.run_code(code))
        except Exception as ex:  # never let a tool error kill the loop
            result = f"Traceback: {ex}"

        if "complete_task" in code:
            submitted = True
            break

        errored = "Traceback" in result or "Error" in result
        if errored:
            ctx.reflect("execution error; reading the traceback and fixing the exact cause before retrying")

        left = turns - turn - 1
        # one mandatory verify pass before we let it submit, on a clean run
        if not errored and not verified and left <= 6:
            verified = True
            nudge = (
                " Before finishing: re-read the world and confirm EVERY entity named in the task reached the "
                "goal state (for a question, recompute the exact value from the last page). Then call "
                "apis.supervisor.complete_task (answer=... only for a question)."
            )
        elif left <= 3:
            nudge = " Few turns left: finish now -- verify quickly, then call apis.supervisor.complete_task."
        else:
            nudge = " Continue with one ```python``` block; call apis.supervisor.complete_task when the world is in the goal state."

        messages.append({"role": "user", "content": f"RESULT:\n{result[:3500]}\n\n{nudge}"})

    # unconditional submit: never leave a task unsubmitted (the #1 documented zero)
    if not submitted:
        ctx.reflect("forcing a final complete_task so the task is never left unsubmitted")
        try:
            ctx.run_code(
                "try:\n"
                "    apis.supervisor.complete_task()\n"
                "except Exception:\n"
                "    apis.supervisor.complete_task(answer='')"
            )
        except Exception:
            try:
                ctx.mcp.call("complete_task", {})
            except Exception:
                pass

    # remember a compact, generalizing recipe keyed by the apps this task touched
    try:
        apps = [a for a in ("spotify", "amazon", "gmail", "phone", "venmo", "splitwise",
                            "todoist", "simple_note", "file_system") if a in instr.lower()]
        if apps:
            key = "recipe_" + "_".join(apps)
            if key not in mem:
                ctx.memory.write(key, "login, paginate list APIs to empty, bulk-write in one run_code, verify by re-reading, then complete_task")
    except Exception:
        pass
