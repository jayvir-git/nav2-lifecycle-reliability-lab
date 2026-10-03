#!/usr/bin/env bash
# Build only nav2_util and nav2_lifecycle_manager; never replace /opt/ros.
set -eo pipefail
variant=${1:-baseline}
case "$variant" in baseline|bounded-response|shutdown-cancellation) ;; *) exit 2;; esac
source /opt/ros/jazzy/setup.bash
base=/home/learner/nav2-shutdown-build
mkdir -p "$base"
if [[ ! -f "$base/source.tar.gz" ]]; then
  curl -fL https://codeload.github.com/ros-navigation/navigation2/tar.gz/refs/tags/1.3.13 -o "$base/source.tar.gz.part"
  mv "$base/source.tar.gz.part" "$base/source.tar.gz"
fi
echo "424bf5ebe912156448a13c1f4153105d302fcb0a5577e9575af6007306da2670  $base/source.tar.gz" | sha256sum -c -
mkdir -p "$base/$variant/src" "$base/$variant/install"
if [[ ! -d "$base/$variant/src/navigation2-1.3.13" ]]; then
  tar -xzf "$base/source.tar.gz" -C "$base/$variant/src"
fi
if [[ "$variant" == bounded-response ]]; then
  python3 "$(dirname "$0")/patch_shutdown_variant.py" "$base/$variant/src/navigation2-1.3.13"
fi
packages="nav2_util nav2_lifecycle_manager"
if [[ "$variant" == shutdown-cancellation ]]; then
  python3 "$(dirname "$0")/patch_cancellation.py" "$base/$variant/src/navigation2-1.3.13"
fi
if [[ "$variant" != baseline ]]; then packages="nav2_lifecycle_manager"; fi
for package in $packages; do
  cmake -S "$base/$variant/src/navigation2-1.3.13/$package" -B "$base/$variant/build/$package" \
    -DCMAKE_INSTALL_PREFIX="$base/$variant/install" -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="$base/$variant/install;$base/baseline/install;/opt/ros/jazzy" \
    -Dnav2_util_DIR="$base/baseline/install/share/nav2_util/cmake"
  cmake --build "$base/$variant/build/$package" -j2
  cmake --install "$base/$variant/build/$package"
done
sha256sum "$base/source.tar.gz"
