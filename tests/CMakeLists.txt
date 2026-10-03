cmake_minimum_required(VERSION 3.20)
project(shutdown_context_probe)
find_package(ament_cmake REQUIRED)
find_package(nav2_lifecycle_manager REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(context_probe context_probe.cpp)
target_link_libraries(context_probe PRIVATE
  nav2_lifecycle_manager::nav2_lifecycle_manager_core
  rclcpp::rclcpp)
target_compile_features(context_probe PRIVATE cxx_std_17)
target_compile_options(context_probe PRIVATE -Wall -Wextra -Werror)
