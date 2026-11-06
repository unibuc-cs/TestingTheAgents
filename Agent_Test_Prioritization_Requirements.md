# Research Requirements and Proposed Direction
## Test Prioritization for Agentic Systems in Adobe Experience Manager

This document consolidates what Georgiana requested, what remains unclear, and the research direction discussed so far.

The central goal is to **select and prioritize agent tests and evaluations after software changes, reducing execution time and token consumption while preserving the ability to detect important regressions.**

The prototype should provide a realistic environment in which agents, tools, services, and supporting components can be implemented, observed, modified, and evaluated.

---

# 1. What Georgiana Wants to Achieve

The following requirements come from the July 2026 discussion with Georgiana.

## 1.1 Existing testing environment

| Area | Reported information |
|---|---|
| Agent platform | More than 50 agents supporting AEM-related workflows |
| Existing tests | Unit, integration/system, and end-to-end tests |
| Evaluations | Statistical evaluations (evals) using datasets |
| Dataset examples | Prompt with expected response; prompt with expected tool invocation |
| Execution | Tests are run in batches, including nightly runs |
| Current problem | Determine which tests and eval datasets should run after a change |
| Optimization goals | Reduce execution time and token consumption |
| Coverage preference | Per feature was suggested, with feature changes including skills, harness code, and configuration |

Georgiana described the task as selecting tests and subsets of eval datasets according to changes, rather than generating an entirely new test suite.

## 1.2 Change categories explicitly mentioned

| Change category | Example |
|---|---|
| Skills | Modification of `skill.md` |
| Runtime harness | Modification to agent execution or orchestration code |
| Configuration | Modification of agent or runtime configuration |

The team also needs to clarify whether a single change can affect several agents, shared components, or workflows.

---

# 2. Research Problem

The problem is not simply to execute fewer tests. It is to determine **which evaluations provide sufficient evidence about the effects of a particular change, and in what order they should run.**

Three related problems should be distinguished:

| Problem | Research question |
|---|---|
| Test selection | Which tests and evals should be executed? |
| Test prioritization | In which order should they run? |
| Budget-aware stopping | When is there enough evidence to stop? |

For example, a selection method may identify 20 relevant evaluations. A prioritization method runs the most informative ones first. A stopping criterion determines whether the remaining budget should be spent on more evaluations.

## 2.1 Optimization objectives

Georgiana explicitly identified execution time and token consumption. Monetary cost can also be recorded if available, but it should not become a separate optimization objective unless the team confirms that it matters.

The central trade-off is:

> Reduce execution cost while retaining the ability to detect regressions introduced by changes.

| Efficiency measures | Effectiveness measures |
|---|---|
| Execution time | Regression detection rate |
| Token consumption | Missed regression rate |
| Monetary cost, if available | Coverage of affected behavior |
| Number of evaluations executed | Coverage of important risks |

A method that saves tokens but misses important regressions is not necessarily useful.

---

# 3. Questions to Clarify with Georgiana

The original discussion establishes the problem, but several methodological details remain unresolved.

## 3.1 Changes and dependencies
- How are changes currently identified and categorized?
- Is there a registry mapping agents to skills, tools, configurations, and workflows?
- Can one change affect several agents or shared runtime components?

## 3.2 Existing tests and evals
- How many tests and evaluation examples exist?
- What metadata is available for each test?
- Are datasets tagged by agent, feature, tool, workflow, or behavioral property?

## 3.3 Coverage and quality
- What does sufficient coverage mean for the team?
- Is coverage expected per agent, feature, workflow, execution path, or behavioral property?
- Which failures are critical enough to require mandatory evaluation?

## 3.4 Execution and evaluation
- How are expected outcomes verified: programmatic assertions, LLM judges, human annotations, or a combination?
- Can execution traces and historical results be accessed?
- Is there a mandatory test set, and when should the system stop running additional evaluations?

These questions should guide the experimental design rather than be treated as settled assumptions.

---

# 4. Proposed Technical Direction

The proposed principle is:

> A small real application, real agents, real tools, and executable services, assembled primarily from existing open-source infrastructure, with controlled mutations and observable traces.

The domain can be simulated. The software and its behavior should be real.

## 4.1 Proposed experimental system

```text
                  Agent runtime / harness
                 (Pi or another framework)
                            |
             +--------------+--------------+
             |                             |
      Agent components               Executable services
      - Skills                       - HTTP APIs
      - Prompts                      - Database
      - Tool selection               - Business logic
      - Orchestration                 - Tool adapters
      - Runtime configuration        - Fault injection
             |                             |
             +--------------+--------------+
                            |
                Tasks, tests and eval datasets
                            |
              Independent outcome verification
                    and trace collection
```

The purpose is to introduce controlled changes to different parts of the system and observe which tests detect their effects.

## 4.2 Candidate infrastructure to reuse

These are candidates, not a requirement to combine every project.

| Candidate | Potential contribution |
|---|---|
| Pi | Agent runtime, tools, skills, and configurable extensions |
| τ²-bench | Executable tool environments, policies, tasks, and evaluation machinery |
| AppWorld | Implemented applications, APIs, databases, and task verifiers |
| SkillsBench | Existing skill-based tasks, environments, and automatic checks |
| Harbor | Benchmark execution, container management, and agent integration |

The initial implementation should use the smallest compatible combination that provides meaningful experimental variation.

The current preference is to reuse an existing executable benchmark environment and add Pi or another agent runtime only where needed. This avoids spending most of the project implementing an application instead of studying test selection.

---

# 5. Experimental Structure

## 5.1 Scenario catalogue

Each scenario should have a stable, structured description.

| Field | Purpose |
|---|---|
| Scenario ID | Stable identifier |
| Initial state | Starting environment |
| User request | Input to the agent |
| Relevant components | Skills, tools, configuration, and services |
| Expected outcome | Independently verifiable result |
| Expected behavior | Required or forbidden actions |
| Cost | Historical execution time and token use |
| Risk | Consequence of an incorrect result |

The catalogue should include shared dependencies. For example, several tasks may use the same publication tool or skill. A change to that shared component should affect multiple scenarios, making test selection nontrivial.

## 5.2 Controlled mutations

The initial proposal is to define approximately 20 controlled mutations.

| Mutation category | Example |
|---|---|
| Code | Incorrect tool argument mapping |
| Code | Retry logic mishandles a timeout |
| Skill | Verification instruction removed |
| Prompt | Incorrect tool-selection guidance |
| Configuration | Required tool disabled |
| Runtime | Incorrect termination condition |
| Combined | Code change interacts with configuration |
| Benign change | Refactoring that should not alter behavior |

A mutation is not necessarily a test. It is a controlled change used to determine whether selected tests detect its consequences.

Include changes that do not introduce regressions. Otherwise, a method may appear effective simply by selecting everything.

---

# 6. Coverage Model

Coverage should be multidimensional rather than defined only by the number of agents tested.

| Dimension | What it captures |
|---|---|
| Agent | Which agent is exercised |
| Feature | Which user-visible capability is tested |
| Skill | Which instructions are loaded |
| Tool | Which operations are invoked |
| Configuration | Which settings influence execution |
| Workflow | Which multi-step task is exercised |
| Execution path | Which observed tool or agent sequence occurs |
| Property | Which behavioral requirement is checked |
| Risk | Which important failure modes are covered |

A test may cover a publication workflow, invoke a content-editing skill, use several tools, and verify correctness and authorization.

Coverage should distinguish:

- **Declared coverage:** dependencies recorded in test metadata.
- **Observed coverage:** components and paths actually exercised during execution.
- **Required coverage:** mandatory properties and risks that must be evaluated.

---

# 7. Trace Requirements

Trace information is central because it can reveal dependencies that are not explicitly declared.

At minimum, each execution should record:

| Trace information | Why it matters |
|---|---|
| Test and scenario ID | Identify the evaluation |
| Agent and runtime version | Reproduce the execution |
| Skill and prompt versions | Detect instruction changes |
| Configuration snapshot | Identify effective settings |
| Tool calls and arguments | Understand behavior and dependencies |
| Agent transitions | Reconstruct orchestration |
| Tool results and errors | Identify failure propagation |
| Final response | Evaluate output quality |
| Final application state | Verify actual effects |
| Token usage and latency | Estimate execution cost |
| Evaluator results | Determine pass/fail and evidence |

OpenTelemetry is a candidate for instrumentation, supplemented by application-specific events and state checks.

A trace showing that a tool was called does not prove that the intended state change occurred. Independent verification is required.

---

# 8. Evaluation Methodology

Compare several selection strategies against full-suite execution.

| Strategy | Selection basis |
|---|---|
| Full suite | Execute all tests |
| Random selection | Select tests randomly under the same budget |
| Change-based selection | Use declared component dependencies |
| Coverage-based selection | Cover affected features, tools, and properties |
| Trace-informed selection | Use observed execution dependencies |
| Cost-aware selection | Consider historical execution cost |
| Adaptive selection | Select the next evaluation based on results so far |

Probabilistic selection and contextual bandits are possible later approaches, but simple baselines should be established first.

## 8.1 Evaluation metrics

**Effectiveness**
- Regression detection rate.
- Missed regression rate.
- Coverage of affected properties and workflows.
- Detection of critical failures.

**Efficiency**
- Execution time.
- Token consumption.
- Monetary cost, if available.
- Number of evaluations executed.

**Selection quality**
- Detection rate under a fixed budget.
- Cost required to detect a regression.
- Time to first detected regression.
- Coverage achieved before stopping.

The full suite provides the reference against which reduced suites can be compared.

---

# 9. Proposed Execution Strategy

Georgiana mentioned nightly batch execution. We should not assume the primary use case is a mandatory test run on every pull request.

| Execution point | Proposed purpose |
|---|---|
| Pull request | Fast mandatory checks and targeted evaluations, if required |
| Nightly | Change-aware selection across accumulated changes |
| Full-suite run | Establish reference results and detect selection blind spots |
| Model or runtime upgrade | Broader behavioral evaluation |
| Production | Sampled trace evaluation and drift detection |

The exact schedule should follow the team's existing workflow. Nightly-style batch execution is sufficient for the initial research prototype.

---

# 10. What the Prototype Should Demonstrate

The prototype should answer four questions:

1. Can we identify which tests are relevant to a particular change?
2. Can execution traces improve selection beyond static dependency information?
3. Can we prioritize tests to detect regressions earlier?
4. Can we reduce time and token consumption while retaining acceptable regression detection and coverage?

The initial experiment can use a limited number of agents, skills, tools, services, scenarios, and mutations. It does not need to reproduce Adobe's entire 50+ agent platform.

---

# 11. Research Summary

We aim to develop and evaluate a cost-aware method for selecting and prioritizing agent tests and statistical evaluations after changes to skills, prompts, runtime code, and configuration. The method will use change dependencies, test metadata, execution traces, historical outcomes, and evaluation costs to select a reduced set of tests while preserving coverage of important behaviors and risks. We will study the method in a reproducible environment assembled from existing open-source agent frameworks, executable services, and benchmark tasks, using controlled changes and independent outcome verification. The evaluation will compare selection strategies against full-suite execution in terms of regression detection, coverage, execution time, and token consumption.

**The main research contribution is the selection method—not the benchmark, application domain, or a new agent framework.** Those are experimental infrastructure chosen to make the method testable and the results reproducible.
