// Public API test: embed the real manager in a non-default ROS context.
#include <chrono>
#include <exception>
#include <iostream>
#include <thread>
#include <atomic>
#include "rclcpp/rclcpp.hpp"
#include "nav2_lifecycle_manager/lifecycle_manager.hpp"
using namespace std::chrono_literals;
int main(int argc, char ** argv)
{
  const std::string mode = argc > 1 ? argv[1] : "discovery";
  if (mode != "discovery" && mode != "empty" && mode != "before-spin") {return 4;}
  const bool discovery = mode == "discovery";
  const int delay_ms = argc > 2 ? std::stoi(argv[2]) : 0;
  if (delay_ms < 0 || delay_ms > 2000) {return 4;}
  auto context = std::make_shared<rclcpp::Context>();
  context->init(0, nullptr);  // Deliberately never initialize the global context.
  rclcpp::NodeOptions options;
  options.context(context);
  options.parameter_overrides({rclcpp::Parameter("node_names", discovery ?
    std::vector<std::string>{"absent_context_server"} : std::vector<std::string>{}),
    rclcpp::Parameter("autostart", true)});
  auto manager = std::make_shared<nav2_lifecycle_manager::LifecycleManager>(options);
  rclcpp::ExecutorOptions executor_options; executor_options.context = context;
  rclcpp::executors::MultiThreadedExecutor executor(executor_options, 2);
  executor.add_node(manager);
  if (mode == "before-spin") {
    context->shutdown("before first executor spin");
    std::cout << "CONTEXT_SHUTDOWN_OK before-spin" << std::endl;
    return 0;
  }
  std::exception_ptr error;
  std::atomic_bool failed{false};
  std::thread spin([&] {
    try {executor.spin();} catch (const std::exception & e) {
      std::cerr << "SPIN_ERROR: " << e.what() << std::endl;
      error = std::current_exception(); failed = true;
    }
  });
  bool ready = false;
  const auto deadline = std::chrono::steady_clock::now() + 5s;
  while (!failed && std::chrono::steady_clock::now() < deadline) {
    if (discovery) {
      try {
        auto clients = manager->get_node_graph_interface()->get_client_names_and_types_by_node("lifecycle_manager", "/");
        ready = clients.count("/absent_context_server/get_state") != 0;
      } catch (const std::exception &) {
        // DDS graph discovery may not have observed the newly constructed node yet.
      }
    } else {
      ready = manager->get_service_names_and_types().count("/lifecycle_manager/manage_nodes") != 0;
    }
    if (ready) {break;}
    std::this_thread::sleep_for(5ms);
  }
  std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
  const auto start = std::chrono::steady_clock::now();
  context->shutdown("context regression probe");
  executor.cancel(); spin.join();
  if (error) {
    try {std::rethrow_exception(error);} catch (const std::exception & e) {
      std::cerr << "EXECUTOR_ERROR: " << e.what() << std::endl;
    }
    return 1;
  }
  if (!ready) {std::cerr << "SETUP_NOT_REACHED" << std::endl; return 2;}
  const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  std::cout << "CONTEXT_SHUTDOWN_OK " << elapsed << std::endl;
  return elapsed < 2.0 ? 0 : 3;
}
