# Shutdown cancellation prototype

This experiment tests Nav2 1.3.13 on ROS 2 Jazzy in the dedicated Ubuntu 24.04 WSL environment. It addresses one observed failure: after a managed server dies, the manager's worker waits for its lifecycle response while the shutdown thread waits to join that worker.

## Design

`shutdown_lifecycle_client.hpp` implements a manager-local service client. `patch_cancellation.py` substitutes it into the pinned manager source and sets a shared atomic stop flag at the beginning of `onRclPreshutdown`, before the worker join. Discovery and response waits check the flag in slices of at most 50 ms. On interruption, the client removes the pending request and raises an exception through the manager's existing error-handling path.

The flag stays set. A request beginning after shutdown cannot clear the shutdown intent. This is local cancellation of waiting; it cannot undo a transition that a server already performed. Normal lifecycle transition response waits remain unbounded. Existing finite state-query timeouts remain finite. Thread scheduling and other teardown work mean the 50 ms polling interval is not a shutdown deadline guarantee.

The adapter uses the original client's SystemDefaultsQoS. It is scoped to the experimental manager; the source-built baseline utility library is shared, and installed `/opt/ros` packages are unchanged. The minimal probes record actual loaded library paths. The full run records process command lines and the selected variant.

## Validation and failed attempts

- Three killed-node candidate probes, with shutdown requested 2 s, 0 s, and 0.05 s after bond-loss detection, exited cleanly in 0.165, 0.215, and 0.215 seconds. These are individual observations, not latency guarantees or exhaustive race coverage.
- Suspending a healthy map server for three seconds during pause, then resuming it, produced a successful candidate transition in 3.760 seconds. The two-second bounded-response variant returned failure for this negative control. Its shutdown measurement was not reached after that failure.
- Initial full candidate run `20261003T020246Z` failed before fault injection. Pose publication could be delayed while our observer waited on state queries. Both observers now publish initial pose on a timer while spinning, cancel it before navigation, and keep readiness retries within the existing 90-second budget.
- Full attempt `20261003T020758Z` completed the fault observation but failed a recovery readiness query. It also exposed duplicate interrupts: our harness signalled the process group and ROS launch forwarded another signal to children. We now signal the launcher once, retaining process-group escalation only for timeout/residual cleanup.
- Full attempt `20261003T021100Z` passed fault observation and clean manager shutdown in both phases, but recovery startup stalled. The smoother server explicitly logged that delivery of its change-state response timed out. Cause remains unproven. We retained this failure and removed redundant per-loop pose publication that could flood startup; publication now runs only on its 0.2-second timer. A subsequent successful run, if present in the final evidence, does not establish that the intermittent response failure is solved.

`cancellation-results.json` contains the final baseline and candidate reports, all listed minimal probe results, and failed attempts. Its top-level run `success` and `checks` are authoritative; old historical reports used an imprecise `success_meaning` sentence even when success was false. Final reports describe what success requires. Baseline success means expected fault behavior plus restart; candidate success additionally requires both lifecycle managers to exit cleanly in both phases and no launcher escalation messages.

## Final paired results

With the final timer-only readiness harness, candidate fault run `20261003T021328Z` and recovery `20261003T021359Z` passed all six combined checks: action abortion, planner and navigator deactivation, fresh navigation, no forced shutdown, and clean exit of both lifecycle managers in both phases. The matching baseline fault `20261003T021453Z` still required forced manager termination; recovery `20261003T021534Z` passed navigation and pause/resume. These are one final full sequence per variant, not a reliability-rate estimate.

## Repeat

From this repository in the dedicated WSL distribution, run serially:

```bash
bash build_shutdown_variant.sh baseline
bash build_shutdown_variant.sh shutdown-cancellation
bash probe_shutdown_variant.sh shutdown-cancellation dead
NAV2_PROBE_SHUTDOWN_DELAY=0 bash probe_shutdown_variant.sh shutdown-cancellation dead
NAV2_PROBE_SHUTDOWN_DELAY=0.05 bash probe_shutdown_variant.sh shutdown-cancellation dead
bash probe_shutdown_variant.sh shutdown-cancellation slow
bash build_shutdown_variant.sh bounded-response
bash probe_shutdown_variant.sh bounded-response slow # expected failure
bash run_cancellation_experiment.sh baseline
bash run_cancellation_experiment.sh shutdown-cancellation
```

The pinned source hash and build dependencies are in [source comparison](source-comparison.md). Probes share ROS domain 74 and full runs use 73. Run one experiment at a time. The full test kills only its verified controller process after observed motion, checks action abortion and peer deactivation, then starts a new stack and checks two goals and lifecycle pause/resume. It does not restart just the controller or resume the interrupted goal.

## Limits and next review boundary

This is an experimental candidate, not a production fix or an accepted upstream contribution. We have not tested current upstream main, other middleware, shutdown during initial service discovery, every transition, physical hardware, or exhaustive concurrency interleavings. The manager-local adapter duplicates utility behavior and needs design review before proposing an upstream implementation. The intermittent service-response delivery failure is retained as an unresolved reliability finding. No upstream message or PR has been submitted.
