#!/usr/bin/env bash
# Candidate overlay for this invocation only; installed packages stay intact.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
variant=${1:-shutdown-cancellation}
case "$variant" in baseline|shutdown-cancellation) ;; *) exit 2;; esac
prefix=/home/learner/nav2-shutdown-build/$variant/install
export AMENT_PREFIX_PATH="$prefix:$AMENT_PREFIX_PATH"
export LD_LIBRARY_PATH="$prefix/lib:/home/learner/nav2-shutdown-build/baseline/install/lib:$LD_LIBRARY_PATH"
export ROS_DOMAIN_ID=73
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export NAV2_PROBE_VARIANT=$variant
cd "$(dirname "$0")"
python3 run_failure.py
