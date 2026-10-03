# Pinned-main port and concurrency review

The coordinated experiment is now ported to upstream commit `d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a`. This is the previously captured main snapshot, not a claim that the branch has remained unchanged. The manager and its pinned upstream dependencies are built on ROS 2 Jazzy in WSL; this is not native Rolling validation.

## What the review changed

Main creates lifecycle publishers and service servers in its initialization callback as well as clients. The port places this whole initialization sequence under the handoff mutex. Main also passes its configurable `service_timeout` into lifecycle client calls. The manager-local replacement now accepts those arguments instead of silently substituting the old fixed values. Normal lifecycle transitions remain unbounded when their transition timeout is zero; shutdown interrupts the wait.

The port uses a distinct `ShutdownCancelled` exception. Initialization catches that type only when its shutdown flag is set. An unrelated runtime error is no longer swallowed just because shutdown happened concurrently. The historical 1.3.13 candidate and its results are preserved.

## Ownership argument and limits

- Initialization owns the mutex while creating clients, publishers, servers, timers, and the worker pointer. Pre-shutdown publishes cancellation before waiting for this mutex, allowing discovery to unwind.
- The queued startup callback checks the flag and accesses its timer under the same mutex. Pre-shutdown releases the mutex before joining, allowing that callback to finish instead of deadlocking on the mutex.
- After joining the dedicated worker, pre-shutdown can clear worker-owned maps and destroy the bond timer. This argument assumes the standalone manager's callback-group arrangement and one shutdown caller.
- This is a source review, not a ThreadSanitizer result or proof of all interleavings. Construction-time shutdown, destructor/pre-shutdown callback lifetime, diagnostics state access, custom contexts and multithreaded composition need separate investigation. The client currently uses the default ROS context, so custom contexts are outside the validated scope.
- The replacement is a manager-local experimental client, not a general drop-in replacement for every upstream client API. Negative timeout configurations and positive transition deadlines have not been validated. Full navigation results from the 1.3.13 candidate do not establish full-stack behavior for this port.

## Reproduce

In the dedicated WSL environment, after `bash build_upstream.sh upstream-main` has built the pinned dependencies:

```bash
bash build_main_candidate.sh
source /opt/ros/jazzy/setup.bash
python3 validate_main.py
python3 export_prototype_patch.py main-coordinated
```

The suite reruns unmodified main's healthy and killed-server controls, then tests six discovery interruptions (two repetitions at each of 0, 0.05, and 2 seconds after the initialization log) and four candidate service-wait paths. It records every attempted case and process log. See `main-matrix.json` for the actual outcomes; a timing sweep is not an estimate of a production reliability rate.

No upstream issue or PR has been submitted. A next contribution decision should follow native-target validation and human review, including whether maintaining a duplicate client is an acceptable design.

## Recorded outcome

All ten candidate probes passed: six discovery interruptions and four service-wait modes. The two unmodified-main controls also matched their expectations: healthy shutdown exited cleanly, while killed-server shutdown exceeded five seconds. The candidate killed-server probe exited in 0.216 seconds; this single timing is not a guarantee. The exported patch applied cleanly in a dry-run against the pinned source. Python, shell, and JavaScript syntax checks passed.
