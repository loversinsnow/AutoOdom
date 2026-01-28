# generated from rosidl_generator_py/resource/_idl.py.em
# with input from booster_interface:msg/RobotStatesMsg.idl
# generated code does not contain a copyright notice


# Import statements for member types

# Member 'current_actions'
import array  # noqa: E402, I100

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_RobotStatesMsg(type):
    """Metaclass of message 'RobotStatesMsg'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('booster_interface')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'booster_interface.msg.RobotStatesMsg')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__robot_states_msg
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__robot_states_msg
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__robot_states_msg
            cls._TYPE_SUPPORT = module.type_support_msg__msg__robot_states_msg
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__robot_states_msg

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class RobotStatesMsg(metaclass=Metaclass_RobotStatesMsg):
    """Message class 'RobotStatesMsg'."""

    __slots__ = [
        '_current_mode',
        '_current_body_control',
        '_current_actions',
    ]

    _fields_and_field_types = {
        'current_mode': 'int32',
        'current_body_control': 'int32',
        'current_actions': 'sequence<int32>',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.UnboundedSequence(rosidl_parser.definition.BasicType('int32')),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.current_mode = kwargs.get('current_mode', int())
        self.current_body_control = kwargs.get('current_body_control', int())
        self.current_actions = array.array('i', kwargs.get('current_actions', []))

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.current_mode != other.current_mode:
            return False
        if self.current_body_control != other.current_body_control:
            return False
        if self.current_actions != other.current_actions:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def current_mode(self):
        """Message field 'current_mode'."""
        return self._current_mode

    @current_mode.setter
    def current_mode(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'current_mode' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'current_mode' field must be an integer in [-2147483648, 2147483647]"
        self._current_mode = value

    @builtins.property
    def current_body_control(self):
        """Message field 'current_body_control'."""
        return self._current_body_control

    @current_body_control.setter
    def current_body_control(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'current_body_control' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'current_body_control' field must be an integer in [-2147483648, 2147483647]"
        self._current_body_control = value

    @builtins.property
    def current_actions(self):
        """Message field 'current_actions'."""
        return self._current_actions

    @current_actions.setter
    def current_actions(self, value):
        if isinstance(value, array.array):
            assert value.typecode == 'i', \
                "The 'current_actions' array.array() must have the type code of 'i'"
            self._current_actions = value
            return
        if __debug__:
            from collections.abc import Sequence
            from collections.abc import Set
            from collections import UserList
            from collections import UserString
            assert \
                ((isinstance(value, Sequence) or
                  isinstance(value, Set) or
                  isinstance(value, UserList)) and
                 not isinstance(value, str) and
                 not isinstance(value, UserString) and
                 all(isinstance(v, int) for v in value) and
                 all(val >= -2147483648 and val < 2147483648 for val in value)), \
                "The 'current_actions' field must be a set or sequence and each value of type 'int' and each integer in [-2147483648, 2147483647]"
        self._current_actions = array.array('i', value)
