# Notes from 10 November 2026: revealing tests, the fields of a property, take-aways, GPUs

**1. "A test reveals a change" and "catalog order."**
A test reveals a change when it passes on the current app and fails on the changed copy, each by majority over the
recorded runs (three for Gemma). The revealing tests of a change are its ground truth. They are measured after the
recording, and no strategy is ever shown them. A change with no revealing test is either benign or one the model
does not notice. "Catalog order" is what the `full` strategy runs: the tests as they are listed in the catalog's
YAML files, then the dataset items. It is the reference, not a method. Both terms are now defined where they first
appear in DEMO.md.

**2. The fields of a property.** The lines selected in `properties.yaml` (`checked_by: [state, trace]`,
`mandatory: false`, `threshold: 0.95`) are a property that is checked on the final state and on the trace, is not a
release blocker, and counts as met when at least 95% of its tests pass. All six fields and where the code uses them:

- **category**: one of correctness, safety, resilience, orchestration, efficiency, quality. The report groups by
  it, and the drafting command takes a new property's defaults from it (safety becomes mandatory with threshold
  1.0).
- **description**: the requirement in a sentence, read by people and by the model that tags the tests.
- **checked_by**: how its tests verify it: state (final application state), trace (tool calls, agents, audit,
  steps), judge (a model reads the answer against a rubric), dataset (prompt to expected item). It documents the
  oracle; the draft accepts only these values.
- **mandatory**: a release blocker. The adaptive method's last step runs a test of every mandatory property a
  change may affect before calling the change clean. The live check names affected properties left unchecked, and
  the report counts the runs that covered them.
- **threshold**: the share of its tests that must pass on the current app. Report section 5 compares the mean pass
  rate of its tests with it. This is policy, not used by selection.
- **sources**: the components that state the requirement, as component ids. A change affects a property when its
  change set touches one of the sources, or when a test that checks the property reached a changed component in its
  traces.

The explanation was spread over the YAML header, AEM_ALIGNMENT §3.4 and USER_GUIDE §7, and none said where each
field is used. AEM_ALIGNMENT §3.4 now has a field table with the uses; USER_GUIDE §7 and DEMO §6 point to it.

**3. Take-aways.** A numbered "Take-aways" section closes DEMO.md, the same list is RESEARCH_PLAN §5.5, and the
README points to it. Eight items: record traces rather than maintain a map; read the diff; stop when confident,
with the mandatory rule as the safety net; discount the tests the model already fails; measure the model's noise
before trusting a verdict; where CASPER and the bandit fit, including the AEM first-pass point and the combination;
text as the cheap fallback; and what is not yet covered.

**GPUs.** Gemma is recording the frozen app with five repetitions on fmi0 GPU 0, about two hours (`runs/gemma7` in
the record checkout). It tests whether Gemma's vote stays stable with five runs and gives Gemma a history for the
four tests the demo recording lacks (CFG-01..03, WF2-03). Qwen continues on the cluster until about 18:00. GPU 1
stays idle, since a second Qwen copy cannot join the running job and gpt-oss needs both. When Qwen's job ends, the
plan is to resubmit it for the baseline rerun that replaces the tunnel-broken repetition. All servers come down
before Thursday morning.

Commits on branch `baselines`: `4033962` (gpt-oss five repetitions, report in `docs/results/gptoss7/`), `69d8d9e`
(definitions, the fields of a property, the take-aways).
