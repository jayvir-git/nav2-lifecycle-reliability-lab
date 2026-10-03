# Upstream review checkpoint

This is a private review package. Nothing has been submitted upstream. The candidate is **not ready for submission**: the expanded discovery-shutdown test aborts, and a directly overlapping report already exists.

## Pinned upstream sources

Fetched from the official repository on 2 October 2026, America/New_York:

- Jazzy: `645abd95f2be02a13ca539b29c2ddc065db34f89`, committed 28 September. Archive SHA-256 `d8f1b1ff566dacfae63fd474d86b3dbef9cd626ebc254eab0ea04e7ea2246b9a`.
- Main: `d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a`, committed 2 October. Archive SHA-256 `c30b04b5b200909eff7f752e91528d2aac37785b12eae7ff697529cb8056460b`.

`build_upstream.sh` pins both archives and builds into separate prefixes. Jazzy's utility and manager build completed without source edits. Loaded-library paths in the probe results verify that both came from that prefix. The map server and ROS runtime remain the installed Jazzy packages.

The current Jazzy manager passed the healthy control and remained alive beyond the five-second shutdown deadline after its managed map server was killed and bond loss was detected. This extends the runtime evidence to the maintained Jazzy branch; it does not establish behavior on every ROS release.

Main's inspected shutdown callback still resets the worker before clearing lifecycle clients. Its service client has moved into `nav2_ros_common`, with other API and QoS changes. The unmodified pinned main build completed for nav2_common, nav2_msgs, nav2_ros_common, nav2_util, and nav2_lifecycle_manager. Its healthy control exited in 0.165 seconds; its killed-node probe remained alive after five seconds. The test used main-source libraries on the existing Jazzy runtime and an installed Jazzy map server. It is not validation on main's native Rolling distribution. The preceding focused translation-unit compatibility check is not being used as runtime evidence.

## Additional edge cases

`diagnose_shutdown.py transition` starts a real map server and manager, confirms active/bond startup, suspends the server, requests pause, waits for the manager's deactivation log, then signals the manager while its transition is waiting. The candidate exits cleanly; the 1.3.13 baseline exceeds five seconds. Cleanup resumes the server before terminating it.

`probe_discovery.py` starts the real manager with one deliberately absent service, waits until client initialization begins, then interrupts it. Both baseline and candidate exit with SIGABRT. The candidate throws an uncaught `Lifecycle service wait interrupted by shutdown` exception; the baseline reports an invalid ROS context during sleep. These are different exception paths. This test does not demonstrate a new candidate regression, but it disproves complete startup/shutdown coverage. No sanitizer result is claimed. A simple catch around the constructor is not yet a justified fix: initialization can still be mutating lifecycle containers while the pre-shutdown callback clears them. A follow-up design needs to coordinate initialization, service waits, and teardown rather than merely suppressing the exception.

## Existing reports and contribution decision

- [Issue 6565](https://github.com/ros-navigation/navigation2/issues/6565) reports a closely overlapping crashed-node response wait on Nav2 1.3.13. Its [closure comment](https://github.com/ros-navigation/navigation2/issues/6565#issuecomment-5880456756) cites AI spam and contribution policy. A closed/completed label therefore must not be read as evidence that a technical fix landed.
- [Issue 6489](https://github.com/ros-navigation/navigation2/issues/6489) covers a reported initialization/shutdown race under a multithreaded executor. The maintainer questions that usage. Our discovery test uses the normal standalone executable; we have not reproduced that issue's sanitizer findings and do not equate the two.
- [Issue 6556](https://github.com/ros-navigation/navigation2/issues/6556) discusses transition response timeouts under heavy startup load. The maintainer recommends addressing load/composition/networking before adding retries. That context motivates measuring our intermittent failure, not assuming a recovery feature is the correct fix.
- [Nav2's contribution process](https://docs.nav2.org/rolling/community/getting_involved/#process) emphasizes human technical responsibility and earned trust for AI-assisted changes, particularly in sensitive architecture.

The useful deliverable at this checkpoint is reproducible, bounded evidence plus a clearly identified incomplete prototype. A duplicate report or a large automated cancellation rewrite would not yet add a defensible contribution. Before proposing a patch, Jayvir should be able to explain the two executors, the join ordering, why local cancellation cannot undo a remote transition, and what the discovery test revealed. No claim is made that Jayvir independently authored or reviewed the generated implementation.

## Reproduction entry points

```bash
bash build_upstream.sh upstream-jazzy
bash probe_shutdown_variant.sh upstream-jazzy alive
bash probe_shutdown_variant.sh upstream-jazzy dead # expected nonzero on tested commit
bash probe_shutdown_variant.sh baseline transition
bash probe_shutdown_variant.sh shutdown-cancellation transition
source /opt/ros/jazzy/setup.bash
python3 probe_discovery.py baseline
python3 probe_discovery.py shutdown-cancellation
python3 run_reliability.py --pairs 3
```

Run serially in the dedicated WSL distribution, without another Nav2 experiment. `docs/upstream-results.json` records selected probe outcomes. Earlier evidence and the prototype design remain in [cancellation validation](cancellation-validation.md). The prototype patch is available in `docs/cancellation-prototype.patch` for local review; it is against 1.3.13, not a ready-to-submit main-branch PR.

## Review package checks

The exported prototype patch passed `patch --dry-run -p1` against the clean 1.3.13 source. New Python files parse, shell entry points pass `bash -n`, and the notebook JavaScript passes syntax checks. These checks establish reproducibility of the package; they do not erase the failing discovery test.

## Repeated full-stack results

Three alternating pairs completed: baseline 3/3 fault-and-restart sequences, candidate 3/3 sequences including clean shutdown. All three baseline fault phases required forced manager termination; all candidate phases passed clean-manager and no-escalation checks. Both builds completed all six recovery goals across their three runs and pause/resume on each restart. No server response-delivery warning was observed in this batch.

The earlier response-delivery failure was not reproduced. Its cause remains unresolved; absence in six sequences is not evidence that it was fixed. We did not change middleware settings or add transition retries. Aggregate WSL CPU and memory samples are summarized in `reliability-summary.json`; they cannot rule out thread-specific starvation, short unsampled spikes, or Windows host scheduling effects. Compilation had finished before the repeat batch began.

## Main debugger confirmation

A separate root-run probe (root used to permit debugger attachment), `shutdown-dead-1790995333628598576`, captures the same blocked chain in pinned main: pre-shutdown is joining `nav2::NodeThread` at manager line 517, while the worker is in `checkBondConnections -> reset -> change_state` with an infinite (`-1 ms`) transition-response timeout inside `spin_until_future_complete`. See `upstream-main-backtrace.txt`. Its 8.165-second elapsed value includes debugger work and must not be treated as the shutdown deadline or a performance measurement. The ordinary-user main probe independently remained alive at the five-second deadline.

## Subsequent candidate

The [coordinated candidate](coordinated-validation.md) addresses the discovery gap identified at this checkpoint. The findings above describe the original cancellation prototype; newer results are recorded separately.
