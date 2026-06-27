"""Answers to the questions every candidate asks. Run it before you ask us.

  python tools/faq.py            list the questions
  python tools/faq.py <words>    print the answers that match (e.g. `python tools/faq.py faiss`)
"""
import sys

FAQ = [
    {
        "q": "Can I use a pre-trained embedding model for retrieval (FAISS, sentence-transformers)?",
        "tags": "faiss embeddings sentence-transformers pretrained model rag vector retrieve bm25",
        "a": """Yes. The only fixed thing in the challenge is the LLM (gemini-3.1-flash-lite through
the proxy). The RAG stack is yours: any embedding model, any vector DB, FAISS, BM25, whatever.

The catch is the sandbox. Your graded run is OFFLINE: dependencies from requirements.txt
install at build time (network allowed), but at runtime your code can reach only the model
proxy and the MCP gateway. Nothing else. So sentence-transformers cannot download weights
from HuggingFace mid-run -- that call will hang and die.

Two ways to make embeddings work:
  1. Commit the model weights into your repo (a MiniLM is ~90MB, fits) and load from the
     local path with local_files_only / HF_HUB_OFFLINE=1.
  2. Pre-compute the index over the 457 docs offline and commit it. Note the query at
     runtime still needs embedding, so for dense retrieval the model ships either way.

Honest take: for finding the right API among 457 docs, BM25 or TF-IDF works very well --
the task text shares vocabulary with the docs (app names, verbs like send/play/transfer).
It is offline by nature, zero heavy deps, zero sandbox risk. Go hybrid (lexical + dense)
if you want more. The big points in this challenge are memory and the self-correction
loop, not the retriever.""",
    },
    {
        "q": "What can my agent reach at runtime? Does the sandbox have internet?",
        "tags": "internet network offline sandbox download runtime egress",
        "a": """No internet at runtime. The graded container reaches exactly two things: the model
proxy (FLYWHEEL_PROXY_URL) and the MCP gateway (FLYWHEEL_MCP_URL). pip dependencies
install at build time with network; after that, everything your code needs must be in
the repo. If your agent works locally but dies graded, a runtime download is the first
thing to check.""",
    },
    {
        "q": "Can I use frameworks like LangChain, LlamaIndex, or the OpenAI SDK?",
        "tags": "framework langchain llamaindex openai sdk library allowed",
        "a": """Yes, anything. The proxy is OpenAI-compatible, so any client works. Pin your deps in
requirements.txt (plain PyPI names only -- VCS/URL/editable installs are rejected). The
one thing you cannot do is swap the model or go around the proxy.""",
    },
    {
        "q": "Why does my task fail even though the API calls look right?",
        "tags": "login auth fail token access_token supervisor passwords",
        "a": """Probably the login flow -- it is the #1 thing that trips people up. Most apps need you
to log in first (get the user's credentials via the supervisor app, then auth against the
target app to get an access_token for subsequent calls). Read docs/appworld.md, the login
section, before debugging anything else.""",
    },
    {
        "q": "What is the difference between practice and evaluate?",
        "tags": "practice evaluate attempts scorecard submit api",
        "a": """Practice is free and unlimited -- use it to calibrate, it returns per-task traces.
Evaluate is the run that counts and you get five attempts, on a held-out split you never
see. Spend them deliberately.""",
    },
    {
        "q": "How is the memory gap measured? What counts as real memory?",
        "tags": "memory gap wiped ablation decorative score",
        "a": """We run your agent twice: memory on, and memory wiped between tasks. The gap between
those two lines is part of your grade. Memory must live in the harness service
(FLYWHEEL_MEMORY_URL / ctx.memory), not in files you write -- and it must change behavior:
something you learn in one task has to make a later task pass that would otherwise fail.
A memory you write but never read scores a zero gap, which fails.""",
    },
]


def main():
    words = [w.lower() for w in sys.argv[1:]]
    if not words:
        print(__doc__)
        for i, e in enumerate(FAQ, 1):
            print(f"{i}. {e['q']}")
        return
    hits = [e for e in FAQ if all(w in (e["q"] + " " + e["tags"]).lower() for w in words)]
    if not hits:
        hits = [e for e in FAQ if any(w in (e["q"] + " " + e["tags"]).lower() for w in words)]
    if not hits:
        print("no match. run with no arguments to list the questions.")
        return
    for e in hits:
        print(f"Q: {e['q']}\n\n{e['a']}\n")


if __name__ == "__main__":
    main()
