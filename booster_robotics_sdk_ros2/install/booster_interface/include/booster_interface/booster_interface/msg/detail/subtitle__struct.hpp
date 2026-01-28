// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from booster_interface:msg/Subtitle.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__booster_interface__msg__Subtitle __attribute__((deprecated))
#else
# define DEPRECATED__booster_interface__msg__Subtitle __declspec(deprecated)
#endif

namespace booster_interface
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct Subtitle_
{
  using Type = Subtitle_<ContainerAllocator>;

  explicit Subtitle_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->magic_number = "";
      this->text = "";
      this->language = "";
      this->user_id = "";
      this->seq = 0l;
      this->definite = false;
      this->paragraph = false;
      this->round_id = 0l;
    }
  }

  explicit Subtitle_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : magic_number(_alloc),
    text(_alloc),
    language(_alloc),
    user_id(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->magic_number = "";
      this->text = "";
      this->language = "";
      this->user_id = "";
      this->seq = 0l;
      this->definite = false;
      this->paragraph = false;
      this->round_id = 0l;
    }
  }

  // field types and members
  using _magic_number_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _magic_number_type magic_number;
  using _text_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _text_type text;
  using _language_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _language_type language;
  using _user_id_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _user_id_type user_id;
  using _seq_type =
    int32_t;
  _seq_type seq;
  using _definite_type =
    bool;
  _definite_type definite;
  using _paragraph_type =
    bool;
  _paragraph_type paragraph;
  using _round_id_type =
    int32_t;
  _round_id_type round_id;

  // setters for named parameter idiom
  Type & set__magic_number(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->magic_number = _arg;
    return *this;
  }
  Type & set__text(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->text = _arg;
    return *this;
  }
  Type & set__language(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->language = _arg;
    return *this;
  }
  Type & set__user_id(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->user_id = _arg;
    return *this;
  }
  Type & set__seq(
    const int32_t & _arg)
  {
    this->seq = _arg;
    return *this;
  }
  Type & set__definite(
    const bool & _arg)
  {
    this->definite = _arg;
    return *this;
  }
  Type & set__paragraph(
    const bool & _arg)
  {
    this->paragraph = _arg;
    return *this;
  }
  Type & set__round_id(
    const int32_t & _arg)
  {
    this->round_id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    booster_interface::msg::Subtitle_<ContainerAllocator> *;
  using ConstRawPtr =
    const booster_interface::msg::Subtitle_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<booster_interface::msg::Subtitle_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<booster_interface::msg::Subtitle_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::Subtitle_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::Subtitle_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::Subtitle_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::Subtitle_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<booster_interface::msg::Subtitle_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<booster_interface::msg::Subtitle_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__booster_interface__msg__Subtitle
    std::shared_ptr<booster_interface::msg::Subtitle_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__booster_interface__msg__Subtitle
    std::shared_ptr<booster_interface::msg::Subtitle_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const Subtitle_ & other) const
  {
    if (this->magic_number != other.magic_number) {
      return false;
    }
    if (this->text != other.text) {
      return false;
    }
    if (this->language != other.language) {
      return false;
    }
    if (this->user_id != other.user_id) {
      return false;
    }
    if (this->seq != other.seq) {
      return false;
    }
    if (this->definite != other.definite) {
      return false;
    }
    if (this->paragraph != other.paragraph) {
      return false;
    }
    if (this->round_id != other.round_id) {
      return false;
    }
    return true;
  }
  bool operator!=(const Subtitle_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct Subtitle_

// alias to use template instance with default allocator
using Subtitle =
  booster_interface::msg::Subtitle_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_HPP_
