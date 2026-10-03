#include <iostream>
#include "rclcpp/rclcpp.hpp"
#include "lifecycle_msgs/srv/get_state.hpp"
int main(int argc, char **argv) {
 rclcpp::init(argc,argv); auto node=std::make_shared<rclcpp::Node>("qos_observation");
 for(bool service : {false,true}) {
  auto client=node->create_client<lifecycle_msgs::srv::GetState>(service?"service_profile":"system_profile",service?rclcpp::QoS(rclcpp::ServicesQoS()):rclcpp::QoS(rclcpp::SystemDefaultsQoS()));
  auto req=client->get_request_publisher_actual_qos().get_rmw_qos_profile();
  auto res=client->get_response_subscription_actual_qos().get_rmw_qos_profile();
  std::cout << (service?"ServicesQoS":"SystemDefaultsQoS") << " request reliability=" << req.reliability << " depth=" << req.depth << " durability=" << req.durability << " response reliability=" << res.reliability << " depth=" << res.depth << " durability=" << res.durability << std::endl;
 }
 rclcpp::shutdown();
}
