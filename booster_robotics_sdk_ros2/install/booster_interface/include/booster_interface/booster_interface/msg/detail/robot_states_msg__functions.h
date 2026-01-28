// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice

#ifndef BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__FUNCTIONS_H_
#define BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "booster_interface/msg/rosidl_generator_c__visibility_control.h"

#include "booster_interface/msg/detail/robot_states_msg__struct.h"

/// Initialize msg/RobotStatesMsg message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * booster_interface__msg__RobotStatesMsg
 * )) before or use
 * booster_interface__msg__RobotStatesMsg__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__init(booster_interface__msg__RobotStatesMsg * msg);

/// Finalize msg/RobotStatesMsg message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
void
booster_interface__msg__RobotStatesMsg__fini(booster_interface__msg__RobotStatesMsg * msg);

/// Create msg/RobotStatesMsg message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * booster_interface__msg__RobotStatesMsg__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
booster_interface__msg__RobotStatesMsg *
booster_interface__msg__RobotStatesMsg__create();

/// Destroy msg/RobotStatesMsg message.
/**
 * It calls
 * booster_interface__msg__RobotStatesMsg__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
void
booster_interface__msg__RobotStatesMsg__destroy(booster_interface__msg__RobotStatesMsg * msg);

/// Check for msg/RobotStatesMsg message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__are_equal(const booster_interface__msg__RobotStatesMsg * lhs, const booster_interface__msg__RobotStatesMsg * rhs);

/// Copy a msg/RobotStatesMsg message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__copy(
  const booster_interface__msg__RobotStatesMsg * input,
  booster_interface__msg__RobotStatesMsg * output);

/// Initialize array of msg/RobotStatesMsg messages.
/**
 * It allocates the memory for the number of elements and calls
 * booster_interface__msg__RobotStatesMsg__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__Sequence__init(booster_interface__msg__RobotStatesMsg__Sequence * array, size_t size);

/// Finalize array of msg/RobotStatesMsg messages.
/**
 * It calls
 * booster_interface__msg__RobotStatesMsg__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
void
booster_interface__msg__RobotStatesMsg__Sequence__fini(booster_interface__msg__RobotStatesMsg__Sequence * array);

/// Create array of msg/RobotStatesMsg messages.
/**
 * It allocates the memory for the array and calls
 * booster_interface__msg__RobotStatesMsg__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
booster_interface__msg__RobotStatesMsg__Sequence *
booster_interface__msg__RobotStatesMsg__Sequence__create(size_t size);

/// Destroy array of msg/RobotStatesMsg messages.
/**
 * It calls
 * booster_interface__msg__RobotStatesMsg__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
void
booster_interface__msg__RobotStatesMsg__Sequence__destroy(booster_interface__msg__RobotStatesMsg__Sequence * array);

/// Check for msg/RobotStatesMsg message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__Sequence__are_equal(const booster_interface__msg__RobotStatesMsg__Sequence * lhs, const booster_interface__msg__RobotStatesMsg__Sequence * rhs);

/// Copy an array of msg/RobotStatesMsg messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_booster_interface
bool
booster_interface__msg__RobotStatesMsg__Sequence__copy(
  const booster_interface__msg__RobotStatesMsg__Sequence * input,
  booster_interface__msg__RobotStatesMsg__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // BOOSTER_INTERFACE__MSG__DETAIL__ROBOT_STATES_MSG__FUNCTIONS_H_
