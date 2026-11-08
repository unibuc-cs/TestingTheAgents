"""Agent backends: ``llm_openai``, a chat model behind an OpenAI-compatible client.

A backend decides what one agent does next. A backend module offers ``make_backend_factory(...)``; the
runtime calls the factory it returns as ``factory(agent, runtime, session)`` once for every agent it runs.
The backend then answers ``next_action()`` with an ``Action`` (a tool call or the final message) and
is told the result of every tool call, delegations included, through ``observe(action, result)``.
"""
