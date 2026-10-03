# Shutdown diagnosis: a blocked lifecycle service call

Investigated 2 October 2026, America/New_York. Installed ROS 2 Jazzy / Nav2 1.3.13 packages; package versions are recorded in `packages.txt`.

## Reproduction and control

The full navigation failure can be reduced to a map server and lifecycle manager. No simulator, navigation goal, controller, ROS launch process, or group-wide signal is needed. Run only one probe at a time in the dedicated environment. The script selects domain 74, generates its own map, waits for completed manager startup, allows the heartbeat connection to settle, kills its own map-server child, and requires a logged bond failure before testing shutdown.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
python3 diagnose_shutdown.py alive
python3 diagnose_shutdown.py dead
```

The healthy control exits 0 when manager SIGINT exits gracefully. The dead-node test exits 1 if the manager fails the five-second deadline. This is an intentionally failing diagnostic, not a fixed regression test. Cleanup kills only its own remaining subprocesses.

Validated results:

- `shutdown-alive-1790991751335919170`: manager exited gracefully in 0.165 seconds.
- `shutdown-dead-1790991705338641851`: manager remained alive after five seconds; startup and bond-loss gates both confirmed.
- `shutdown-dead-1790991808938017821`: repeated failure with a debugger attached after the five-second deadline. This run used root solely to permit debugger attachment. Its reported elapsed duration includes debugger overhead; do not treat 6.585 seconds as the timeout.

Earlier small tests were invalid for this failure: one killed the node before bond establishment, another did not observe bond-loss handling before shutdown. Their apparent clean exits are not counterexamples. The final probe explicitly gates both conditions. The final ordinary-user dead-node run and root debugger run reproduced the same symptom.

## Mechanism supported by the stack trace

`shutdown-backtrace.txt` captures two relevant threads in the installed binary:

1. The signal/shutdown thread is in `LifecycleManager::onRclPreshutdown`, destroying `NodeThread`, then waiting in `std::thread::join`.
2. That worker is in `checkBondConnections → reset → changeStateForNode → LifecycleServiceClient::change_state → spin_until_future_complete_impl`.

Thus the manager is joining a worker which is still waiting for a lifecycle service response from the killed server. The installed `ServiceClient` overload used by `change_state(uint8_t)` waits without an explicit response deadline. Cancelling the worker's outer executor does not, in this observed run, release the inner service executor. This explains the observed shutdown blockage. We have not patched or rebuilt Nav2, established behavior on every middleware, or tested current upstream main.

Ranked hypotheses considered were simulated-clock effects, group-wide shutdown interference, and blocked lifecycle service handling. The validated reproduction uses wall time and direct process signals, eliminating the first two as necessary conditions. The debugger supports the third.

## Existing upstream work

- [Issue 5437](https://github.com/ros-navigation/navigation2/issues/5437) describes a related shutdown deadlock during bringup.
- [PR 5438](https://github.com/ros-navigation/navigation2/pull/5438) merged into main on 11 August 2025, commit `f7b665406c46494b0f6fbfe80bd16d4f0d85e1df`. It adds service-executor cancellation and lifecycle-client destructor calls.
- [Issue 6041](https://github.com/ros-navigation/navigation2/issues/6041) reports related behavior on Humble.
- Versioned implementation: [manager](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_lifecycle_manager/src/lifecycle_manager.cpp), [lifecycle client](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_util/src/lifecycle_service_client.cpp), [worker thread](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_util/src/node_thread.cpp).

Follow-up: the installed headers and 1.3.13 source already contain the cited cancellation additions. The clean source build still reproduces our crash-triggered hang. A bounded-response diagnostic passes the small test but fails full-stack startup; see [source comparison](source-comparison.md). No upstream issue or PR has been created, and current main has not been tested.
