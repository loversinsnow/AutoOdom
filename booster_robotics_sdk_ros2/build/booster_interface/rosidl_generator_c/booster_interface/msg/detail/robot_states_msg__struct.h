// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'current_actions'
#include "rosidl_runtime_c/primitives_sequence.h"

/// Struct defined in msg/RobotStatesMsg in the package booster_interface.
typedef struct booster_interface__msg__RobotStatesMsg
{
  /// fields
  int32_t current_mode;
  int32_t current_body_control;
  rosidl_runtime_c__int32__Sequence current_actions;
} booster_interface__msg__RobotStatesMsg;

// Struct for a sequence of booster_interface__msg__RobotStatesMsg.
typedef struct booster_interface__msg__RobotStatesMsg__Sequence
{
  booster_interface__msg__RobotStatesMsg * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} booster_interface__msg__RobotStatesMsg__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__STRUCT_H_
