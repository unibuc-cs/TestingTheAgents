"""Keyword-based routing and intent detection used by the simulated backend (the LLM backend receives
the same triggers and intents rendered into the orchestrator / agent prompts)."""

import re


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\-]+", text.lower())


def _score(text: str, keywords: list[str]) -> int:
    low = text.lower()
    toks = set(_tokens(text))
    score = 0
    for kw in keywords:
        kw = kw.lower()
        if " " in kw:
            if kw in low:
                score += 2  # multi-word trigger matched as a phrase
        elif kw in toks:
            score += 1
    return score


def route(request: str, agents: dict, default_agent: str) -> tuple[str, dict]:
    """Pick the specialist agent whose triggers best match the request. Ties go to the default agent
    when it is among the best, else to the first best agent in catalogue order."""
    scores = {}
    for name, agent in agents.items():
        if agent.is_orchestrator:
            continue
        s = _score(request, agent.triggers)
        if s > 0:
            scores[name] = s
    if not scores:
        return default_agent, {"reason": "no_trigger_matched", "scores": {}}
    best = max(scores.values())
    candidates = [n for n, s in scores.items() if s == best]
    chosen = default_agent if default_agent in candidates else candidates[0]
    return chosen, {"reason": "trigger_match", "scores": scores}


def detect_intent(request: str, intents: dict[str, list[str]], default: str | None = None) -> str:
    best_name, best_score = default, 0
    for name, keywords in intents.items():
        s = _score(request, keywords)
        if s > best_score:
            best_name, best_score = name, s
    if best_name is None and intents:
        best_name = next(iter(intents))
    return best_name
