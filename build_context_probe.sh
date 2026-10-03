#!/usr/bin/env bash
set -eo pipefail
ros_prefix=/opt/ros/${ROS_DISTRO:-jazzy}
source "$ros_prefix/setup.bash"
base=${NAV2_LAB_BUILD_ROOT:-/home/learner/nav2-shutdown-build}
export AMENT_PREFIX_PATH="$base/main-coordinated/install:$base/upstream-main/install:$AMENT_PREFIX_PATH"
cmake -S "$(dirname "$0")/tests" -B "$base/context-probe" \
  -DCMAKE_PREFIX_PATH="$base/main-coordinated/install;$base/upstream-main/install;$ros_prefix"
cmake --build "$base/context-probe" -j2
export LD_LIBRARY_PATH="$base/main-coordinated/install/lib:$base/upstream-main/install/lib:$LD_LIBRARY_PATH"
export ROS_DOMAIN_ID=74 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
timeout 12 "$base/context-probe/context_probe" "${1:-discovery}"
