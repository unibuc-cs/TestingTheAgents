"""Agent runtime harness: configuration, skill loading, tool dispatch, retries, agent loop.

- ``runtime`` runs the agent loop and the delegation between agents.
- ``backends`` decide each agent's next move (a model).
- ``dispatcher`` is the single path from an agent to a tool.
- ``retry`` repeats calls that failed transiently.
- ``faults`` injects such failures on purpose.
- ``agents`` loads the agent definitions.
- ``skills`` loads the SKILL.md files.
- ``config`` reads the runtime settings.
"""
