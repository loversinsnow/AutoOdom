// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from booster_interface:msg/ProneBodyControlStatus.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__BUILDER_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "booster_interface/msg/detail/prone_body_control_status__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace booster_interface
{

namespace msg
{

namespace builder
{

class Init_ProneBodyControlStatus_posture
{
public:
  Init_ProneBodyControlStatus_posture()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::booster_interface::msg::ProneBodyControlStatus posture(::booster_interface::msg::ProneBodyControlStatus::_posture_type arg)
  {
    msg_.posture = std::move(arg);
    return std::move(msg_);
  }

private:
  ::booster_interface::msg::ProneBodyControlStatus msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::booster_interface::msg::ProneBodyControlStatus>()
{
  return booster_interface::msg::builder::Init_ProneBodyControlStatus_posture();
}

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__BUILDER_HPP_
