"""Keyword-based routing and intent detection used by the simulated backend (the LLM backend receives
the same triggers and intents rendered into the orchestrator / agent prompts)."""

import re


def _tokens(text: str) -> list[str]:
    """The words of ``text`` in lower case: runs of the letters a-z, digits and hyphens, so "go-live" is
    one word. Any other character separates words."""
    return re.findall(r"[a-z0-9\-]+", text.lower())


def _score(text: str, keywords: list[str]) -> int:
    """How strongly ``text`` matches ``keywords``, ignoring case. A one-word keyword adds 1 when it is one
    of the words of the text; a keyword of several words adds 2 when the phrase occurs in the text, since
    a phrase is a stronger signal than a single word."""
    low = text.lower()
    toks = set(_tokens(text))
    score = 0
    for kw in keywords:
        kw = kw.lower()
        # A phrase is looked up in the text as it stands; a single word has to equal a whole word of the
        # text, so "live" does not match "delivery".
        if " " in kw:
            if kw in low:
                score += 2  # multi-word trigger matched as a phrase
        elif kw in toks:
            score += 1
    return score


def route(request: str, agents: dict, default_agent: str) -> tuple[str, dict]:
    """Pick the specialist agent whose triggers best match the request. Ties go to the default agent
    when it is among the best, else to the first best agent in catalogue order.

    Returns the chosen agent's name and an explanation for the trace: ``reason`` is ``trigger_match``, or
    ``no_trigger_matched`` when no trigger matched and the default agent gets the request, and ``scores``
    holds the score of every agent that matched at all.
    """
    # Score every specialist; an orchestrator is never a candidate, and agents without a match drop out.
    scores = {}
    for name, agent in agents.items():
        if agent.is_orchestrator:
            continue
        s = _score(request, agent.triggers)
        if s > 0:
            scores[name] = s
    if not scores:
        return default_agent, {"reason": "no_trigger_matched", "scores": {}}
    # Among the best-scoring agents the default one wins; otherwise the first in the order of ``agents``,
    # which is alphabetical when the dict comes from the agent loader.
    best = max(scores.values())
    candidates = [n for n, s in scores.items() if s == best]
    chosen = default_agent if default_agent in candidates else candidates[0]
    return chosen, {"reason": "trigger_match", "scores": scores}


def detect_intent(request: str, intents: dict[str, list[str]], default: str | None = None) -> str:
    """Name of the intent whose keywords best match ``request``. ``intents`` maps each intent name to its
    keywords, which are scored like routing triggers. On a tie the intent listed first wins. When no
    keyword matches, the answer is ``default``, or the first intent listed when no default is given
    (None only if there are no intents at all)."""
    # Only a strictly higher score replaces the current best, which is what makes the first listed intent
    # win a tie.
    best_name, best_score = default, 0
    for name, keywords in intents.items():
        s = _score(request, keywords)
        if s > best_score:
            best_name, best_score = name, s
    # Nothing matched and there is no default: fall back to the first intent the agent declares.
    if best_name is None and intents:
        best_name = next(iter(intents))
    return best_name
