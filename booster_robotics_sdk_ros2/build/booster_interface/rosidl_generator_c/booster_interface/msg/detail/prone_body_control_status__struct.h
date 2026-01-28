// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from booster_interface:msg/ProneBodyControlStatus.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in msg/ProneBodyControlStatus in the package booster_interface.
typedef struct booster_interface__msg__ProneBodyControlStatus
{
  int32_t posture;
} booster_interface__msg__ProneBodyControlStatus;

// Struct for a sequence of booster_interface__msg__ProneBodyControlStatus.
typedef struct booster_interface__msg__ProneBodyControlStatus__Sequence
{
  booster_interface__msg__ProneBodyControlStatus * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} booster_interface__msg__ProneBodyControlStatus__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__PRONE_BODY_CONTROL_STATUS__STRUCT_H_
