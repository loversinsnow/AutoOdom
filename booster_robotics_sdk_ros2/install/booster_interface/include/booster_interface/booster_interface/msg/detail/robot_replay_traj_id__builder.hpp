// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from booster_interface:msg/RobotReplayTrajID.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__BUILDER_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "booster_interface/msg/detail/robot_replay_traj_id__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace booster_interface
{

namespace msg
{

namespace builder
{

class Init_RobotReplayTrajID_id
{
public:
  Init_RobotReplayTrajID_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::booster_interface::msg::RobotReplayTrajID id(::booster_interface::msg::RobotReplayTrajID::_id_type arg)
  {
    msg_.id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::booster_interface::msg::RobotReplayTrajID msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::booster_interface::msg::RobotReplayTrajID>()
{
  return booster_interface::msg::builder::Init_RobotReplayTrajID_id();
}

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__BUILDER_HPP_
