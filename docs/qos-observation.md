# Observed service QoS: middleware defaults are not service defaults

The upstream `nav2_ros_common` service client explicitly creates clients with `rclcpp::ServicesQoS()`. The experimental replacement originally used `rclcpp::SystemDefaultsQoS()`. Those do not resolve to equivalent settings in our environment.

The attached `qos-observation.cpp` creates real ROS clients with each profile and queries `get_request_publisher_actual_qos()` and `get_response_subscription_actual_qos()`. It does not send requests or inject a failure.

Observed output on WSL/Jazzy, `rclcpp 28.1.22` and `rmw_fastrtps_cpp 8.4.4`:

```text
SystemDefaultsQoS request reliability=1 depth=1 durability=1 response reliability=2 depth=1 durability=2
ServicesQoS request reliability=1 depth=10 durability=2 response reliability=1 depth=10 durability=2
```

The installed `rmw/types.h` defines reliability 1 as reliable and 2 as best effort; durability 1 is transient local and 2 is volatile. Thus the middleware-default response subscription was best effort with depth 1, whereas the explicit service profile was reliable with depth 10. The request durability and depth differed as well.

This establishes a concrete compatibility difference. It does **not** prove that a particular response was lost or that this caused every earlier startup timeout. No packet trace or deterministic loss experiment was captured. Default resolutions may differ with middleware or configuration.

The final main-source candidate now uses `ServicesQoS()`, matching the upstream client at the pinned source revision. Its later validation results are recorded in the milestone evidence, with earlier failures preserved.

To reproduce, copy `qos-observation.cpp` as `main.cpp` and `qos-observation-CMakeLists.txt` as `CMakeLists.txt` into an empty build project, source the ROS environment, then run:

```bash
cmake -S . -B build
cmake --build build
./build/qos_observation
```

The observation's CMake file records the original Jazzy build recipe. On distributions that removed `ament_target_dependencies`, link the exported `rclcpp::rclcpp` and `lifecycle_msgs::lifecycle_msgs` targets instead.
