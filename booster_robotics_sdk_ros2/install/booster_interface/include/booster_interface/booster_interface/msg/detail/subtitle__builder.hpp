// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from booster_interface:msg/Subtitle.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__BUILDER_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "booster_interface/msg/detail/subtitle__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace booster_interface
{

namespace msg
{

namespace builder
{

class Init_Subtitle_round_id
{
public:
  explicit Init_Subtitle_round_id(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  ::booster_interface::msg::Subtitle round_id(::booster_interface::msg::Subtitle::_round_id_type arg)
  {
    msg_.round_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_paragraph
{
public:
  explicit Init_Subtitle_paragraph(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_round_id paragraph(::booster_interface::msg::Subtitle::_paragraph_type arg)
  {
    msg_.paragraph = std::move(arg);
    return Init_Subtitle_round_id(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_definite
{
public:
  explicit Init_Subtitle_definite(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_paragraph definite(::booster_interface::msg::Subtitle::_definite_type arg)
  {
    msg_.definite = std::move(arg);
    return Init_Subtitle_paragraph(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_seq
{
public:
  explicit Init_Subtitle_seq(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_definite seq(::booster_interface::msg::Subtitle::_seq_type arg)
  {
    msg_.seq = std::move(arg);
    return Init_Subtitle_definite(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_user_id
{
public:
  explicit Init_Subtitle_user_id(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_seq user_id(::booster_interface::msg::Subtitle::_user_id_type arg)
  {
    msg_.user_id = std::move(arg);
    return Init_Subtitle_seq(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_language
{
public:
  explicit Init_Subtitle_language(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_user_id language(::booster_interface::msg::Subtitle::_language_type arg)
  {
    msg_.language = std::move(arg);
    return Init_Subtitle_user_id(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_text
{
public:
  explicit Init_Subtitle_text(::booster_interface::msg::Subtitle & msg)
  : msg_(msg)
  {}
  Init_Subtitle_language text(::booster_interface::msg::Subtitle::_text_type arg)
  {
    msg_.text = std::move(arg);
    return Init_Subtitle_language(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

class Init_Subtitle_magic_number
{
public:
  Init_Subtitle_magic_number()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_Subtitle_text magic_number(::booster_interface::msg::Subtitle::_magic_number_type arg)
  {
    msg_.magic_number = std::move(arg);
    return Init_Subtitle_text(msg_);
  }

private:
  ::booster_interface::msg::Subtitle msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::booster_interface::msg::Subtitle>()
{
  return booster_interface::msg::builder::Init_Subtitle_magic_number();
}

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__BUILDER_HPP_
