// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from booster_interface:msg/RobotReplayTrajID.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__booster_interface__msg__RobotReplayTrajID __attribute__((deprecated))
#else
# define DEPRECATED__booster_interface__msg__RobotReplayTrajID __declspec(deprecated)
#endif

namespace booster_interface
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct RobotReplayTrajID_
{
  using Type = RobotReplayTrajID_<ContainerAllocator>;

  explicit RobotReplayTrajID_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = "";
    }
  }

  explicit RobotReplayTrajID_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : id(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->id = "";
    }
  }

  // field types and members
  using _id_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _id_type id;

  // setters for named parameter idiom
  Type & set__id(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> *;
  using ConstRawPtr =
    const booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__booster_interface__msg__RobotReplayTrajID
    std::shared_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__booster_interface__msg__RobotReplayTrajID
    std::shared_ptr<booster_interface::msg::RobotReplayTrajID_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const RobotReplayTrajID_ & other) const
  {
    if (this->id != other.id) {
      return false;
    }
    return true;
  }
  bool operator!=(const RobotReplayTrajID_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct RobotReplayTrajID_

// alias to use template instance with default allocator
using RobotReplayTrajID =
  booster_interface::msg::RobotReplayTrajID_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_HPP_
