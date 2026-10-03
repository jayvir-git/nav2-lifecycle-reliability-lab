#!/usr/bin/env bash
# Pinned upstream snapshots, built without modifying installed ROS packages.
set -eo pipefail
variant=${1:?upstream-jazzy or upstream-main}
case "$variant" in
  upstream-jazzy) sha=645abd95f2be02a13ca539b29c2ddc065db34f89; checksum=d8f1b1ff566dacfae63fd474d86b3dbef9cd626ebc254eab0ea04e7ea2246b9a; packages="nav2_util nav2_lifecycle_manager";;
  upstream-main) sha=d7bf2ac06fe778c21c6141eb49b4d3e2c0c82d3a; checksum=c30b04b5b200909eff7f752e91528d2aac37785b12eae7ff697529cb8056460b; packages="nav2_common nav2_msgs nav2_ros_common nav2_util nav2_lifecycle_manager";;
  *) exit 2;;
esac
ros_prefix=/opt/ros/${ROS_DISTRO:-jazzy}
source "$ros_prefix/setup.bash"
base=${NAV2_LAB_UPSTREAM_ROOT:-/home/learner/nav2-upstream-audit}
prefix=${NAV2_LAB_BUILD_ROOT:-/home/learner/nav2-shutdown-build}/$variant/install
mkdir -p "$base" "$prefix"
archive="$base/$sha.tar.gz"
if [[ ! -f "$archive" ]]; then
  curl -fL "https://codeload.github.com/ros-navigation/navigation2/tar.gz/$sha" -o "$archive.part"
  mv "$archive.part" "$archive"
fi
echo "$checksum  $archive" | sha256sum -c -
if [[ ! -d "$base/navigation2-$sha" ]]; then tar -xzf "$archive" -C "$base"; fi
export AMENT_PREFIX_PATH="$prefix:$AMENT_PREFIX_PATH"
for package in $packages; do
  cmake -S "$base/navigation2-$sha/$package" -B "$base/$variant/build/$package" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="$prefix;$ros_prefix"
  cmake --build "$base/$variant/build/$package" -j2
  cmake --install "$base/$variant/build/$package"
done
