// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from booster_interface:msg/Subtitle.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__TRAITS_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "booster_interface/msg/detail/subtitle__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace booster_interface
{

namespace msg
{

inline void to_flow_style_yaml(
  const Subtitle & msg,
  std::ostream & out)
{
  out << "{";
  // member: magic_number
  {
    out << "magic_number: ";
    rosidl_generator_traits::value_to_yaml(msg.magic_number, out);
    out << ", ";
  }

  // member: text
  {
    out << "text: ";
    rosidl_generator_traits::value_to_yaml(msg.text, out);
    out << ", ";
  }

  // member: language
  {
    out << "language: ";
    rosidl_generator_traits::value_to_yaml(msg.language, out);
    out << ", ";
  }

  // member: user_id
  {
    out << "user_id: ";
    rosidl_generator_traits::value_to_yaml(msg.user_id, out);
    out << ", ";
  }

  // member: seq
  {
    out << "seq: ";
    rosidl_generator_traits::value_to_yaml(msg.seq, out);
    out << ", ";
  }

  // member: definite
  {
    out << "definite: ";
    rosidl_generator_traits::value_to_yaml(msg.definite, out);
    out << ", ";
  }

  // member: paragraph
  {
    out << "paragraph: ";
    rosidl_generator_traits::value_to_yaml(msg.paragraph, out);
    out << ", ";
  }

  // member: round_id
  {
    out << "round_id: ";
    rosidl_generator_traits::value_to_yaml(msg.round_id, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Subtitle & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: magic_number
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "magic_number: ";
    rosidl_generator_traits::value_to_yaml(msg.magic_number, out);
    out << "\n";
  }

  // member: text
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "text: ";
    rosidl_generator_traits::value_to_yaml(msg.text, out);
    out << "\n";
  }

  // member: language
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "language: ";
    rosidl_generator_traits::value_to_yaml(msg.language, out);
    out << "\n";
  }

  // member: user_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "user_id: ";
    rosidl_generator_traits::value_to_yaml(msg.user_id, out);
    out << "\n";
  }

  // member: seq
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "seq: ";
    rosidl_generator_traits::value_to_yaml(msg.seq, out);
    out << "\n";
  }

  // member: definite
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "definite: ";
    rosidl_generator_traits::value_to_yaml(msg.definite, out);
    out << "\n";
  }

  // member: paragraph
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "paragraph: ";
    rosidl_generator_traits::value_to_yaml(msg.paragraph, out);
    out << "\n";
  }

  // member: round_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "round_id: ";
    rosidl_generator_traits::value_to_yaml(msg.round_id, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Subtitle & msg, bool use_flow_style = false)
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
  const booster_interface::msg::Subtitle & msg,
  std::ostream & out, size_t indentation = 0)
{
  booster_interface::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use booster_interface::msg::to_yaml() instead")]]
inline std::string to_yaml(const booster_interface::msg::Subtitle & msg)
{
  return booster_interface::msg::to_yaml(msg);
}

template<>
inline const char * data_type<booster_interface::msg::Subtitle>()
{
  return "booster_interface::msg::Subtitle";
}

template<>
inline const char * name<booster_interface::msg::Subtitle>()
{
  return "booster_interface/msg/Subtitle";
}

template<>
struct has_fixed_size<booster_interface::msg::Subtitle>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<booster_interface::msg::Subtitle>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<booster_interface::msg::Subtitle>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__TRAITS_HPP_
