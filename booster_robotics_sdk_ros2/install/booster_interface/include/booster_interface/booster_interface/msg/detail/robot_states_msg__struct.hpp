// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__booster_interface__msg__RobotStatesMsg __attribute__((deprecated))
#else
# define DEPRECATED__booster_interface__msg__RobotStatesMsg __declspec(deprecated)
#endif

namespace booster_interface
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct RobotStatesMsg_
{
  using Type = RobotStatesMsg_<ContainerAllocator>;

  explicit RobotStatesMsg_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->current_mode = 0l;
      this->current_body_control = 0l;
    }
  }

  explicit RobotStatesMsg_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->current_mode = 0l;
      this->current_body_control = 0l;
    }
  }

  // field types and members
  using _current_mode_type =
    int32_t;
  _current_mode_type current_mode;
  using _current_body_control_type =
    int32_t;
  _current_body_control_type current_body_control;
  using _current_actions_type =
    std::vector<int32_t, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<int32_t>>;
  _current_actions_type current_actions;

  // setters for named parameter idiom
  Type & set__current_mode(
    const int32_t & _arg)
  {
    this->current_mode = _arg;
    return *this;
  }
  Type & set__current_body_control(
    const int32_t & _arg)
  {
    this->current_body_control = _arg;
    return *this;
  }
  Type & set__current_actions(
    const std::vector<int32_t, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<int32_t>> & _arg)
  {
    this->current_actions = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    booster_interface::msg::RobotStatesMsg_<ContainerAllocator> *;
  using ConstRawPtr =
    const booster_interface::msg::RobotStatesMsg_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::RobotStatesMsg_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::RobotStatesMsg_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__booster_interface__msg__RobotStatesMsg
    std::shared_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__booster_interface__msg__RobotStatesMsg
    std::shared_ptr<booster_interface::msg::RobotStatesMsg_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const RobotStatesMsg_ & other) const
  {
    if (this->current_mode != other.current_mode) {
      return false;
    }
    if (this->current_body_control != other.current_body_control) {
      return false;
    }
    if (this->current_actions != other.current_actions) {
      return false;
    }
    return true;
  }
  bool operator!=(const RobotStatesMsg_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct RobotStatesMsg_

// alias to use template instance with default allocator
using RobotStatesMsg =
  booster_interface::msg::RobotStatesMsg_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_HPP_
