#!/usr/bin/env bash
set -eo pipefail
variant=${1:?variant required}
mode=${2:-dead}
case "$variant" in baseline|bounded-response|shutdown-cancellation|shutdown-coordinated|upstream-jazzy|upstream-main|main-coordinated) ;; *) exit 2;; esac
ros_prefix=/opt/ros/${ROS_DISTRO:-jazzy}
source "$ros_prefix/setup.bash"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export NAV2_PROBE_PREFIX="${NAV2_LAB_BUILD_ROOT:-/home/learner/nav2-shutdown-build}/$variant/install"
export NAV2_PROBE_MANAGER="$NAV2_PROBE_PREFIX/lib/nav2_lifecycle_manager/lifecycle_manager"
export NAV2_PROBE_VARIANT="$variant"
python3 "$(dirname "$0")/diagnose_shutdown.py" "$mode" "${@:3}"
