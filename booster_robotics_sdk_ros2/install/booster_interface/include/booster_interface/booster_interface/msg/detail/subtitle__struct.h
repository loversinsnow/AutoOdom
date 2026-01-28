// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from booster_interface:msg/Subtitle.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

// Include directives for member types
// Member 'magic_number'
// Member 'text'
// Member 'language'
// Member 'user_id'
#include "rosidl_runtime_c/string.h"

/// Struct defined in msg/Subtitle in the package booster_interface.
typedef struct booster_interface__msg__Subtitle
{
  rosidl_runtime_c__String magic_number;
  rosidl_runtime_c__String text;
  rosidl_runtime_c__String language;
  rosidl_runtime_c__String user_id;
  int32_t seq;
  bool definite;
  bool paragraph;
  int32_t round_id;
} booster_interface__msg__Subtitle;

// Struct for a sequence of booster_interface__msg__Subtitle.
typedef struct booster_interface__msg__Subtitle__Sequence
{
  booster_interface__msg__Subtitle * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} booster_interface__msg__Subtitle__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__SUBTITLE__STRUCT_H_
