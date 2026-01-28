# generated from rosidl_generator_py/resource/_idl.py.em
# with input from booster_interface:msg/Subtitle.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_Subtitle(type):
    """Metaclass of message 'Subtitle'."""

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
                'booster_interface.msg.Subtitle')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__subtitle
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__subtitle
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__subtitle
            cls._TYPE_SUPPORT = module.type_support_msg__msg__subtitle
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__subtitle

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Subtitle(metaclass=Metaclass_Subtitle):
    """Message class 'Subtitle'."""

    __slots__ = [
        '_magic_number',
        '_text',
        '_language',
        '_user_id',
        '_seq',
        '_definite',
        '_paragraph',
        '_round_id',
    ]

    _fields_and_field_types = {
        'magic_number': 'string',
        'text': 'string',
        'language': 'string',
        'user_id': 'string',
        'seq': 'int32',
        'definite': 'boolean',
        'paragraph': 'boolean',
        'round_id': 'int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.magic_number = kwargs.get('magic_number', str())
        self.text = kwargs.get('text', str())
        self.language = kwargs.get('language', str())
        self.user_id = kwargs.get('user_id', str())
        self.seq = kwargs.get('seq', int())
        self.definite = kwargs.get('definite', bool())
        self.paragraph = kwargs.get('paragraph', bool())
        self.round_id = kwargs.get('round_id', int())

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
        if self.magic_number != other.magic_number:
            return False
        if self.text != other.text:
            return False
        if self.language != other.language:
            return False
        if self.user_id != other.user_id:
            return False
        if self.seq != other.seq:
            return False
        if self.definite != other.definite:
            return False
        if self.paragraph != other.paragraph:
            return False
        if self.round_id != other.round_id:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def magic_number(self):
        """Message field 'magic_number'."""
        return self._magic_number

    @magic_number.setter
    def magic_number(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'magic_number' field must be of type 'str'"
        self._magic_number = value

    @builtins.property
    def text(self):
        """Message field 'text'."""
        return self._text

    @text.setter
    def text(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'text' field must be of type 'str'"
        self._text = value

    @builtins.property
    def language(self):
        """Message field 'language'."""
        return self._language

    @language.setter
    def language(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'language' field must be of type 'str'"
        self._language = value

    @builtins.property
    def user_id(self):
        """Message field 'user_id'."""
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'user_id' field must be of type 'str'"
        self._user_id = value

    @builtins.property
    def seq(self):
        """Message field 'seq'."""
        return self._seq

    @seq.setter
    def seq(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'seq' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'seq' field must be an integer in [-2147483648, 2147483647]"
        self._seq = value

    @builtins.property
    def definite(self):
        """Message field 'definite'."""
        return self._definite

    @definite.setter
    def definite(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'definite' field must be of type 'bool'"
        self._definite = value

    @builtins.property
    def paragraph(self):
        """Message field 'paragraph'."""
        return self._paragraph

    @paragraph.setter
    def paragraph(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'paragraph' field must be of type 'bool'"
        self._paragraph = value

    @builtins.property
    def round_id(self):
        """Message field 'round_id'."""
        return self._round_id

    @round_id.setter
    def round_id(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'round_id' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'round_id' field must be an integer in [-2147483648, 2147483647]"
        self._round_id = value
