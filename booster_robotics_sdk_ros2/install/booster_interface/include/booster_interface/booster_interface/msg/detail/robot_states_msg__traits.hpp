// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__TRAITS_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "booster_interface/msg/detail/robot_states_msg__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace booster_interface
{

namespace msg
{

inline void to_flow_style_yaml(
  const RobotStatesMsg & msg,
  std::ostream & out)
{
  out << "{";
  // member: current_mode
  {
    out << "current_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.current_mode, out);
    out << ", ";
  }

  // member: current_body_control
  {
    out << "current_body_control: ";
    rosidl_generator_traits::value_to_yaml(msg.current_body_control, out);
    out << ", ";
  }

  // member: current_actions
  {
    if (msg.current_actions.size() == 0) {
      out << "current_actions: []";
    } else {
      out << "current_actions: [";
      size_t pending_items = msg.current_actions.size();
      for (auto item : msg.current_actions) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const RobotStatesMsg & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: current_mode
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "current_mode: ";
    rosidl_generator_traits::value_to_yaml(msg.current_mode, out);
    out << "\n";
  }

  // member: current_body_control
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "current_body_control: ";
    rosidl_generator_traits::value_to_yaml(msg.current_body_control, out);
    out << "\n";
  }

  // member: current_actions
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.current_actions.size() == 0) {
      out << "current_actions: []\n";
    } else {
      out << "current_actions:\n";
      for (auto item : msg.current_actions) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const RobotStatesMsg & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace booster_interface

namespace rosidl_generator_traits
{

[[deprecated("use booster_interface::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const booster_interface::msg::RobotStatesMsg & msg,
  std::ostream & out, size_t indentation = 0)
{
  booster_interface::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use booster_interface::msg::to_yaml() instead")]]
inline std::string to_yaml(const booster_interface::msg::RobotStatesMsg & msg)
{
  return booster_interface::msg::to_yaml(msg);
}

template<>
inline const char * data_type<booster_interface::msg::RobotStatesMsg>()
{
  return "booster_interface::msg::RobotStatesMsg";
}

template<>
inline const char * name<booster_interface::msg::RobotStatesMsg>()
{
  return "booster_interface/msg/RobotStatesMsg";
}

template<>
struct has_fixed_size<booster_interface::msg::RobotStatesMsg>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<booster_interface::msg::RobotStatesMsg>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<booster_interface::msg::RobotStatesMsg>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__TRAITS_HPP_
