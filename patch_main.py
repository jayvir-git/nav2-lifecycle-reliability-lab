"""Port the coordinated experiment to the pinned main API, preserving timeouts."""
from pathlib import Path
import subprocess
import sys

subprocess.run([sys.executable,str(Path(__file__).with_name('patch_coordinated.py')),
                sys.argv[1],'--upstream-main'],check=True)
header=Path(sys.argv[1])/'nav2_lifecycle_manager/include/nav2_lifecycle_manager/shutdown_lifecycle_client.hpp'
s=header.read_text()
s=s.replace('class ShutdownLifecycleClient {', '''class ShutdownCancelled : public std::runtime_error {
public:
  ShutdownCancelled() : std::runtime_error("Lifecycle wait cancelled by shutdown") {}
};
class ShutdownLifecycleClient {''')
s=s.replace('bool change_state(uint8_t transition) {', '''bool change_state(uint8_t transition,
    std::chrono::milliseconds transition_timeout = std::chrono::milliseconds(0),
    std::chrono::milliseconds discovery_timeout = std::chrono::seconds(5)) {''')
s=s.replace('invoke<Change>(change_, request, std::chrono::seconds(5),\n      std::chrono::nanoseconds(-1))', '''invoke<Change>(change_, request, discovery_timeout,
      transition_timeout.count() > 0 ? std::chrono::duration_cast<std::chrono::nanoseconds>(transition_timeout) :
      std::chrono::nanoseconds(-1))''')
s=s.replace('uint8_t get_state() {', 'uint8_t get_state(std::chrono::milliseconds timeout = std::chrono::seconds(2)) {')
s=s.replace('std::chrono::seconds(2), std::chrono::seconds(2))->current_state.id;', 'timeout, timeout)->current_state.id;')
s=s.replace('throw std::runtime_error("Lifecycle service wait interrupted by shutdown");','throw ShutdownCancelled();')
s=s.replace(': stopping_(stopping) {', '''
  : stopping_(stopping), context_(node->get_node_base_interface()->get_context()),
    executor_(executor_options(context_)) {''')
s=s.replace('!rclcpp::ok()', '!rclcpp::ok(context_)')
s=s.replace('private:\n  void check_stop()', '''private:
  static rclcpp::ExecutorOptions executor_options(rclcpp::Context::SharedPtr context) {
    rclcpp::ExecutorOptions options;
    options.context = context;
    return options;
  }
  void check_stop()''')
s=s.replace('  rclcpp::CallbackGroup::SharedPtr group_;', '  rclcpp::Context::SharedPtr context_;\n  rclcpp::CallbackGroup::SharedPtr group_;')
header.write_text(s)
source=Path(sys.argv[1])/'nav2_lifecycle_manager/src/lifecycle_manager.cpp'
s=source.read_text()
s=s.replace('auto executor = std::make_shared<rclcpp::executors::SingleThreadedExecutor>();', '''rclcpp::ExecutorOptions worker_options;
      worker_options.context = get_node_base_interface()->get_context();
      auto executor = std::make_shared<rclcpp::executors::SingleThreadedExecutor>(worker_options);''')
source.write_text(s)
