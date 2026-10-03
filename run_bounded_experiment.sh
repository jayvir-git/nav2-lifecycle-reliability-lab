#!/usr/bin/env bash
# Experimental overlay for this invocation only. Does not change /opt/ros.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
prefix=/home/learner/nav2-shutdown-build/bounded-response/install
export AMENT_PREFIX_PATH="$prefix:$AMENT_PREFIX_PATH"
export LD_LIBRARY_PATH="$prefix/lib:/home/learner/nav2-shutdown-build/baseline/install/lib:$LD_LIBRARY_PATH"
export ROS_DOMAIN_ID=73
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export NAV2_PROBE_VARIANT=bounded-response
cd "$(dirname "$0")"
python3 run_failure.py
