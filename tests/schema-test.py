from __future__ import print_function
import six
import unittest
import collections
import json
from random import shuffle
from copy import deepcopy

from good import *
from good.schema.markers import Marker
from good.schema.util import get_type_name, Undefined, const


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

    v_no = u'-none-'

    es_type = u'Wrong type'
    es_value_type = u'Wrong value type'
    es_value = u'Invalid value'

    es_required = u'Required key not provided'
    es_extra = u'Extra keys not allowed'
    es_rejected = u'Value rejected'


class GoodTestBase(unittest.TestCase):
    """ Helpers for testing """

    longMessage = True

    def assertInvalidError(self, actual, expected):
        """ Assert that the two Invalid exceptions are the same

        :param actual: Actual exception
        :type actual: Invalid
        :param expected: Expected exception
        :type expected: Invalid
        """
        repr(actual), six.text_type(actual)  # repr() works fine
        self.assertEqual(type(expected), type(actual))  # type matches

        if isinstance(actual, MultipleInvalid):
            return self.assertMultipleInvalidError(actual, expected)

        self.assertEqual(expected.path, actual.path)
        self.assertEqual(expected.validator, actual.validator)
        self.assertEqual(expected.message, actual.message)
        self.assertEqual(expected.provided, actual.provided)
        self.assertEqual(expected.expected, actual.expected)
        self.assertEqual(expected.info, actual.info)

        # Also test that Errors always have the desired types
        self.assertTrue(isinstance(actual.path,     list))           # Always a list
        self.assertTrue(isinstance(actual.message,  six.text_type))  # Unicode
        self.assertTrue(isinstance(actual.provided, six.text_type))  # Unicode
        self.assertTrue(isinstance(actual.expected, six.text_type))  # Unicode
        self.assertTrue(isinstance(actual.info,     dict))           # Dict
        # Check path: all components should always be literals.
        for p in actual.path:
            # This makes sure that no Marker(value) ever makes it to the path, since it's not JSON-serializable.
            self.assertNotIsInstance(p, Marker)
            # Make sure path is a list of literals.
            # (They're not limited to the listed types, but our tests only use these.)
            self.assertIsInstance(p, (six.string_types, six.integer_types))

    def assertMultipleInvalidError(self, actual, expected):
        """ Assert that the two MultipleInvalid exceptions are the same

        :param actual: Actual exception
        :type actual: MultipleInvalid
        :param expected: Expected exception
        :type expected: MultipleInvalid
        """
        # Match lists
        expected_errors = expected.errors[:]
        extra_errors = []
        raised_expectedly = []

        for actual_e in actual.errors:
            # Find the matching error
            for i, expected_e in enumerate(expected_errors):
                try:
                    # Matches?
                    self.assertInvalidError(actual_e, expected_e)
                except self.failureException:
                    pass
                else:
                    # Matches!
                    e = expected_errors.pop(i)
                    raised_expectedly.append(e)
                    break
            else:
                expected_e = None

            # No match
            if not expected_e:
                extra_errors.append(actual_e)

        # All ok?
        if not expected_errors and not extra_errors:
            return

        # Throw errors
        self.fail(
            u'MultipleError failed:\n' +
            u'\nNot raised:\n'
            u' * ' + '\n * '.join(map(repr, expected_errors)) +
            u'\nGot instead:\n' +
            u' * ' + '\n * '.join(map(repr, extra_errors)) +
            u'\nRaised expectedly:\n' +
            u' * ' + '\n * '.join(map(repr, raised_expectedly))
        )

    def assertValid(self, schema, value, validated_value=None):
        """ Try the given Schema against a value and expect that it's valid

        :type schema: Schema
        :param value: The value to validate
        :type validated_value: The expected validated value
        """
        if validated_value is None:
            validated_value = deepcopy(value)

        self.assertEqual(
            schema(value),
            validated_value,
            'Sanitized value is wrong'
        )

    def assertInvalid(self, schema, value, e):
        """ Try the given Schema against a value and expect that it's Invalid

        :type schema: Schema
        :param value: The value to validate
        :param e: Expected exception, or `None` if you don't care about it
        :type e: Invalid|MultipleInvalid
        """
        repr(schema), six.text_type(schema)  # no errors

        try:
            sanitized = schema(value)
            self.fail(u'False positive: {!r}\nExpected: {!r}'.format(sanitized, e))
        except Invalid as exc:
            if e is not None:
                self.assertInvalidError(exc, e)


class SchemaCoreTest(GoodTestBase):
    """ Test Schema (core) """
    
    def test_undefined(self):
        """ Test Undefined: it should never ever match any check """
        self.assertFalse(const.UNDEFINED == 0)
        self.assertFalse(const.UNDEFINED == 1)
        self.assertFalse(const.UNDEFINED == True)
        self.assertFalse(const.UNDEFINED == False)
        self.assertFalse(const.UNDEFINED is None)
        self.assertFalse(isinstance(const.UNDEFINED, type))

        # The only way is to test `UNDEFINED is UNDEFINED`
        self.assertTrue(const.UNDEFINED is const.UNDEFINED)

        # Singleton
        self.assertIs(Undefined(), Undefined())

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

        # Remove() marker
        schema = Schema([six.text_type, Remove(int)])
        self.assertValid(schema, [u'a', u'b'])
        self.assertValid(schema, [u'a', u'b', 1, 2], [u'a', u'b'])

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

        self.assertInvalid(schema, None, Invalid(u'int() argument must be a string or a number, not \'NoneType\'',  u'intify()', s.t_none,  [], intify))
        self.assertInvalid(schema, u'a', Invalid(u'invalid literal for int() with base 10: \'a\'',                  u'intify()', u'a',      [], intify))

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

    def test_schema_schema(self):
        """ Test Schema(Schema) """
        sub_schema = Schema(int)
        schema = Schema([None, sub_schema])

        self.assertValid(schema, [None, 1, 2])
        self.assertInvalid(schema, [None, u'1'],
                           Invalid(s.es_value, u'List[None|Integer number]', u'1', [1], [None, sub_schema]))

    def test_mapping_literal(self):
        """ Test Schema(<mapping>), literal keys """
        structure = {
            'name': six.text_type,
            'age': int,
            'sex': u'f',  # girls only :)
        }
        schema = Schema(structure)

        # Okay
        self.assertValid(schema, {'name': u'A', 'age': 18, 'sex': u'f'})

        # Wrong type
        self.assertInvalid(schema, [],
                           Invalid(s.es_value_type, s.t_dict, s.t_list, [], structure))

        # Wrong 'sex'
        self.assertInvalid(schema, {'name': u'A', 'age': 18, 'sex': None},
                           Invalid(s.es_value_type, s.t_unicode,            s.t_none,               ['sex'],    u'f'))
        self.assertInvalid(schema, {'name': u'A', 'age': 18, 'sex': u'm'},
                           Invalid(s.es_value,      u'f',                   u'm',                   ['sex'],    u'f'))
        # Wrong 'name' and 'age'
        self.assertInvalid(schema, {'name': None, 'age': None, 'sex': u'f'}, MultipleInvalid([
                           Invalid(s.es_type,       s.t_unicode,            s.t_none,               ['name'],   six.text_type),
                           Invalid(s.es_type,       s.t_int,                s.t_none,               ['age'],    int),
        ]))

        # Missing key 'sex'
        self.assertInvalid(schema, {'name': u'A', 'age': 18},
                           Invalid(s.es_required,   six.text_type('sex'),   s.v_no,                 ['sex'],    Required('sex')))
        # Extra key 'lol'
        self.assertInvalid(schema, {'name': u'A', 'age': 18, 'sex': u'f', 'lol': 1},
                           Invalid(s.es_extra,      s.v_no,                 six.text_type('lol'),   ['lol'],    Extra))
        # Missing keys 'age', 'sex', extra keys 'lol', 'hah'
        self.assertInvalid(schema, {'name': u'A', 'lol': 1, 'hah': 2}, MultipleInvalid([
                           Invalid(s.es_required,   six.text_type('age'),   s.v_no,                 ['age'],    Required),
                           Invalid(s.es_required,   six.text_type('sex'),   s.v_no,                 ['sex'],    Required),
                           Invalid(s.es_extra,      s.v_no,                 six.text_type('lol'),   ['lol'],    Extra),
                           Invalid(s.es_extra,      s.v_no,                 six.text_type('hah'),   ['hah'],    Extra),
        ]))

    def test_mapping_type(self):
        """ Test Schema(<mapping>), type keys """
        schema = Schema({
            'name': 1,
            int: bool,
        })

        # Okay
        self.assertValid(schema, {'name': 1, 1: True, 2: True})

        # Wrong value type
        self.assertInvalid(schema, {'name': 1},
                           Invalid(s.es_required,   s.t_int,  s.v_no,      [],  Required(int)))
        self.assertInvalid(schema, {'name': 1, 1: True, 2: u'WROOONG'},
                           Invalid(s.es_type,       s.t_bool, s.t_unicode, [2], bool))

        # Wrong key type (meaning, `int` not provided, and extra key `'2'`)
        self.assertInvalid(schema, {'name': 1, u'1': True}, MultipleInvalid([
                           Invalid(s.es_extra,      s.v_no,   u'1',        [u'1'], Extra),
                           Invalid(s.es_required,   s.t_int,  s.v_no,      [],  Required(int)),
        ]))

    def test_mapping_callable(self):
        """ Test Schema(<mapping>), callable keys """
        def multikey(*keys):
            def multikey_validate(v):
                assert v in keys
                return v
            return multikey_validate

        def intify(v):
            try:
                return int(v)
            except ValueError as e:
                raise Invalid(u'Int failed')

        abc = multikey('a', 'b', 'c')
        schema = Schema({
            # Values for ('a', 'b', 'c') are int()ified
            abc: intify,
            # Other keys are int()ified and should be boolean
            intify: bool
        })

        # Okay
        self.assertValid(schema, {'a': 1, 'b': '2', 1: True},             {'a': 1, 'b': 2, 1: True})
        self.assertValid(schema, {'a': 1, 'b': '2', 1: True, '2': False}, {'a': 1, 'b': 2, 1: True, 2: False})

        # Wrong value for `multikey()`
        self.assertInvalid(schema, {'a': u'!', '1': True},
                           Invalid(u'Int failed', u'intify()', u'!', ['a'], intify))
        # Wrong value for `bool`
        self.assertInvalid(schema, {'a': 1, '1': None},
                           Invalid(s.es_type, s.t_bool, s.t_none, ['1'], bool))
        # `intify()` did not match
        self.assertInvalid(schema, {'a': 1},
                           Invalid(u'Required key not provided', u'intify()', s.v_no, [], Required(intify)))
        # `multikey()` did not match
        self.assertInvalid(schema, {1: True},
                           Invalid(u'Required key not provided', u'multikey_validate()', s.v_no, [], Required(abc)))
        # Both `intify()` and `multikey()` did not match
        self.assertInvalid(schema, {}, MultipleInvalid([
            Invalid(u'Required key not provided', u'intify()', s.v_no, [], Required(intify)),
            Invalid(u'Required key not provided', u'multikey_validate()', s.v_no, [], Required(abc)),
        ]))

    def test_mapping_markers(self):
        """ Test Schema(<mapping>), with Markers """
        # Required, literal
        schema = Schema({
            Required(u'a'): 1,
            u'b': 2,
            Required(int): bool,
        })

        self.assertValid(schema,   {u'a': 1, u'b': 2, 3: True})
        self.assertInvalid(schema, {u'a': 1,          3: True},
                           Invalid(s.es_required, u'b', s.v_no, [u'b'], Required(u'b')))
        self.assertInvalid(schema, {u'a': 1, u'b': 2},
                           Invalid(s.es_required, s.t_int, s.v_no, [], Required(int)))

        # Optional
        schema = Schema({
            Optional(u'a'): 1,
            u'b': 2,
            Optional(int): bool,
        })
        self.assertValid(schema,   {         u'b': 2         })
        self.assertValid(schema,   {u'a': 1, u'b': 2         })
        self.assertValid(schema,   {u'a': 1, u'b': 2, 3: True})
        self.assertInvalid(schema, {u'a': 1                  },
                           Invalid(s.es_required, u'b', s.v_no, [u'b'], Required(u'b')))

        # Remove: as key
        schema = Schema({
            Remove(u'a'): 1,
            u'b': 2,
            Remove(int): bool,
        })
        self.assertValid(schema, {           u'b': 2         })
        self.assertValid(schema, {           u'b': 2, 1: True}, {u'b': 2})
        self.assertValid(schema, {u'a': 1,   u'b': 2, 1: True}, {u'b': 2})
        # removes invalid values before they're validated
        self.assertValid(schema, {u'a': 'X', u'b': 2, 1: True}, {u'b': 2})
        self.assertValid(schema, {u'a': 'X', u'b': 2, 1: 'X' }, {u'b': 2})

        # Remove: as value
        schema = Schema({
            u'a': Remove,
            u'b': 2,
            int: Remove(bool),  # it does not care about the value
        })
        self.assertValid(schema,   {u'a': None, u'b': 2, 1: True}, {u'b': 2})
        self.assertValid(schema,   {u'a': None, u'b': 2, 1: None}, {u'b': 2})

        # Extra
        schema = Schema({
            u'b': 1,
            Extra: int
        })
        self.assertValid(schema, {u'b': 1})
        self.assertValid(schema, {u'b': 1, u'c': 1, 1: 2})
        self.assertInvalid(schema, {u'b': 1, u'c': u'abc'},
                           Invalid(s.es_type, s.t_int, s.t_unicode, [u'c'], int))

        # Extra: Reject
        schema = Schema({
            u'a': 1,
            Extra: Reject
        })
        self.assertValid(schema, {u'a': 1})
        self.assertInvalid(schema, {u'a': 1, u'b': 2},
                           Invalid(s.es_extra, s.v_no, u'b', [u'b'], Extra))

        # Extra: Remove
        schema = Schema({
            u'a': 1,
        }, extra_keys=Remove)
        self.assertValid(schema, {u'a': 1})
        self.assertValid(schema, {u'a': 1, u'b': 2, u'c': 3}, {u'a': 1})

        # Extra: Allow
        schema = Schema({
            u'a': 1,
        }, extra_keys=Allow)
        self.assertValid(schema, {u'a': 1})
        self.assertValid(schema, {u'a': 1, u'b': 2, u'c': 3})

        # Reject: as key
        schema = Schema({
            u'a': 1,
            Reject(six.text_type): int,
        })
        self.assertValid(schema,   {u'a': 1})
        self.assertInvalid(schema, {u'a': 1, u'b': 1},
                           Invalid(s.es_rejected, s.v_no, u'b', [u'b'], Reject(six.text_type)))

        # Reject: as value
        schema = Schema({
            u'a': 1,
            Optional(six.text_type): Reject,
        })
        self.assertValid(schema, {u'a': 1})
        self.assertInvalid(schema, {u'a': 1, u'b': 1},
                           Invalid(s.es_rejected, s.v_no, u'1', [u'b'], Reject))

        # Entire
        def max3keys(d):
            if len(d) > 3:
                raise Invalid(u'Too many keys', u'<=3 keys', u'{} keys'.format(len(d)))
            return d

        schema = Schema({
            six.text_type: int,
            Entire: max3keys
        })

        self.assertValid(schema,   {u'a': 1})
        self.assertValid(schema,   {u'a': 1, u'b': 2})
        self.assertValid(schema,   {u'a': 1, u'b': 2, u'c': 3})
        self.assertInvalid(schema, {u'a': 1, u'b': 2, u'c': 3, u'd': 4},
                           Invalid(u'Too many keys', u'<=3 keys', u'4 keys', [], max3keys))

    def test_mapping_priority(self):
        """ Test Schema(<mapping>), priority test """
        # This test validates that schema key type priorities are working fine

        # Use different functions so they have different hashes and do not collapse into a single value.
        identity1 = lambda x: x
        identity2 = lambda x: x
        identity3 = lambda x: x

        # All key schemas will match integers, and values will show whether the priorities work fine
        schema = {
            # Remove has the highest priority
            Remove(identity1): lambda x: None,
            # These two are wrapped with Optional(), but still must be applied in order
            # Literal, then type
            100: lambda x: 'literal',
            int: lambda x: 'type',
            # Callable: lower than type
            identity2: lambda x: 'callable',
            # Reject: lower than callable
            Reject(identity3): lambda x: None,
            # Extra: absolutely last
            Extra: lambda x: 'Extra'
        }

        assert len(schema), 6

        def assertValid(schema, value, expected_result=None, expected_error=None):
            """ Test a schema definition, randomizing the sequence every time """
            schema_items = list(schema.items())
            for i in range(0, 10):
                shuffle(schema_items)
                sch = Schema(collections.OrderedDict(schema), default_keys=Optional)
                if expected_error:
                    self.assertInvalid(sch, deepcopy(value), expected_error)
                else:
                    self.assertValid(sch, deepcopy(value), expected_result)

        # Now try matching the schema in multiple steps, dropping the top priority key every time
        # This also ensures the dict is not modified by the schema itself.

        # 1. Marker:Remove
        assertValid(schema, {100: None}, {})
        schema.pop(identity1)

        # 2. literal
        assertValid(schema, {100: None}, {100: 'literal'})
        schema.pop(100)

        # 3. type
        assertValid(schema, {100: None}, {100: 'type'})
        schema.pop(int)

        # 4. callable
        assertValid(schema, {100: None}, {100: 'callable'})
        schema.pop(identity2)

        # 5. Reject
        assertValid(schema, {100: None}, expected_error=Invalid(s.es_rejected, s.v_no, u'100', [100], Reject(identity3)))
        schema.pop(identity3)

        # 6. Marker:Extra
        assertValid(schema, {100: None}, {100: 'Extra'})
        schema.pop(Extra)


class InvalidJsonTest(unittest.TestCase):

    def test_json(self):
        """ Test how Invalid works with JSON """

        # Schema
        schema = Schema({
            'a': 1,
            'b': 2
        })

        # Validate, get error
        with self.assertRaises(MultipleInvalid) as ecm:
            schema({'a': 2, 'b': 1})
        ee = ecm.exception

        # Format & Load
        errors = [{'msg': e.message, 'path': e.path} for e in ee]
        errors_json = json.dumps(errors)  # without errors
        errors = json.loads(errors_json)  # without errors

        # Predictable order
        errors = sorted(errors, key=lambda x: x['path'])

        # Check
        self.assertEqual(errors, [
            {'msg': s.es_value, 'path': ['a']},
            {'msg': s.es_value, 'path': ['b']},
        ])


class HelpersTest(GoodTestBase):
    """ Test: Helpers """

    def test_Object(self):
        """ Test Object() """

        def intify(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                raise Invalid(s.es_value, u'Number')

        # Class
        class OPerson(object):
            category = u'Something'  # Not validated

            def __init__(self, name, age):
                self.name = name
                self.age = age

            def __eq__(self, other):
                return isinstance(other, type(self)) and self.name == other.name and self.age == other.age

        # NamedTuple class
        TPerson = collections.namedtuple('TPerson', ('name', 'age'))

        # Slots class
        class SPerson(OPerson):
            __slots__ = ('name', 'age')

        # Test on every class
        for Person in (OPerson, TPerson, SPerson):
            # Object()
            object_validator = Object({
                u'name': six.text_type,
                u'age': intify,
            })
            schema = Schema(object_validator)

            self.assertValid(schema, Person(u'Alex', 18), Person(u'Alex', 18))
            self.assertInvalid(schema, type('A', (object,), {})(), MultipleInvalid([
                Invalid(s.es_required, u'name', s.v_no, [u'name'], Required(u'name')),
                Invalid(s.es_required, u'age',  s.v_no, [u'age'],  Required(u'age')),
            ]))
            self.assertInvalid(schema, Person(u'Alex', u'abc'),
                               Invalid(s.es_value, u'Number', u'abc', [u'age'], intify))

            # Test attribute mutation
            if Person is not TPerson:  # `TPerson` is immutable and cannot be tested
                self.assertValid(schema, Person(u'Alex', u'18'), Person(u'Alex', 18))

            # Object() with typecheck
            object_validator = Object({
                u'name': six.text_type,
                u'age': intify,
            }, Person)
            schema = Schema(object_validator)

            self.assertValid(schema, Person(u'Alex', 18), Person(u'Alex', 18))
            self.assertInvalid(schema, type('A', (object,), {})(),
                               Invalid(s.es_value_type, u'Object({})'.format(Person.__name__), u'Object(A)', [], object_validator))

    def test_Msg(self):
        """ Test Msg() """

        # Test Msg() with Invalid
        schema = Schema(Msg(int, u'Need a number'))

        self.assertValid(schema, 1)
        self.assertInvalid(schema, u'a',
                           Invalid(u'Need a number', s.t_int, s.t_unicode, [], int))

        # Test Msg() with ValueError
        intify = lambda v: int(v)
        intify.name = u'Int'

        schema = Schema(Msg(intify, u'Need a number'))

        self.assertValid(schema, 1)
        self.assertInvalid(schema, u'a',
                           Invalid(u'Need a number', u'Int', u'a', [], intify))

        # Test Msg() with MultipleInvalid
        schema = Schema(Msg({
            'a': 1,
            'b': 2,
        }, u'Wrong!'))

        self.assertValid(schema,   {'a': 1, 'b': 2})
        self.assertInvalid(schema, {'a': 2, 'b': 1}, MultipleInvalid([
            Invalid(u'Wrong!', u'1', u'2', ['a'], 1),
            Invalid(u'Wrong!', u'2', u'1', ['b'], 2),
        ]))

    def test_message(self):
        """ Test @message() """

        def intify(v):
            return int(v)
        wintify = message(u'Need a number')(intify)  # using function name

        schema = Schema(wintify)

        self.assertValid(schema, 1)
        self.assertInvalid(schema, u'a',
                           Invalid(u'Need a number', u'intify()', u'a', [], intify))

    def test_truth(self):
        """ Test @truth() """

        @truth(u'Must be 1')
        def isOne(v):
            return v == 1

        schema = Schema(isOne)

        self.assertValid(schema, 1)
        self.assertInvalid(schema, u'1',
                           Invalid(u'Must be 1', u'isOne()', u'1', [], isOne))


class PredicatesTest(GoodTestBase):
    """ Test: Validators.Predicates """

    def test_Any(self):
        """ Test Any() """

        any = Any(int, name(u'str', lambda v: u'('+v+u')'))
        schema = Schema(any)

        self.assertValid(schema, 1)
        self.assertValid(schema, u'1', u'(1)')

        self.assertInvalid(schema, None,
                           Invalid(s.es_value, u'Any(Integer number|str)', s.t_none, [], any))

    def test_All(self):
        """ Test All() """

        @truth(u'Must be in range 0..100', u'Range(0..100)')
        def percent(v):
            return 0 <= v <= 100

        schema = Schema(All(int, percent))

        self.assertValid(schema, 90)
        self.assertInvalid(schema, 190,
                           Invalid(u'Must be in range 0..100', u'Range(0..100)', u'190', [], percent))

    def test_Neither(self):
        """ Test Neither() """

        schema = Schema(All(
            int,
            Neither(-1, 0, 1)
        ))

        self.assertValid(schema, 10)
        self.assertInvalid(schema, 0,
                           Invalid(u'Value not allowed', u'Not(0)', u'0', [], 0))

    def test_Inclusive(self):
        """ Test Inclusive() """
        inclusive_group = Inclusive('width', 'height')
        schema = Schema({
            # Fields for all files
            'name': str,
            # Fields for images only
            Optional('width'): int,
            Optional('height'): int,
            # Now put a validator on the entire mapping
            Entire: inclusive_group
        })

        self.assertValid(schema,   {'name': 'monica.jpg'})
        self.assertValid(schema,   {'name': 'monica.jpg', 'width': 800, 'height': 600})

        self.assertInvalid(schema, {'name': 'monica.jpg', 'width': 800},
                           Invalid(s.es_required, u'height', s.v_no, ['height'], inclusive_group))

    def test_Exclusive(self):
        """ Test Exclusive() """

        for mode in (None, Required, Optional):
            if mode is None:
                exclusive_group = Exclusive('login', 'email')
            else:
                exclusive_group = Exclusive(mode, 'login', 'email')

            schema = Schema({
                Optional('login'): six.text_type,
                Optional('email'): six.text_type,
                'password': six.text_type,
                Entire: exclusive_group
            })

            self.assertValid(schema,   {'login': u'a', 'password': u'b'})
            self.assertValid(schema,   {'email': u'a', 'password': u'b'})

            self.assertInvalid(schema, {'login': u'a', 'email': u'b', 'password': u'c'},
                               Invalid(u'Choose one of the options, not multiple', u'Exclusive(email,login)', u'email,login', [], exclusive_group))

            if mode is Optional:
                self.assertValid(schema,   {'password': u'c'})
            else:
                self.assertInvalid(schema, {'password': u'c'},
                               Invalid(u'Choose one of the options', u'Exclusive(email,login)', s.v_no, [], exclusive_group))


class TypesTest(GoodTestBase):
    """ Test: Validators.Types """

    def test_Coerce(self):
        """ Test Coerce() """

        # int
        coerce_int = Coerce(int)
        schema = Schema(coerce_int)

        self.assertValid(schema, 1, 1)
        self.assertValid(schema, True, 1)
        self.assertValid(schema, u'1', 1)

        self.assertInvalid(schema, u'a',
                           Invalid(s.es_value, u'*' + s.t_int, u'a', [], coerce_int))

        # Callable
        intify = lambda x: int(x)
        intify.name = u'intify()'
        coerce_int = Coerce(intify)

        schema = Schema(coerce_int)

        self.assertValid(schema, u'1', 1)
        self.assertInvalid(schema, u'a',
                           Invalid(s.es_value, u'*intify()', u'a', [], coerce_int))

        # Callable which throws Invalid
        def intify(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                raise Invalid(u'Not an integer')
        coerce_int = Coerce(intify)
        schema = Schema(coerce_int)

        self.assertValid(schema, u'1', 1)
        self.assertInvalid(schema, u'a',
                           Invalid(u'Not an integer', u'*intify()', u'a', [], coerce_int))


class ValuesTest(GoodTestBase):
    """ Test: Validators.Values """

    def test_In(self):
        """ Test In() """
        allowed = In({1,2,3})
        schema = Schema(allowed)

        self.assertValid(schema, 1)
        self.assertValid(schema, 2)

        self.assertInvalid(schema, u'1',
                           Invalid(u'Value not allowed', u'In(1,2,3)', u'1', [], allowed))
        self.assertInvalid(schema, 99,
                           Invalid(u'Value not allowed', u'In(1,2,3)', u'99', [], allowed))

    def test_Length(self):
        """ Test Length() """

        for lencheck in (Length(1, 3), Length(1), Length(max=3)):
            schema = Schema(All(
                list,
                lencheck
            ))

            self.assertValid(schema, [1])
            self.assertValid(schema, [1,2])
            self.assertValid(schema, [1,2,3])

            if lencheck.min is None:
                self.assertValid(schema, [])
            else:
                self.assertInvalid(schema, [],
                                   Invalid(u'Too few values (1 is the least)', u'1', u'0', [], lencheck))

            if lencheck.max is None:
                self.assertValid(schema, [1,2,3,4])
            else:
                self.assertInvalid(schema, [1,2,3,4],
                                   Invalid(u'Too many values (3 is the most)', u'3', u'4', [], lencheck))

        # Test with a non-Sized input
        schema = Schema(lencheck)

        self.assertInvalid(schema, 1,
                           Invalid(u'Input is not a collection', u'Collection', s.t_int, [], lencheck))

        # Mapping: 2..3
        lencheck = Length(1, 3)
        schema = Schema({
            six.text_type: int,
            Entire: lencheck
        })

        self.assertValid(schema, {u'a': 1})
        self.assertValid(schema, {u'a': 1, u'b': 2})
        self.assertValid(schema, {u'a': 1, u'b': 2, u'c': 3})

        self.assertInvalid(schema, {}, MultipleInvalid([
            Invalid(s.es_required, s.t_unicode, s.v_no, [], Required(six.text_type)),
            Invalid(u'Too few values (1 is the least)', u'1', u'0', [], lencheck)
        ]))

    def test_Default(self):
        """ Test Default() and Fallback() """

        for validator in (Default(0), Fallback(0), lambda v: 0,):
            # Test as validator
            any = Any(
                int,
                validator
            )
            schema = Schema(any)

            self.assertValid(schema, 1)
            self.assertValid(schema, 0)
            self.assertValid(schema, None, 0)

            if type(validator) is Default:
                self.assertInvalid(schema, u'1',
                                   Invalid(s.es_value, u'Any('+s.t_int+u'|Default=0)', u'1', [], any))
            else:
                self.assertValid(schema, u'1', 0)

            # Test with mapping
            schema = Schema({
                u'name': six.text_type,
                u'age': any  # Default() is detected deep inside (using Undefined)
            })

            self.assertValid(schema, {u'name': u'Alex', u'age': 18})
            self.assertValid(schema, {u'name': u'Alex', u'age': None}, {u'name': u'Alex', u'age': 0})
            self.assertValid(schema, {u'name': u'Alex'},               {u'name': u'Alex', u'age': 0})

            if type(validator) is Default:
                self.assertInvalid(schema, {u'name': u'Alex', u'age': u'a'},
                                   Invalid(s.es_value, u'Any('+s.t_int+u'|Default=0)', u'a', [u'age'], any))
            else:
                self.assertValid(schema, {u'name': u'Alex', u'age': u'a'}, {u'name': u'Alex', u'age': 0})


class BooleansTest(GoodTestBase):
    """ Test: Validators.Booleans """

    def test_Check(self):
        """ Test Check() """

        check = Check(
            lambda v: v < 15,
            u'Must be <15',
            u'<15'
        )
        schema = Schema(check)

        self.assertValid(schema, 1)

        self.assertInvalid(schema, 15,
                           Invalid(u'Must be <15', u'<15', u'15', [], check))

    def test_Truthy(self):
        """ Test Truthy() """

        truthy = Truthy()
        schema = Schema(truthy)

        self.assertValid(schema, 1)
        self.assertValid(schema, u'abc')

        self.assertInvalid(schema, [],
                           Invalid(u'Empty value', u'Truthy', u'List[-]', [], truthy))

    def test_Falsy(self):
        """ Test Falsy() """

        falsy = Falsy()
        schema = Schema(falsy)

        self.assertValid(schema, 0)
        self.assertValid(schema, [])

        self.assertInvalid(schema, [1,2,3],
                           Invalid(u'Non-empty value', u'Falsy', u'List[...]', [], falsy))

    def test_Boolean(self):
        """ Test Boolean() """

        boolean_v = Boolean()
        schema = Schema(boolean_v)

        # Test valid
        tests = {
            True: (
                True, 1, -1, 100,
                u'y', u'Y', u'yes', u'Yes', u'YES', u'true', u'True', u'TRUE', u'on', u'On', u'ON'
            ),
            False: (
                None,
                False, 0,
                u'n', u'N', u'no', u'No', u'NO', u'false', u'False', u'FALSE', u'off', u'Off', u'OFF'
            )
        }
        for result, inputs in tests.items():
            for input in inputs:
                self.assertValid(schema, input, result)

        self.assertInvalid(schema, 0.0,
                           Invalid(u'Wrong boolean value type', u'Boolean', s.t_float, [], boolean_v))
        self.assertInvalid(schema, u'okay',
                           Invalid(u'Wrong boolean value', u'Boolean', u'okay', [], boolean_v))


class FilesTest(GoodTestBase):
    """ Test: Validators.Files """


class NumbersTest(GoodTestBase):
    """ Test: Validators.Numbers """


class StringsTest(GoodTestBase):
    """ Test: Validators.Strings """
