#!/usr/bin/env bash
# Disposable CI container only: resolve dependencies for the six pinned packages.
set -eo pipefail
base=${NAV2_LAB_UPSTREAM_ROOT:?CI source directory required}
sha=d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a
mkdir -p "$base" results
curl -fL "https://codeload.github.com/ros-navigation/navigation2/tar.gz/$sha" -o "$base/$sha.tar.gz"
echo "c30b04b5b200909eff7f752e91528d2aac37785b12eae7ff697529cb8056460b  $base/$sha.tar.gz" | sha256sum -c -
tar -xzf "$base/$sha.tar.gz" -C "$base"
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then rosdep init; fi
rosdep update --rosdistro "$ROS_DISTRO"
paths=()
for package in nav2_common nav2_msgs nav2_ros_common nav2_util nav2_lifecycle_manager nav2_map_server; do
  paths+=("$base/navigation2-$sha/$package")
done
rosdep install --from-paths "${paths[@]}" --ignore-src --rosdistro "$ROS_DISTRO" -y
dpkg-query -W > results/packages.txt
uname -a > results/kernel.txt
