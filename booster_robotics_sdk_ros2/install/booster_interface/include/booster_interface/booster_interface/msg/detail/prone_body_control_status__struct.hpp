// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from booster_interface:msg/ProneBodyControlStatus.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_HPP_
#define BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__booster_interface__msg__ProneBodyControlStatus __attribute__((deprecated))
#else
# define DEPRECATED__booster_interface__msg__ProneBodyControlStatus __declspec(deprecated)
#endif

namespace booster_interface
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct ProneBodyControlStatus_
{
  using Type = ProneBodyControlStatus_<ContainerAllocator>;

  explicit ProneBodyControlStatus_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->posture = 0l;
    }
  }

  explicit ProneBodyControlStatus_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->posture = 0l;
    }
  }

  // field types and members
  using _posture_type =
    int32_t;
  _posture_type posture;

  // setters for named parameter idiom
  Type & set__posture(
    const int32_t & _arg)
  {
    this->posture = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> *;
  using ConstRawPtr =
    const booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__booster_interface__msg__ProneBodyControlStatus
    std::shared_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__booster_interface__msg__ProneBodyControlStatus
    std::shared_ptr<booster_interface::msg::ProneBodyControlStatus_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const ProneBodyControlStatus_ & other) const
  {
    if (this->posture != other.posture) {
      return false;
    }
    return true;
  }
  bool operator!=(const ProneBodyControlStatus_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct ProneBodyControlStatus_

// alias to use template instance with default allocator
using ProneBodyControlStatus =
  booster_interface::msg::ProneBodyControlStatus_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace booster_interface

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_HPP_
