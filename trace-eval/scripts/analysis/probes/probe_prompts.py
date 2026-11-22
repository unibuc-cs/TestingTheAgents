"""Probe (read-only): the system prompt and the first user message each agent is sent, built without a model."""

import sys
from types import SimpleNamespace

from traceeval.catalog import load_catalog
from traceeval.sut import SUT_ROOT
from traceeval.sut.harness.agents import AgentLoader
from traceeval.sut.harness.backends.llm_openai import build_system_prompt, build_user_message
from traceeval.sut.harness.config import Config
from traceeval.sut.harness.runtime import Session
from traceeval.sut.harness.skills import SkillLoader
from traceeval.sut.tools import TOOLS

config = Config.load(SUT_ROOT / "config" / "runtime.yaml")
agents = AgentLoader(SUT_ROOT / "agents")
skills = SkillLoader(SUT_ROOT / "skills")
runtime = SimpleNamespace(agents=agents, skills=skills, config=config)
which = sys.argv[1:] or agents.available()
sizes = {}
for name in agents.available():
    agent = agents.load(name)
    session = Session(agent=agent, skills=[skills.load(s) for s in agent.skills], ctx={}, request="")
    prompt = build_system_prompt(agent, session, runtime)
    sizes[name] = (len(prompt), len(agent.tools), len(agent.skills))
    if name in which:
        print("=" * 30, name, "tools:", agent.tools)
        print(prompt)
print({k: v for k, v in sizes.items()})
print("tools registered:", len(TOOLS), sorted(TOOLS))
case = {c.id: c for c in load_catalog()}["AUT-01"]
agent = agents.load("authoring")
print(
    build_user_message(
        Session(agent=agent, skills=[], ctx={**case.context, "request": case.request}, request=case.request)
    )
)
