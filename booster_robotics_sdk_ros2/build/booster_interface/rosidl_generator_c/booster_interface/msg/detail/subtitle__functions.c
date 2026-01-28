// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from booster_interface:msg/Subtitle.idl
// generated code does not contain a copyright notice
#include "booster_interface/msg/detail/subtitle__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `magic_number`
// Member `text`
// Member `language`
// Member `user_id`
#include "rosidl_runtime_c/string_functions.h"

bool
booster_interface__msg__Subtitle__init(booster_interface__msg__Subtitle * msg)
{
  if (!msg) {
    return false;
  }
  // magic_number
  if (!rosidl_runtime_c__String__init(&msg->magic_number)) {
    booster_interface__msg__Subtitle__fini(msg);
    return false;
  }
  // text
  if (!rosidl_runtime_c__String__init(&msg->text)) {
    booster_interface__msg__Subtitle__fini(msg);
    return false;
  }
  // language
  if (!rosidl_runtime_c__String__init(&msg->language)) {
    booster_interface__msg__Subtitle__fini(msg);
    return false;
  }
  // user_id
  if (!rosidl_runtime_c__String__init(&msg->user_id)) {
    booster_interface__msg__Subtitle__fini(msg);
    return false;
  }
  // seq
  // definite
  // paragraph
  // round_id
  return true;
}

void
booster_interface__msg__Subtitle__fini(booster_interface__msg__Subtitle * msg)
{
  if (!msg) {
    return;
  }
  // magic_number
  rosidl_runtime_c__String__fini(&msg->magic_number);
  // text
  rosidl_runtime_c__String__fini(&msg->text);
  // language
  rosidl_runtime_c__String__fini(&msg->language);
  // user_id
  rosidl_runtime_c__String__fini(&msg->user_id);
  // seq
  // definite
  // paragraph
  // round_id
}

bool
booster_interface__msg__Subtitle__are_equal(const booster_interface__msg__Subtitle * lhs, const booster_interface__msg__Subtitle * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // magic_number
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->magic_number), &(rhs->magic_number)))
  {
    return false;
  }
  // text
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->text), &(rhs->text)))
  {
    return false;
  }
  // language
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->language), &(rhs->language)))
  {
    return false;
  }
  // user_id
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->user_id), &(rhs->user_id)))
  {
    return false;
  }
  // seq
  if (lhs->seq != rhs->seq) {
    return false;
  }
  // definite
  if (lhs->definite != rhs->definite) {
    return false;
  }
  // paragraph
  if (lhs->paragraph != rhs->paragraph) {
    return false;
  }
  // round_id
  if (lhs->round_id != rhs->round_id) {
    return false;
  }
  return true;
}

bool
booster_interface__msg__Subtitle__copy(
  const booster_interface__msg__Subtitle * input,
  booster_interface__msg__Subtitle * output)
{
  if (!input || !output) {
    return false;
  }
  // magic_number
  if (!rosidl_runtime_c__String__copy(
      &(input->magic_number), &(output->magic_number)))
  {
    return false;
  }
  // text
  if (!rosidl_runtime_c__String__copy(
      &(input->text), &(output->text)))
  {
    return false;
  }
  // language
  if (!rosidl_runtime_c__String__copy(
      &(input->language), &(output->language)))
  {
    return false;
  }
  // user_id
  if (!rosidl_runtime_c__String__copy(
      &(input->user_id), &(output->user_id)))
  {
    return false;
  }
  // seq
  output->seq = input->seq;
  // definite
  output->definite = input->definite;
  // paragraph
  output->paragraph = input->paragraph;
  // round_id
  output->round_id = input->round_id;
  return true;
}

booster_interface__msg__Subtitle *
booster_interface__msg__Subtitle__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__Subtitle * msg = (booster_interface__msg__Subtitle *)allocator.allocate(sizeof(booster_interface__msg__Subtitle), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(booster_interface__msg__Subtitle));
  bool success = booster_interface__msg__Subtitle__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
booster_interface__msg__Subtitle__destroy(booster_interface__msg__Subtitle * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    booster_interface__msg__Subtitle__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
booster_interface__msg__Subtitle__Sequence__init(booster_interface__msg__Subtitle__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__Subtitle * data = NULL;

  if (size) {
    data = (booster_interface__msg__Subtitle *)allocator.zero_allocate(size, sizeof(booster_interface__msg__Subtitle), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = booster_interface__msg__Subtitle__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        booster_interface__msg__Subtitle__fini(&data[i - 1]);
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
booster_interface__msg__Subtitle__Sequence__fini(booster_interface__msg__Subtitle__Sequence * array)
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
      booster_interface__msg__Subtitle__fini(&array->data[i]);
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

booster_interface__msg__Subtitle__Sequence *
booster_interface__msg__Subtitle__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  booster_interface__msg__Subtitle__Sequence * array = (booster_interface__msg__Subtitle__Sequence *)allocator.allocate(sizeof(booster_interface__msg__Subtitle__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = booster_interface__msg__Subtitle__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
booster_interface__msg__Subtitle__Sequence__destroy(booster_interface__msg__Subtitle__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    booster_interface__msg__Subtitle__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
booster_interface__msg__Subtitle__Sequence__are_equal(const booster_interface__msg__Subtitle__Sequence * lhs, const booster_interface__msg__Subtitle__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!booster_interface__msg__Subtitle__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
booster_interface__msg__Subtitle__Sequence__copy(
  const booster_interface__msg__Subtitle__Sequence * input,
  booster_interface__msg__Subtitle__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(booster_interface__msg__Subtitle);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    booster_interface__msg__Subtitle * data =
      (booster_interface__msg__Subtitle *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!booster_interface__msg__Subtitle__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          booster_interface__msg__Subtitle__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!booster_interface__msg__Subtitle__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
