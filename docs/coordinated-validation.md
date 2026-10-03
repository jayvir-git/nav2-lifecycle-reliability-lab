# Coordinating initialization and shutdown

The previous cancellation prototype released blocked service waits but aborted if shutdown interrupted initial service discovery. This candidate adds coordination around initialization rather than treating the exception alone as the whole problem. It is an isolated patch against Nav2 1.3.13; the installed packages and prior candidates remain unchanged.

## Ordering and ownership

1. Pre-shutdown sets the persistent atomic stop flag **before** waiting for the initialization mutex. A constructor waiting for an absent service can observe the flag and unwind.
2. The initial timer callback owns the initialization mutex while constructing clients, scheduling startup, and publishing the worker-thread pointer. It catches a runtime error only when shutdown has been requested; other runtime errors still propagate. A queued initialization callback observes the flag and returns without touching the containers.
3. Pre-shutdown acquires that mutex to wait for initialization to leave its protected section and to cancel the initialization/startup timer. The startup callback guards its timer access with the same mutex and checks the flag before proceeding.
4. Pre-shutdown **releases the mutex before joining the worker**. Holding it across join could deadlock with a queued startup callback that needs the mutex to observe shutdown.
5. Only after the worker has exited does pre-shutdown destroy the bond timer and clear node names, lifecycle clients, and bonds. This also avoids resetting the bond timer while a worker callback is using or resetting it.

The service client is unchanged from the first prototype: it checks shutdown between bounded wait slices while allowing healthy transitions to take longer than a blanket two-second timeout. This patch does not cancel a transition already executing remotely.

## Focused regression matrix

`validate_coordinated.py` executes real processes serially, records every result and process log, and preserves expected failing controls.

- Baseline 1.3.13 and the first cancellation candidate both still abort during missing-service discovery, with exit code -6. Both reached client initialization before interruption.
- The coordinated candidate exits cleanly in all 15 discovery trials: three repetitions each at 0, 0.005, 0.05, 0.5, and 2 seconds after the initialization log is observed. These are delay settings, not precisely controlled CPU interleavings. A zero delay still occurs after the observer notices the log.
- Healthy shutdown, killed-server shutdown after bond-loss detection, shutdown during a suspended server's transition, and a three-second delayed healthy transition all pass. The delayed pause completes successfully in 3.802 seconds in this run.

The 21-case matrix therefore contains 19 candidate clean exits and two deliberately failing controls. See `coordinated-matrix.json` for individual timings, loaded-library paths, and logs. An initial build attempt failed the upstream compiler's shadow-variable warning; unique lock-variable names resolved that compilation error before runtime testing.

## Reproduce

In the dedicated WSL environment, run one experiment at a time:

```bash
bash build_shutdown_variant.sh baseline
bash build_shutdown_variant.sh shutdown-cancellation
bash build_shutdown_variant.sh shutdown-coordinated
source /opt/ros/jazzy/setup.bash
python3 validate_coordinated.py
python3 run_reliability.py --candidate shutdown-coordinated --pairs 2
python3 export_prototype_patch.py shutdown-coordinated
```

The full runner applies strict clean-manager and no-escalation checks to both cancellation candidates. Each sequence injects a controller failure only after observed motion, verifies the aborted action and inactive peers, then restarts the stack and tests two goals plus lifecycle pause/resume. Baseline success excludes clean shutdown by design; its forced shutdown remains explicitly recorded.

## Limits

This is a tested experimental candidate, not an upstream-ready or production-certified fix. Timing sweeps do not replace ThreadSanitizer or a proof of all interleavings. Tests use the standalone manager on one WSL/Jazzy environment, one missing discovery service, and the existing idealized navigation simulation. Shutdown before the initialization callback is observed, multiple simultaneous shutdown callers, custom multithreaded composition, and other middleware are not covered. The new patch has not been ported to current main. The earlier intermittent response-delivery failure remains unresolved; later clean runs cannot prove its cause or cure.

The [upstream review](upstream-review.md) still applies: related reports already exist, and no issue or PR has been submitted. A human design review of initialization, worker lifetime, and cancellation behavior remains necessary before proposing this implementation upstream.

## Full-stack confirmation

Two alternating baseline/coordinated pairs completed successfully under their respective checks. Candidate fault runs `20261003T025555Z` and `20261003T025748Z`, with restart runs `20261003T025625Z` and `20261003T025820Z`, passed all six combined checks. Both paired baseline fault runs still required forced shutdown. All four candidate recovery goals succeeded, with pause/resume and clean manager exits in both phases. No response-delivery warning occurred in this batch. See `coordinated-reliability.json` for the checks, run IDs, and resource summaries.

The exported `coordinated-prototype.patch` passed a dry-run against the clean 1.3.13 source. Python parsing, shell syntax checks, and JavaScript syntax checks passed. These checks and the finite timing matrix do not establish exhaustive concurrency correctness.

## Subsequent checkpoint

A separate pinned-main port and its focused validation are recorded in [main-port-review.md](main-port-review.md). This document and its full-navigation evidence describe the historical 1.3.13 candidate.
