# First Nav2 operating lesson

This lab operates the existing ROS 2 Nav2 stack. It is a learning environment, not a new navigation framework or a claim of vehicle validation.

## Visual walkthrough

Open `docs/index.html` in a browser. It works offline with the adjacent `baseline.js` file: step through the navigation pipeline, toggle the educational lifecycle model, and scrub actual feedback from the clean baseline. The visual is not connected to a running robot. `docs/baseline.json` preserves the source evidence; the lifecycle toggle is illustrative.

## Set up on another machine

Use Ubuntu 24.04 (native or a dedicated WSL distribution) with internet access. Review `setup.sh`, then run `sudo bash setup.sh` to install official ROS 2 Jazzy and Nav2 packages. This creates an unprivileged `learner` account if absent and installs a substantial dependency set. Clone this repository into a directory writable by the runtime user. Run `bash run.sh` as that user, not root. The Windows wrapper expects a WSL distribution named `Nav2-Jazzy`; other installations can use the Linux command directly.

This repository includes the lesson code and selected baseline evidence, not the installed WSL disk, package downloads, or local installation logs. The healthy baseline and pause/resume lesson are implemented; deliberate fault injection is future work.

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

The first exercise is to explain why an existing process does not necessarily mean navigation is ready. After that, inspect `launch.log` and identify the configure/activate transitions for the controller. Future lessons can introduce a deliberate startup failure or lost component after the healthy baseline is established.

## Sources

- [Nav2 lifecycle manager](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_lifecycle_manager/README.md)
- [Upstream loopback simulator](https://github.com/ros-navigation/navigation2/tree/jazzy/nav2_loopback_sim)
- [Jazzy installation documentation](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst)

Check an actual run's `summary.json` for its outcome. Installation or file creation alone is not evidence of successful navigation.

## Verified clean baseline

`results/20261002T053910Z`: both goal actions returned SUCCEEDED, four queried lifecycle nodes were active before navigation, controller pause returned inactive, resume returned active, and the launch exited with code 0. A separate Linux process inspection after shutdown confirmed no navigation or simulator processes remained. Success uses Nav2's configured 0.25m position tolerance, not exact arrival at the requested coordinate.

`results/20261002T053530Z` retains the initial failed attempt: lowercase `false` in our invocation caused a Python expression error in the launch path. The runner now uses `False`. No navigation ran in that failed attempt, but a simulator child survived the failed launcher.

`results/20261002T053727Z` completed its goals but is superseded as baseline evidence because that earlier simulator was still running. We identified and stopped the leftover process, strengthened cleanup of the runner's own process group, and repeated the lesson from a clean state to produce the verified run above.
