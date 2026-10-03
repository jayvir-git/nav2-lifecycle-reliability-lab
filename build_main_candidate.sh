#!/usr/bin/env bash
# Isolated manager build using the already pinned, unmodified main dependencies.
set -eo pipefail
ros_prefix=/opt/ros/${ROS_DISTRO:-jazzy}
source "$ros_prefix/setup.bash"
sha=d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a
build_root=${NAV2_LAB_BUILD_ROOT:-/home/learner/nav2-shutdown-build}
base=$build_root/main-coordinated
deps=$build_root/upstream-main/install
archive=${NAV2_LAB_UPSTREAM_ROOT:-/home/learner/nav2-upstream-audit}/$sha.tar.gz
echo "c30b04b5b200909eff7f752e91528d2aac37785b12eae7ff697529cb8056460b  $archive" | sha256sum -c -
mkdir -p "$base/src"
if [[ ! -d "$base/src/navigation2-$sha" ]]; then tar -xzf "$archive" -C "$base/src"; fi
python3 "$(dirname "$0")/patch_main.py" "$base/src/navigation2-$sha"
export AMENT_PREFIX_PATH="$deps:$AMENT_PREFIX_PATH"
cmake -S "$base/src/navigation2-$sha/nav2_lifecycle_manager" -B "$base/build" \
  -DCMAKE_INSTALL_PREFIX="$base/install" -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_PREFIX_PATH="$deps;$ros_prefix"
cmake --build "$base/build" -j2
cmake --install "$base/build"
