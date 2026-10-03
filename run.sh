#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=73
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
cd "$(dirname "$0")"
if [[ "${1:-}" == "--failure-experiment" ]]; then
    python3 run_failure.py
else
    python3 run_lesson.py "$@"
fi
