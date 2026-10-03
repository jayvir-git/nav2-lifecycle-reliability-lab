# Milestone: independently reproducible shutdown regression

The useful deliverable is a small, reviewable experiment that another engineer can run: a pinned failing control, an isolated candidate, and tests that reject the candidate when its behavior is wrong. It is not a new robotics product or a claim that an upstream maintainer wants this implementation.

**Milestone achieved:** [independent run 37095489089](https://github.com/jayvir-git/nav2-lifecycle-lab/actions/runs/37095489089) passed on both Jazzy and Rolling at lab commit `ba20d4479d7d813a780675fb898baba2111522fd`. Each job passed its 16-case process matrix and 21-case context matrix. The downloaded JSON artifacts were checked for successful outcomes and expected case counts, then saved in this repository as `ci-jazzy-main.json`, `ci-jazzy-context.json`, `ci-rolling-main.json`, and `ci-rolling-context.json`. Runtime and selected package versions are in `milestone-ci.json`.

## A new failure found by broadening the test

The previous main-source port passed standalone process probes. Embedding that same manager in a non-default ROS context with a two-thread executor exposed an initialization abort. The replacement client queried the global context, although the caller had initialized only its own context. An uncaught exception in executor activity terminated the process. See `context-before.log.txt`.

The client now retains the node's context, uses it for its executor and validity check, and the manager creates its worker executor with that context. Shutdown cancellation remains a distinct exception. The previously failing test then exited cleanly (`context-after.log.txt`). The full updated diff is `main-context.patch`; older patches and reports remain historical checkpoints.

A later source comparison also found that the replacement used middleware-default QoS rather than upstream's explicit `rclcpp::ServicesQoS()`. The final candidate preserves that upstream setting. This is a compatibility correction, not evidence that QoS caused the intermittent timeout described below.

A direct [QoS observation](qos-observation.md) found that the middleware-default response subscription in the local Fast DDS environment was best effort with depth 1; the explicit service profile was reliable with depth 10. Request durability differed too. The observation source and raw output are retained.

## What the context tests actually exercise

`tests/context_probe.cpp` uses public APIs of the real manager, ROS context, graph, and executor. There are no injected private-state hooks. It deliberately does not initialize the global context.

- Shutdown after construction but before the first executor spin.
- Shutdown after the graph exposes a client for an intentionally absent lifecycle server.
- Shutdown around initialization/autostart with an empty managed-node list, after the manager service appears in the graph.

The latter two modes use delays of 0, 5, and 50 milliseconds after the observable setup condition. Three repetitions of these seven combinations produce **21 trials**, all passing locally. These are controlled scenarios with timing variation, not forced instruction-level interleavings or an exhaustive race detector. The process timeout is 12 seconds; an abort, missing setup condition, or timeout fails the test.

After the fix, the prior **12-case matrix** also passed locally: ten clean candidate probes plus an unmodified healthy control and an expected unmodified killed-server hang. See `context-matrix.json` and `post-context-main-matrix.json`.

## Independent validation

The GitHub Actions workflow runs disposable [official ROS containers](https://github.com/docker-library/official-images/blob/master/library/ros) on a GitHub-hosted Linux runner, separately from the developer's WSL installation. Each job downloads the checksummed Nav2 snapshot, resolves dependencies from its package manifests, builds the manager and map server, then runs both matrices. Full process logs and package versions are uploaded as artifacts even when later steps fail.

The first Rolling job failed before testing because binary Nav2 packages were unavailable. The revised workflow builds the six needed Nav2 packages from the pinned source instead. This failure remains in the Actions history. Verified independent outcomes and all preceding run IDs are recorded in `milestone-ci.json`.

The first source-built Rolling matrix passed its two controls and nine candidate cases, but one candidate failed startup before fault injection: a state response timed out after map-server configuration. See `rolling-first-matrix.json`. That failed trial is retained. It is not counted as a successful shutdown test, and later passing batches cannot establish its cause or cure.

Subsequent matrices assign each process trial a separate ROS discovery domain to reduce possible stale-discovery interference, and repeat three matched killed-server comparisons. This increases the process matrix to **16 cases** (12 candidate cases and four controls). Domain isolation is a harness improvement and a hypothesis test, not a demonstrated explanation of the first failure. Context tests also use separate domains. The final independent run tests the explicit-service-QoS candidate with this stricter harness.

The isolation-only Jazzy and Rolling runs each still had two candidate startup failures, recorded in `isolation-only-jazzy-matrix.json` and `isolation-only-rolling-matrix.json`. Separate domains were therefore not a sufficient remedy in those batches. A later Rolling run of the service-QoS candidate passed all 16 process cases but could not build the context test because Rolling had removed `ament_target_dependencies`. The test harness now links exported CMake targets; the manager implementation did not change for that repair.

The final local service-QoS candidate passed all 16 process cases and 21 context cases. See `milestone-local-main.json` and `milestone-local-context.json`. The original 12-case and 21-case reports above remain available as earlier checkpoints.

Source is pinned to `d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a` with a checked archive hash. Container tags and apt dependencies are not frozen: this is a repeatable build-and-test recipe, not a bit-for-bit reproducible image. Actions logs record the pulled image digest; artifacts include installed package versions.

## Reproduce locally in a prepared ROS environment

Repository collaborators can also open **Actions → Independent Linux regression → Run workflow** to repeat the complete experiment without a local ROS installation. The repository remains private; this does not claim public availability or outside adoption.

```bash
export NAV2_LAB_BUILD_ROOT="$HOME/nav2-review-build"
export NAV2_LAB_UPSTREAM_ROOT="$HOME/nav2-review-source"
bash build_upstream.sh upstream-main
bash build_main_candidate.sh
bash build_context_probe.sh discovery
source /opt/ros/${ROS_DISTRO:-jazzy}/setup.bash
python3 validate_context.py
python3 validate_main.py
```

This assumes the package dependencies and a compatible installed map server are available. For a fresh environment, use the checked-in CI workflow, which provisions dependencies and builds the map server too. `prepare_ci.sh` is intended for disposable containers with package-install privileges, not as a host installer.

## Remaining review questions

Passing this suite does not establish freedom from data races. ThreadSanitizer, shutdown concurrent with object construction/destruction, diagnostics state access, multiple shutdown callers, all middleware implementations, negative timeout settings, and all client API semantics remain outside this milestone. A custom context with the tested executor arrangement is covered; arbitrary composition is not.

The main-source port has not run the full navigation fault/restart experiment; those earlier results belong to the 1.3.13 candidate. The intermittent response-delivery failure remains unexplained. The duplicated client implementation requires a design decision before any upstream proposal. No issue, PR, or message has been sent to maintainers.

The next useful review is whether cancellation should live in Nav2's existing service client API rather than a manager-local duplicate. The evidence here can inform that discussion without presenting a finished production fix.
