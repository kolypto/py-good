import unittest
import six
from good import Schema, Invalid, MultipleInvalid
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

    es_type = u'Wrong type'
    es_value_type = u'Wrong value type'
    es_value = u'Invalid value'


class SchemaTest(unittest.TestCase):
    """ Test Schema """

    longMessage = True

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

    def assertInvalid(self, schema, value, e_path, e_validator, e_message, e_expected, e_provided, **e_info):
        """ Try the given Schema against a value and expect that it's invalid

        :type schema: Schema
        :type value: The value to validate
        :type e_path: Expected Invalid.path value
        :param e_validator: Expected Invalid.validator value
        :param e_message: Expected Invalid.message value
        :param e_expected: Expected Invalid.expected value
        :param e_provided: Expected Invalid.provided value
        :param e_info: Expected Invalid.info value
        """
        with self.assertRaises(Invalid) as ecm:
            print 'False positive:', repr(schema(value))
        e = ecm.exception

        # Check error
        self.assertIs(type(e), Invalid)  # Strict type
        self.assertEqual(e.path, e_path)
        self.assertEqual(e.validator, e_validator)
        self.assertEqual(e.message, e_message)
        self.assertEqual(e.expected, e_expected)
        self.assertEqual(e.provided, e_provided)
        self.assertEqual(e.info, e_info)

    #region Schema(<literal>)

    def test_literal(self):
        """ Test Schema(<literal>) """
        # None
        schema = Schema(None)
        self.assertValid(schema, None)
        self.assertInvalid(schema, True, [], None, s.es_value_type, s.t_none, s.t_bool)

        # Bool
        schema = Schema(True)
        self.assertValid(schema, True)
        self.assertInvalid(schema, 1,     [], True, s.es_value_type, s.t_bool, s.t_int)
        self.assertInvalid(schema, False, [], True, s.es_value, u'True', u"False")

        # Integer
        schema = Schema(1)
        self.assertValid(schema, 1)
        self.assertInvalid(schema, True, [], 1, s.es_value_type, s.t_int, s.t_bool)
        self.assertInvalid(schema, 1.0,  [], 1, s.es_value_type, s.t_int, s.t_float)
        self.assertInvalid(schema, 2,    [], 1, s.es_value, u'1', u'2')

        # Float
        schema = Schema(1.0)
        self.assertValid(schema, 1.0)
        self.assertInvalid(schema,  1,    [], 1.0, s.es_value_type, s.t_float, s.t_int)
        self.assertInvalid(schema, 2.0,   [], 1.0, s.es_value, u'1.0', u'2.0')

        # String
        schema = Schema(b'1')
        self.assertValid(schema,   b'1')
        self.assertInvalid(schema,   1,  [], b'1', s.es_value_type, s.t_str, s.t_int)
        self.assertInvalid(schema, u'1', [], b'1', s.es_value_type, s.t_str, s.t_unicode)
        self.assertInvalid(schema, b'2', [], b'1', s.es_value, u'1', u'2')

        # Unicode
        schema = Schema(u'1')
        self.assertValid(schema, u'1')
        self.assertInvalid(schema,   1,  [], u'1', s.es_value_type, s.t_unicode, s.t_int)
        self.assertInvalid(schema, b'1', [], u'1', s.es_value_type, s.t_unicode, s.t_str)
        self.assertInvalid(schema, u'2', [], u'1', s.es_value, u'1', u'2')

    def test_type(self):
        """ Test Schema(<type>) """
        # NoneType
        schema = Schema(type(None))
        self.assertValid(schema, None)
        self.assertInvalid(schema, 1, [], type(None), s.es_type, s.t_none, s.t_int)

        # Bool
        schema = Schema(bool)
        self.assertValid(schema, True)
        self.assertInvalid(schema, 1,    [], bool, s.es_type, s.t_bool, s.t_int)
        self.assertInvalid(schema, None, [], bool, s.es_type, s.t_bool, s.t_none)

        # Integer
        schema = Schema(int)
        self.assertValid(schema, 1)
        self.assertInvalid(schema, True, [], int, s.es_type, s.t_int, s.t_bool)
        self.assertInvalid(schema, None, [], int, s.es_type, s.t_int, s.t_none)

        # Float
        schema = Schema(float)
        self.assertValid(schema, 1.0)
        self.assertInvalid(schema, 1, [], float, s.es_type, s.t_float, s.t_int)

        # String
        schema = Schema(six.binary_type)
        self.assertValid(schema, b'a')
        self.assertInvalid(schema, u'a', [], six.binary_type, s.es_type, s.t_str, s.t_unicode)
        self.assertInvalid(schema, 1,    [], six.binary_type, s.es_type, s.t_str, s.t_int)

        # Unicode
        schema = Schema(six.text_type)
        self.assertValid(schema, u'a')
        self.assertInvalid(schema, 'a', [], six.text_type, s.es_type, s.t_unicode, s.t_str)
        self.assertInvalid(schema, 1,   [], six.text_type, s.es_type, s.t_unicode, s.t_int)

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
        self.assertInvalid(schema, (), [], list_schema, s.es_value_type, u'List', u'Tuple')
        self.assertInvalid(schema, [True,], [0], list_schema, s.es_value, u'1|2|String', u'True')
        self.assertInvalid(schema, [1, 4],  [1], list_schema, s.es_value, u'1|2|String', u'4')
        self.assertInvalid(schema, [1, 4],  [1], list_schema, s.es_value, u'1|2|String', u'4')

    def test_iterable_deep(self):
        """ Test Schema(<iterable of schemas>) """

