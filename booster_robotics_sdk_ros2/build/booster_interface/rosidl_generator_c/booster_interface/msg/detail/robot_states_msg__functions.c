// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from booster_interface:msg/RobotStatesMsg.idl
// generated code does not contain a copyright notice
#include "booster_interface/msg/detail/robot_states_msg__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `current_actions`
#include "rosidl_runtime_c/primitives_sequence_functions.h"

bool
booster_interface__msg__RobotStatesMsg__init(booster_interface__msg__RobotStatesMsg * msg)
{
  if (!msg) {
    return false;
  }
  // current_mode
  // current_body_control
  // current_actions
  if (!rosidl_runtime_c__int32__Sequence__init(&msg->current_actions, 0)) {
    booster_interface__msg__RobotStatesMsg__fini(msg);
    return false;
  }
  return true;
}

void
booster_interface__msg__RobotStatesMsg__fini(booster_interface__msg__RobotStatesMsg * msg)
{
  if (!msg) {
    return;
  }
  // current_mode
  // current_body_control
  // current_actions
  rosidl_runtime_c__int32__Sequence__fini(&msg->current_actions);
}

bool
booster_interface__msg__RobotStatesMsg__are_equal(const booster_interface__msg__RobotStatesMsg * lhs, const booster_interface__msg__RobotStatesMsg * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // current_mode
  if (lhs->current_mode != rhs->current_mode) {
    return false;
  }
  // current_body_control
  if (lhs->current_body_control != rhs->current_body_control) {
    return false;
  }
  // current_actions
  if (!rosidl_runtime_c__int32__Sequence__are_equal(
      &(lhs->current_actions), &(rhs->current_actions)))
  {
    return false;
  }
  return true;
}

bool
booster_interface__msg__RobotStatesMsg__copy(
  const booster_interface__msg__RobotStatesMsg * input,
  booster_interface__msg__RobotStatesMsg * output)
{
  if (!input || !output) {
    return false;
  }
  // current_mode
  output->current_mode = input->current_mode;
  // current_body_control
  output->current_body_control = input->current_body_control;
  // current_actions
  if (!rosidl_runtime_c__int32__Sequence__copy(
      &(input->current_actions), &(output->current_actions)))
  {
    return false;
  }
  return true;
}

booster_interface__msg__RobotStatesMsg *
booster_interface__msg__RobotStatesMsg__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__RobotStatesMsg * msg = (booster_interface__msg__RobotStatesMsg *)allocator.allocate(sizeof(booster_interface__msg__RobotStatesMsg), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(booster_interface__msg__RobotStatesMsg));
  bool success = booster_interface__msg__RobotStatesMsg__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
booster_interface__msg__RobotStatesMsg__destroy(booster_interface__msg__RobotStatesMsg * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    booster_interface__msg__RobotStatesMsg__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
booster_interface__msg__RobotStatesMsg__Sequence__init(booster_interface__msg__RobotStatesMsg__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__RobotStatesMsg * data = NULL;

  if (size) {
    data = (booster_interface__msg__RobotStatesMsg *)allocator.zero_allocate(size, sizeof(booster_interface__msg__RobotStatesMsg), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = booster_interface__msg__RobotStatesMsg__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        booster_interface__msg__RobotStatesMsg__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
booster_interface__msg__RobotStatesMsg__Sequence__fini(booster_interface__msg__RobotStatesMsg__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      booster_interface__msg__RobotStatesMsg__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

booster_interface__msg__RobotStatesMsg__Sequence *
booster_interface__msg__RobotStatesMsg__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__RobotStatesMsg__Sequence * array = (booster_interface__msg__RobotStatesMsg__Sequence *)allocator.allocate(sizeof(booster_interface__msg__RobotStatesMsg__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = booster_interface__msg__RobotStatesMsg__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
booster_interface__msg__RobotStatesMsg__Sequence__destroy(booster_interface__msg__RobotStatesMsg__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    booster_interface__msg__RobotStatesMsg__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
booster_interface__msg__RobotStatesMsg__Sequence__are_equal(const booster_interface__msg__RobotStatesMsg__Sequence * lhs, const booster_interface__msg__RobotStatesMsg__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!booster_interface__msg__RobotStatesMsg__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
booster_interface__msg__RobotStatesMsg__Sequence__copy(
  const booster_interface__msg__RobotStatesMsg__Sequence * input,
  booster_interface__msg__RobotStatesMsg__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(booster_interface__msg__RobotStatesMsg);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    booster_interface__msg__RobotStatesMsg * data =
      (booster_interface__msg__RobotStatesMsg *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!booster_interface__msg__RobotStatesMsg__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          booster_interface__msg__RobotStatesMsg__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!booster_interface__msg__RobotStatesMsg__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
