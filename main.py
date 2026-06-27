"""Entrypoint the sandbox grader invokes once per task. Ctx.from_env() reads the environment:
the graded sandbox sets FLYWHEEL_MCP_URL / FLYWHEEL_PROXY_URL / FLYWHEEL_PROXY_TOKEN (gateways)
and a persistent FLYWHEEL_MEMORY_DIR; locally you set FLYWHEEL_KEY / FLYWHEEL_URL / APPWORLD_ROOT.
Then it runs your solve(ctx). Don't change the contract; put your work in agent.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flywheel import Ctx  # noqa: E402
from agent import solve  # noqa: E402

if __name__ == "__main__":
    solve(Ctx.from_env())
