from __future__ import print_function
import unittest
import six
from good import Schema, Invalid, MultipleInvalid, Required, Optional, Extra, Remove, Reject
from good.schema.util import get_type_name


class s:
    """ Shortcuts """
    # Type names
    t_none = get_type_name(None)
    t_bool = get_type_name(bool)
    t_int = get_type_name(int)
    t_float = get_type_name(float)
    t_str = get_type_name(six.binary_type)  # Binary string
    t_unicode = get_type_name(six.text_type)  # Unicode string
    t_list = get_type_name(list)
    t_dict = get_type_name(dict)

    es_type = u'Wrong type'
    es_value_type = u'Wrong value type'
    es_value = u'Invalid value'

    es_required = u'Required key missing'
    es_extra = u'Extra keys not allowed'


class SchemaTest(unittest.TestCase):
    """ Test Schema """

    longMessage = True

    def assertInvalidError(self, actual, expected):
        """ Assert that the two Invalid exceptions are the same

        :param actual: Actual exception
        :type actual: Invalid
        :param expected: Expected exception
        :type expected: Invalid
        """
        repr(actual), six.text_type(actual)  # repr() works fine

        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.path, actual.path)
        self.assertEqual(expected.validator, actual.validator)
        self.assertEqual(expected.message, actual.message)
        self.assertEqual(expected.expected, actual.expected)
        self.assertEqual(expected.provided, actual.provided)
        self.assertEqual(expected.info, actual.info)

    def assertValid(self, schema, value, validated_value=None):
        """ Try the given Schema against a value and expect that it's valid

        :type schema: Schema
        :param value: The value to validate
        :type validated_value: The expected validated value
        """
        self.assertEqual(
            schema(value),
            value if validated_value is None else validated_value,
            'Sanitized value is wrong'
        )

    def assertInvalid(self, schema, value, e):
        """ Try the given Schema against a value and expect that it's Invalid

        :type schema: Schema
        :param value: The value to validate
        :param e: Expected exception
        :type e: Invalid|MultipleInvalid
        """
        repr(schema), six.text_type(schema)  # no errors

        with self.assertRaises(Invalid) as ecm:
            print('False positive:', repr(schema(value)))

        self.assertInvalidError(ecm.exception, e)


    #region Schema(<literal>)

    def test_literal(self):
        """ Test Schema(<literal>) """
        # None
        schema = Schema(None)
        self.assertValid(schema, None)
        self.assertInvalid(schema, True,  Invalid(s.es_value_type,  s.t_none,           s.t_bool,               [], None))

        # Bool
        schema = Schema(True)
        self.assertValid(schema, True)
        self.assertInvalid(schema, 1,     Invalid(s.es_value_type,  s.t_bool,            s.t_int,               [], True))
        self.assertInvalid(schema, False, Invalid(s.es_value,       u'True',             u"False",              [], True))

        # Integer
        schema = Schema(1)
        self.assertValid(schema, 1)
        self.assertInvalid(schema, True,  Invalid(s.es_value_type,  s.t_int,             s.t_bool,              [], 1))
        self.assertInvalid(schema, 1.0,   Invalid(s.es_value_type,  s.t_int,             s.t_float,             [], 1))
        self.assertInvalid(schema, 2,     Invalid(s.es_value,       u'1',                u'2',                  [], 1))

        # Float
        schema = Schema(1.0)
        self.assertValid(schema, 1.0)
        self.assertInvalid(schema,  1,    Invalid(s.es_value_type,  s.t_float,           s.t_int,               [], 1.0))
        self.assertInvalid(schema, 2.0,   Invalid(s.es_value,       u'1.0',              u'2.0',                [], 1.0))

        # String
        schema = Schema(b'1')
        self.assertValid(schema,   b'1')
        self.assertInvalid(schema,   1,   Invalid(s.es_value_type,  s.t_str,             s.t_int,               [], b'1'))
        self.assertInvalid(schema, u'1',  Invalid(s.es_value_type,  s.t_str,             s.t_unicode,           [], b'1'))
        self.assertInvalid(schema, b'2',  Invalid(s.es_value,       six.text_type(b'1'), six.text_type(b'2'),   [], b'1'))

        # Unicode
        schema = Schema(u'1')
        self.assertValid(schema, u'1')
        self.assertInvalid(schema,   1,   Invalid(s.es_value_type,  s.t_unicode,         s.t_int,               [], u'1'))
        self.assertInvalid(schema, b'1',  Invalid(s.es_value_type,  s.t_unicode,         s.t_str,               [], u'1'))
        self.assertInvalid(schema, u'2',  Invalid(s.es_value,       u'1',                u'2',                  [], u'1'))

    def test_type(self):
        """ Test Schema(<type>) """
        # NoneType
        schema = Schema(type(None))
        self.assertValid(schema, None)
        self.assertInvalid(schema, 1,    Invalid(s.es_type, s.t_none,    s.t_int,     [], type(None)))

        # Bool
        schema = Schema(bool)
        self.assertValid(schema, True)
        self.assertInvalid(schema, 1,    Invalid(s.es_type, s.t_bool,    s.t_int,     [], bool))
        self.assertInvalid(schema, None, Invalid(s.es_type, s.t_bool,    s.t_none,    [], bool))

        # Integer
        schema = Schema(int)
        self.assertValid(schema, 1)
        self.assertInvalid(schema, True, Invalid(s.es_type, s.t_int,     s.t_bool,    [], int))
        self.assertInvalid(schema, None, Invalid(s.es_type, s.t_int,     s.t_none,    [], int))

        # Float
        schema = Schema(float)
        self.assertValid(schema, 1.0)
        self.assertInvalid(schema, 1,    Invalid(s.es_type, s.t_float,   s.t_int,     [], float))

        # String
        schema = Schema(six.binary_type)
        self.assertValid(schema, b'a')
        self.assertInvalid(schema, u'a', Invalid(s.es_type, s.t_str,     s.t_unicode, [], six.binary_type))
        self.assertInvalid(schema, 1,    Invalid(s.es_type, s.t_str,     s.t_int,     [], six.binary_type))

        # Unicode
        schema = Schema(six.text_type)
        self.assertValid(schema, u'a')
        self.assertInvalid(schema, b'a', Invalid(s.es_type, s.t_unicode, s.t_str,     [], six.text_type))
        self.assertInvalid(schema, 1,    Invalid(s.es_type, s.t_unicode, s.t_int,     [], six.text_type))

    def test_iterable(self):
        """ Test Schema(<iterable>) """
        list_schema = [1, 2, six.text_type]

        # Test common cases
        schemas = (
            (tuple,     Schema(tuple(list_schema))),
            (list,      Schema(list(list_schema))),
            (set,       Schema(set(list_schema))),
            (frozenset, Schema(frozenset(list_schema))),
        )
        valid_inputs = (
            (),
            (1,),
            (u'a',),
            (1, 1, 2, u'a', u'b', u'c')
        )

        for type, schema in schemas:
            # Test valid inputs
            for v in valid_inputs:
                # Typecast to the correct value
                value = type(v)
                # Should be valid
                self.assertValid(schema, value)

        # Test specific cases
        schema = Schema(list_schema)
        self.assertInvalid(schema, (),      Invalid(s.es_value_type, u'List',             u'Tuple', [ ], list_schema))
        self.assertInvalid(schema, [True,], Invalid(s.es_value,      u'List[1|2|String]', u'True',  [0], list_schema))
        self.assertInvalid(schema, [1, 4],  Invalid(s.es_value,      u'List[1|2|String]', u'4',     [1], list_schema))
        self.assertInvalid(schema, [1, 4],  Invalid(s.es_value,      u'List[1|2|String]', u'4',     [1], list_schema))

    def test_callable(self):
        """ Test Schema(<callable>) """
        def intify(v):
            return int(v)

        def intify_ex(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                raise Invalid(u'Must be a number', u'Number')

        # Simple callable
        schema = Schema(intify)

        self.assertValid(schema, 1)
        self.assertValid(schema, True, 1)
        self.assertValid(schema, b'1', 1)

        self.assertInvalid(schema, None, Invalid(u'TypeError: int() argument must be a string or a number, not \'NoneType\'',   u'intify()', s.t_none,  [], intify))
        self.assertInvalid(schema, u'a', Invalid(u'ValueError: invalid literal for int() with base 10: \'a\'',                  u'intify()', u'a',      [], intify))

        # Simple callable that throws Invalid
        schema = Schema(intify_ex)

        self.assertValid(schema, u'1', 1)
        self.assertInvalid(schema, u'a', Invalid(u'Must be a number', u'Number', u'a', [], intify_ex))

        # Nested callable
        str_or_int = [
            intify,
            six.text_type
        ]
        schema = Schema(str_or_int)

        self.assertValid(schema, [u'a'])
        self.assertValid(schema, [1])
        self.assertValid(schema, [u'1', 1], [1, 1])
        self.assertValid(schema, [b'1'], [1])

        self.assertInvalid(schema, [b'abc'], Invalid(u'Invalid value', u'List[intify()|String]', six.text_type(b'abc'), [0], str_or_int))

    @unittest.skip
    def test_schema_schema(self):
        """ Test Schema(Schema) """
