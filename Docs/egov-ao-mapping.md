# e-Gov Prototype → AO Mapping

This document maps the e-gov prototype architecture to AO concepts.

---

## Architecture Layers

### Entry Agent (Workflow Router)
AO handles routing natively. The entry agent is the AO harness itself — it reads the user's message, detects intent, and dispatches to the right agent. No custom code needed here.

### Domain Agents
Each workflow-specific agent (Social Benefits, Local Tax, ID Services, Property Sale, E-Factura, etc.) becomes a separate AO agent, instantiated based on a configuration that makes them act differently, with its own instructions and permitted tools. Agents are isolated from each other by configuration.

### Shared Services
The shared services tier maps directly to **AO skills** — reusable capabilities that any agent can invoke.

| Shared Service | Skill responsibility |
|---|---|
| Document Processing & Validation | OCR, extraction, validation |
| Legal / RAG | Knowledge lookup against legal documents |
| Payment Processing | Integration with payment APIs |
| Scheduling | Appointment and queue management |
| Tax Calculation | Compute taxes from structured inputs |
| Case Management | Create, update, and retrieve cases |

Skills are called by domain agents, not by the user directly. Multiple agents can share the same skill.

### Guarded Tool Layer
AO controls which tools each agent can access. This is configured per agent — an agent only sees the tools it needs. This maps directly to the guarded tool layer in the prototype.

### UiPath SDK + External APIs
External capabilities (ghiseul.ro, ANAF SPV, RO e-Factura, city hall APIs, UiPath buckets, queues, etc.) are exposed as tools. Agents call them through AO's tool layer, subject to the access rules above.

### Human-in-the-Loop
The UiPath `Create Task` pattern (escalate complex cases to a human) maps to AO's built-in human-in-the-loop support.

