# First Nav2 operating lesson

This lab operates the existing ROS 2 Nav2 stack. It is a learning environment, not a new navigation framework or a claim of vehicle validation.

## Visual walkthrough

Open `docs/index.html` in a browser. It works offline with the adjacent `baseline.js` file: step through the navigation pipeline, toggle the educational lifecycle model, and scrub actual feedback from the clean baseline. The visual is not connected to a running robot. `docs/baseline.json` preserves the source evidence; the lifecycle toggle is illustrative.

## Set up on another machine

Use Ubuntu 24.04 (native or a dedicated WSL distribution) with internet access. Review `setup.sh`, then run `sudo bash setup.sh` to install official ROS 2 Jazzy and Nav2 packages. This creates an unprivileged `learner` account if absent and installs a substantial dependency set. Clone this repository into a directory writable by the runtime user. Run `bash run.sh` as that user, not root. The Windows wrapper expects a WSL distribution named `Nav2-Jazzy`; other installations can use the Linux command directly.

This repository includes the lesson code and selected experiment evidence, not the installed WSL disk, package downloads, or local installation logs. The healthy baseline, pause/resume lesson, and controller interruption with full-stack restart recovery are implemented.

## Environment

Dedicated WSL distribution: `Nav2-Jazzy`, Ubuntu 24.04, official ROS 2 Jazzy packages. The original Ubuntu 22.04 distribution is separate. The Ubuntu base image checksum is checked against Canonical's HTTPS-hosted SHA256SUMS before import. Downloads and the WSL virtual disk live under this lab's ignored directories; do not delete the `wsl` directory while the distribution is registered.

ROS discovery is limited to localhost, on domain 73. Runtime commands use the unprivileged `learner` user. The setup script installs the package dependencies; the runtime script does not require root.

## Run the lesson

From PowerShell in this directory:

```powershell
.\run.ps1
```

This starts upstream `tb3_loopback_simulation.launch.py` with separate processes and no RViz window, sets the robot's position to (-2, 0), requests destinations (-1, 0) and (0, 0), then pauses and resumes the navigation lifecycle. Each run writes its own directory under `results`. The launch processes are shut down afterwards. Run one copy at a time because the lesson uses a fixed ROS domain and node names.

The map is a deliberately simple 10-by-10-metre room. Nav2's loopback simulator converts commanded velocity into idealized motion. It does not model wheel slip, inertia, real sensor error or physical collisions. Successfully navigating here demonstrates software integration, not robot safety.

## Understand the components

- `map_server` supplies the room's occupancy map: which cells represent free space or walls.
- `planner_server` computes a route to a requested destination.
- `controller_server` uses the route and current pose to produce velocity commands.
- `bt_navigator` coordinates navigation through a behavior tree and exposes the long-running navigation action.
- `loopback_simulator` consumes velocity commands and supplies simulated motion/transforms and map-derived scans.
- `robot_state_publisher` supplies the relationships between the robot's body and sensor frames.
- Lifecycle managers configure and activate the managed nodes, and handle coordinated pause/resume/shutdown.

These are ROS nodes, which are software components. With composition disabled for this lesson, the navigation servers are launched in separate operating-system processes. A ROS node and a Linux process are not universally the same thing: composition can put several nodes in one process.

## What to look for

1. `initial_states` records the states of four key lifecycle nodes before sending a goal. All must be active.
2. Each navigation action result has a ROS action status. Status 4 means SUCCEEDED. The feedback records the robot's reported position and remaining distance; it is not an independent physical measurement.
3. Pause should leave `controller_server` inactive. Its process still exists, but the lifecycle has disabled its operational behavior.
4. Resume should return the controller to active.
5. `launch.log` records startup and shutdown, including failures. `nodes.txt`, `topics.txt`, `processes.txt` and `packages.txt` capture the software that ran.

The first exercise is to explain why an existing process does not necessarily mean navigation is ready. After that, inspect `launch.log` and identify the configure/activate transitions for the controller. The second lesson below interrupts that controller while navigation is underway.

## Controller failure and restart experiment

Run from the repository directory in PowerShell:

```powershell
.\run.ps1 --failure-experiment
```

On Ubuntu, use `bash run.sh --failure-experiment`. Use only the dedicated simulation environment, with one lesson running at a time. The observer verifies the exact controller executable, runtime UID, and the launch process group before sending SIGKILL. It waits for map-frame action feedback to move from x=-2 past x=-1.85 before interruption. The requested destination is (2, 0).

The observer records action completion, lifecycle service samples, and odometry for 20 seconds after interruption. Then the runner cleans up the failed stack and starts a completely fresh stack, resets the pose, and verifies two successful goals plus lifecycle pause/resume. This is deliberate full-stack restart recovery, not automatic respawn or resumption of the interrupted goal.

Two trials on 2 October 2026 evening (America/New_York; 3 October UTC) observed:

- First fault run `20261003T013022Z`: navigation ABORTED 1.091 seconds after SIGKILL; planner first observed inactive after 5.131 seconds. Restart run `20261003T013107Z` passed both goals and pause/resume.
- Repeat fault run `20261003T013207Z`: navigation ABORTED after 0.109 seconds; planner first observed inactive after 5.187 seconds. The corresponding recovery evidence is included in `docs/failure.json`.
- Both fault runs logged a missed controller heartbeat with a 4000 ms threshold and deactivated related nodes. The separately managed map server stayed active. Lifecycle sampling is roughly once per second; first observation is not an exact transition timestamp. Two runs do not establish latency guarantees.
- Both fault runs required SIGINT → SIGTERM → SIGKILL escalation for the navigation lifecycle manager during cleanup. The launch exit code was nevertheless zero. This is a reproducible observation, not an established upstream defect or a claim of graceful recovery.
- Final odometry samples reported zero longitudinal velocity and unchanged position, then stopped arriving. The installed simulator stops integrating commands after one second without fresh velocity, and that path does not publish odometry. We have not isolated the cause of stopping, or measured continuous standstill over the whole observation window. Odometry and map coordinates use different frames.

The combined report's `success` means the action-abort, peer-deactivation and fresh-navigation checks passed. It does not mean every component shut down gracefully. `forced_shutdown_observed` and selected raw log excerpts preserve that distinction. Full local logs remain in `results/`; selected shareable evidence and installed Nav2 package versions live in `docs/`.

Open `docs/index.html#failure` for the interactive event sequence, healthy/fault comparison, and explicit recovery limits. The subsequent [shutdown diagnosis](docs/shutdown-diagnosis.md) reduces the hang to two processes and captures the blocked threads. `docs/index.html#shutdown` explains the mechanism visually. This diagnosis does not claim a tested fix or a new upstream defect.

The [isolated source comparison](docs/source-comparison.md) confirms the upstream cancellation additions are already present. An experimental bounded-response call passes the small shutdown test but breaks full-stack startup, so it is rejected as a fix. The normal lesson continues to use installed Nav2. Open `docs/index.html#comparison` for that comparison.

## Sources

- [Nav2 lifecycle manager](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_lifecycle_manager/README.md)
- [Upstream loopback simulator](https://github.com/ros-navigation/navigation2/tree/jazzy/nav2_loopback_sim)
- [Jazzy installation documentation](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)

Check an actual run's `summary.json` for its outcome. Installation or file creation alone is not evidence of successful navigation.

## Verified clean baseline

`results/20261002T053910Z`: both goal actions returned SUCCEEDED, four queried lifecycle nodes were active before navigation, controller pause returned inactive, resume returned active, and the launch exited with code 0. A separate Linux process inspection after shutdown confirmed no navigation or simulator processes remained. Success uses Nav2's configured 0.25m position tolerance, not exact arrival at the requested coordinate.

`results/20261002T053530Z` retains the initial failed attempt: lowercase `false` in our invocation caused a Python expression error in the launch path. The runner now uses `False`. No navigation ran in that failed attempt, but a simulator child survived the failed launcher.

`results/20261002T053727Z` completed its goals but is superseded as baseline evidence because that earlier simulator was still running. We identified and stopped the leftover process, strengthened cleanup of the runner's own process group, and repeated the lesson from a clean state to produce the verified run above.
