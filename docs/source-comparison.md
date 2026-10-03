# Source comparison: existing fix present; blanket timeout rejected

Investigated 2 October 2026 (America/New_York), using Nav2 1.3.13 and the previously recorded Ubuntu/ROS packages.

## Correction to the previous next step

The installed headers and the upstream 1.3.13 source already contain both additions associated with [PR 5438](https://github.com/ros-navigation/navigation2/pull/5438): `ServiceClient::stop()` cancels the service executor, and `LifecycleServiceClient`'s destructor invokes cancellation for both clients. Applying these additions again produced no source diff. The initial duplicate build directory named `upstream-cancellation` is therefore not a patched variant and is excluded from the comparison.

The captured shutdown path joins the worker before clearing the lifecycle-client map. Cancellation in the clients' destructors is consequently not reached while that join is blocked. This is consistent with the debugger trace. We did not test current upstream main or establish whether another upstream change already addresses this trigger.

## Controlled source test

We built unmodified `nav2_util` and `nav2_lifecycle_manager` from the official 1.3.13 tag. The probe records `/proc/<pid>/maps`, verifying which libraries were actually loaded. The map server stays on the installed package.

- Clean source / healthy node: graceful exit in 0.166 seconds.
- Clean source / killed node: manager remained alive after five seconds, reproducing the installed-package result.
- Diagnostic manager / healthy node: graceful exit in 0.165 seconds.
- Diagnostic manager / killed node: graceful exit in 0.165 seconds.

The diagnostic changes one call to use the existing two-second bounded `change_state` overload. It links the same source-built utility library as the clean-source control. This is a mechanism experiment, not an implementation of PR 5438 or a production timeout recommendation.

## Broader validation rejected the diagnostic as a fix

We then ran the original full navigation failure experiment with the diagnostic overlay. Before any controller kill, controller startup exceeded the two-second call deadline. The manager logged `async_send_request failed` and aborted bringup. The observer subsequently timed out waiting for readiness. No recovery phase was attempted after this failed setup.

The candidate improves the minimal shutdown symptom, but the startup observation was later found to be confounded by our observer delaying initial-pose publication while waiting on lifecycle queries. It does not alone establish that healthy controller initialization requires more than two seconds. We corrected the harness and added an independent negative control: suspend a healthy map server for three seconds during a pause request, then resume it. The bounded-response candidate rejected that transition; the shutdown-cancellation candidate completed it. This directly demonstrates the timeout's behavior change. See [cancellation validation](cancellation-validation.md) for the subsequent design and paired tests. The normal lab and `/opt/ros` remain unchanged.

## Repeat

In the dedicated Ubuntu 24.04 environment, install `build-essential`, `cmake`, and `curl`, and retain the existing Nav2 development dependencies. From the lab directory:

```bash
bash build_shutdown_variant.sh baseline
bash build_shutdown_variant.sh bounded-response
bash probe_shutdown_variant.sh baseline alive
bash probe_shutdown_variant.sh baseline dead # expected exit 1 on affected build
bash probe_shutdown_variant.sh bounded-response alive
bash probe_shutdown_variant.sh bounded-response dead
bash run_bounded_experiment.sh # broader test; observed startup regression
```

Run probes serially; they share domain 74. The full simulation uses domain 73. Builds remain under `/home/learner/nav2-shutdown-build`, with per-invocation library overrides; the installed packages are unchanged. The duplicate no-op build is retained only as local exploratory output, not a tested patch.

Source archive: `https://codeload.github.com/ros-navigation/navigation2/tar.gz/refs/tags/1.3.13`.
SHA-256: `424bf5ebe912156448a13c1f4153105d302fcb0a5577e9575af6007306da2670`.
See `source-comparison.json` for the exact run IDs, loaded library paths, and broader-test evidence.
