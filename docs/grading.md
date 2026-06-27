# How you're graded

Grading is AppWorld's own deterministic state oracle (`world.evaluate()['success']`). No LLM
judges you. The held-out split is one you never see. Four things decide it.

## 1. Beat the baseline

A naive agent on your same model sets the floor: one model ping, one retrieval, submit — no
memory, no self-correction, no tool recovery. It clears the easy tasks and fails everything that
needs a retry or a recalled fact. You have to clear it **by a margin**. Same model for everyone,
so this is pure engineering: discovery, the login flow, pagination, self-correction.

## 2. A real memory gap

We run your agent twice: with memory **on** (one store persists across the whole task stream)
and with memory **wiped between tasks**. The on-arm must pull ahead. A `memory.json` nobody
reads scores a zero gap and fails this. Store what generalizes (login recipes, solved-task
procedures) and recall it on later tasks.

Self-check it locally:

```bash
python run_local.py --n 8                 # memory ON  (carries across tasks)
python run_local.py --n 8 --memory-off    # memory OFF (wiped between tasks)
```

If the two TGCs are equal, your memory isn't doing anything yet. Note: real AppWorld dev tasks
are independent, so the honest local gap from pure skill-reuse can be small — design memory that
actually changes a later task's outcome.

## 3. Reliability

We re-run held-out tasks **k times** with memory frozen; all k must pass. A solution that passes
once out of three is not a solution. Make the loop deterministic where you can (constrain the
model with `response_format`, verify before `complete_task`, retry on traceback).

## 4. Honest traces

The pass gate reads trusted events emitted by the model and MCP gateways. Candidate-written
JSONL traces are useful for your own debugging, but they are not accepted as proof. Your graded run
must show real `retrieval`, tool calls, and recovery from a failed step through those gateways.
Memory is different: it is the persistent `FLYWHEEL_MEMORY_DIR`, and the on-arm / off-arm score gap
(memory carried across tasks vs wiped between them) is what proves your memory is real, not a trace
event. Decorative calls that don't affect the outcome don't help and read as noise.

## Submit

You submit your **full system**, not just a repo: the tools, the MCP servers, the RAG, the
memory/database, the self-improving loop, and your key prompts. All of it is read in review.

```bash
curl https://homodeus-flywheel.fly.dev/api/submit \
  -H "content-type: application/json" \
  -d '{"token":"'$FLYWHEEL_KEY'",
       "repo":"https://github.com/you/your-agent",
       "writeup":"what you built and why (a few real paragraphs)",
       "systems":{
         "tools":"the tool surface your model can call",
         "mcp":"the MCP server(s) you stood up",
         "rag":"your retriever over the API docs (index, embedder, top-k)",
         "memory":"the store and what crosses tasks",
         "self_loop":"verify / reflect / retry",
         "prompts":"your key prompts"
       }}'
```

The `systems` object is mandatory and every field is read. Be concrete.
