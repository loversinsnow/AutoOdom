// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__BUILDER_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "booster_interface/msg/detail/robot_states_msg__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace booster_interface
{

namespace msg
{

namespace builder
{

class Init_RobotStatesMsg_current_actions
{
public:
  explicit Init_RobotStatesMsg_current_actions(::booster_interface::msg::RobotStatesMsg & msg)
  : msg_(msg)
  {}
  ::booster_interface::msg::RobotStatesMsg current_actions(::booster_interface::msg::RobotStatesMsg::_current_actions_type arg)
  {
    msg_.current_actions = std::move(arg);
    return std::move(msg_);
  }

private:
  ::booster_interface::msg::RobotStatesMsg msg_;
};

class Init_RobotStatesMsg_current_body_control
{
public:
  explicit Init_RobotStatesMsg_current_body_control(::booster_interface::msg::RobotStatesMsg & msg)
  : msg_(msg)
  {}
  Init_RobotStatesMsg_current_actions current_body_control(::booster_interface::msg::RobotStatesMsg::_current_body_control_type arg)
  {
    msg_.current_body_control = std::move(arg);
    return Init_RobotStatesMsg_current_actions(msg_);
  }

private:
  ::booster_interface::msg::RobotStatesMsg msg_;
};

class Init_RobotStatesMsg_current_mode
{
public:
  Init_RobotStatesMsg_current_mode()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_RobotStatesMsg_current_body_control current_mode(::booster_interface::msg::RobotStatesMsg::_current_mode_type arg)
  {
    msg_.current_mode = std::move(arg);
    return Init_RobotStatesMsg_current_body_control(msg_);
  }

private:
  ::booster_interface::msg::RobotStatesMsg msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::booster_interface::msg::RobotStatesMsg>()
{
  return booster_interface::msg::builder::Init_RobotStatesMsg_current_mode();
}

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__BUILDER_HPP_
