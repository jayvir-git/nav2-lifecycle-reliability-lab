// Experimental manager-local client. No changes to installed nav2_util ABI.
#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <memory>
#include <stdexcept>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "lifecycle_msgs/srv/change_state.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"

namespace nav2_lifecycle_manager {
class ShutdownLifecycleClient {
  using Change = lifecycle_msgs::srv::ChangeState;
  using State = lifecycle_msgs::srv::GetState;
public:
  ShutdownLifecycleClient(const std::string & name, rclcpp::Node::SharedPtr node,
    std::shared_ptr<std::atomic_bool> stopping)
  : stopping_(stopping) {
    group_ = node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive, false);
    executor_.add_callback_group(group_, node->get_node_base_interface());
    change_ = node->create_client<Change>(name + "/change_state", rclcpp::SystemDefaultsQoS(), group_);
    state_ = node->create_client<State>(name + "/get_state", rclcpp::SystemDefaultsQoS(), group_);
    while (!discover<State>(state_, std::chrono::seconds(2))) { check_stop(); }
  }
  bool change_state(uint8_t transition) {
    auto request = std::make_shared<Change::Request>();
    request->transition.id = transition;
    return invoke<Change>(change_, request, std::chrono::seconds(5),
      std::chrono::nanoseconds(-1))->success;
  }
  uint8_t get_state() {
    return invoke<State>(state_, std::make_shared<State::Request>(),
      std::chrono::seconds(2), std::chrono::seconds(2))->current_state.id;
  }
private:
  void check_stop() const {
    if (stopping_->load() || !rclcpp::ok()) {
      throw std::runtime_error("Lifecycle service wait interrupted by shutdown");
    }
  }
  template<class Service>
  bool discover(typename rclcpp::Client<Service>::SharedPtr client,
    std::chrono::nanoseconds timeout) {
    const auto start = std::chrono::steady_clock::now();
    while (true) {
      check_stop();
      if (client->service_is_ready()) { return true; }
      const auto elapsed = std::chrono::steady_clock::now() - start;
      if (elapsed >= timeout) { return false; }
      const auto remaining = timeout - elapsed;
      client->wait_for_service(std::min(remaining,
        std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::milliseconds(50))));
    }
  }
  template<class Service>
  typename Service::Response::SharedPtr invoke(
    typename rclcpp::Client<Service>::SharedPtr client,
    typename Service::Request::SharedPtr request,
    std::chrono::nanoseconds discovery_timeout, std::chrono::nanoseconds response_timeout) {
    if (!discover<Service>(client, discovery_timeout)) {
      throw std::runtime_error("Lifecycle service unavailable");
    }
    check_stop();
    auto future = client->async_send_request(request);
    const auto start = std::chrono::steady_clock::now();
    try {
      while (true) {
        check_stop();
        auto slice = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::milliseconds(50));
        if (response_timeout.count() >= 0) {
          const auto elapsed = std::chrono::steady_clock::now() - start;
          if (elapsed >= response_timeout) { throw std::runtime_error("Lifecycle response timed out"); }
          slice = std::min(slice, response_timeout - elapsed);
        }
        auto status = executor_.spin_until_future_complete(future, slice);
        if (status == rclcpp::FutureReturnCode::SUCCESS) { return future.get(); }
        if (status == rclcpp::FutureReturnCode::INTERRUPTED) {
          throw std::runtime_error("Lifecycle executor interrupted");
        }
      }
    } catch (...) {
      client->remove_pending_request(future);
      throw;
    }
  }
  std::shared_ptr<std::atomic_bool> stopping_;
  rclcpp::CallbackGroup::SharedPtr group_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  rclcpp::Client<Change>::SharedPtr change_;
  rclcpp::Client<State>::SharedPtr state_;
};
} // namespace nav2_lifecycle_manager
