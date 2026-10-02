#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl locales python3
locale-gen en_US.UTF-8
export LANG=en_US.UTF-8
version=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')
curl -fL "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${version}/ros2-apt-source_${version}.noble_all.deb" -o /tmp/nav2-ros-source.deb
dpkg -i /tmp/nav2-ros-source.deb
apt-get update
apt-get install -y --no-install-recommends ros-jazzy-ros-base ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-minimal-tb3-sim ros-jazzy-nav2-loopback-sim ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py
if ! id learner >/dev/null 2>&1; then useradd -m -s /bin/bash learner; fi
if ! grep -q '/opt/ros/jazzy/setup.bash' /home/learner/.bashrc; then
  printf '\nsource /opt/ros/jazzy/setup.bash\nexport ROS_DOMAIN_ID=73\nexport ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST\n' >> /home/learner/.bashrc
fi
dpkg-query -W 'ros-jazzy-*'
