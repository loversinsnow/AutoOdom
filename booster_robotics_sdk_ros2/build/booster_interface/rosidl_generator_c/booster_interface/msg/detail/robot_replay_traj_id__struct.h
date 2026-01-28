// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from booster_interface:msg/RobotReplayTrajID.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'id'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/RobotReplayTrajID in the package booster_interface.
typedef struct booster_interface__msg__RobotReplayTrajID
{
  rosidl_runtime_c__String id;
} booster_interface__msg__RobotReplayTrajID;

// Struct for a sequence of booster_interface__msg__RobotReplayTrajID.
typedef struct booster_interface__msg__RobotReplayTrajID__Sequence
{
  booster_interface__msg__RobotReplayTrajID * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} booster_interface__msg__RobotReplayTrajID__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_REPLAY_TRAJ_ID__STRUCT_H_
