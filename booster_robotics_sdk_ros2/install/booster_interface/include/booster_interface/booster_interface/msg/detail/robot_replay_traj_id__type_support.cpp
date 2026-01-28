// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from booster_interface:msg/RobotReplayTrajID.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "booster_interface/msg/detail/robot_replay_traj_id__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace booster_interface
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void RobotReplayTrajID_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) booster_interface::msg::RobotReplayTrajID(_init);
}

void RobotReplayTrajID_fini_function(void * message_memory)
{
  auto typed_message = static_cast<booster_interface::msg::RobotReplayTrajID *>(message_memory);
  typed_message->~RobotReplayTrajID();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember RobotReplayTrajID_message_member_array[1] = {
  {
    "id",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(booster_interface::msg::RobotReplayTrajID, id),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers RobotReplayTrajID_message_members = {
  "booster_interface::msg",  // message namespace
  "RobotReplayTrajID",  // message name
  1,  // number of fields
  sizeof(booster_interface::msg::RobotReplayTrajID),
  RobotReplayTrajID_message_member_array,  // message members
  RobotReplayTrajID_init_function,  // function to initialize message memory (memory has to be allocated)
  RobotReplayTrajID_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t RobotReplayTrajID_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &RobotReplayTrajID_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace booster_interface


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<booster_interface::msg::RobotReplayTrajID>()
{
  return &::booster_interface::msg::rosidl_typesupport_introspection_cpp::RobotReplayTrajID_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, booster_interface, msg, RobotReplayTrajID)() {
  return &::booster_interface::msg::rosidl_typesupport_introspection_cpp::RobotReplayTrajID_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
