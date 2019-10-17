from __future__ import print_function
import unittest
import re
from contextlib import contextmanager

from good.voluptuous import *



@contextmanager
def raises(exc, msg=None):
    """ The original voluptuous unit-test utility, modified to our needs """
    try:
        yield
        assert 0, u'False positive'
    except exc as e:
        assert type(e) == exc, u'{} != {}: {}'.format(type(e), exc, e)

        if isinstance(e, MultipleInvalid):
            ee = e
            for e in ee.errors:
                if str(e) == msg:
                    break
            else:
                assert False, u'None of MultipleInvalid matched:' + u'\n' + \
                              u'\n'.join(u'* ' + repr(str(e)) for e in ee.errors)
        elif isinstance(e, Invalid):
            assert str(e) == msg, u'Wrong error message:\n* ' + str(e)
        else:
            assert 0, 'Wrong exc class: {}'.format(e)



class VoluptuousTest(unittest.TestCase):
    """ Compatibility layer tests """

    def test_module_docstring(self):
        """ Test from the doccomment """
        settings = {
            # TODO: propagate `Required()` by default. This can only be achieved if compiler propagates down the validator chain, e.g. with a special compile() method
            #'snmp_community': str,
            Optional('snmp_community'): str,
            #'retries': int,
            Optional('retries'): int,
            #'snmp_version': All(Coerce(str), Any('3', '2c', '1')),
            Optional('snmp_version'): All(Coerce(str), Any('3', '2c', '1')),
            }
        features = ['Ping', 'Uptime', 'Http']

        schema = Schema({
            'exclude': features,
            'include': features,
            'set': settings,
            'targets': {
                'exclude': features,
                #'include': features,
                Optional('include'): features,
                'features': {
                    str: settings,
                    },
                },
            })

        self.assertEqual(
            schema({
                'set': {
                    'snmp_community': 'public',
                    'snmp_version': '2c',
                },
                'targets': {
                    'exclude': ['Ping'],
                    'features': {
                        'Uptime': {'retries': 3},
                        'Users': {'snmp_community': 'monkey'},
                    },
                },
            }),
            {
                'set': {'snmp_version': '2c', 'snmp_community': 'public'},
                'targets': {
                    'exclude': ['Ping'],
                    'features': {'Uptime': {'retries': 3},
                                 'Users': {'snmp_community': 'monkey'}}}}
        )

    def test_compile_object(self):
        # From: def _compile_object(self, schema):
        class Structure:
            def __init__(self, one=None, three=None):
                self.one = one
                self.three = three

        validate = Schema(Object({'one': 'two', 'three': 'four'}, cls=Structure))
        with raises(MultipleInvalid, u"Invalid value, expected two @ data['one']"):#"not a valid value for object value @ data['one']"):
            validate(Structure(one='three'))

    def test_compile_dict(self):
        # From: def _compile_dict(self, schema):
        validate = Schema({})
        #with raises(MultipleInvalid, 'expected a dictionary'):
        with raises(MultipleInvalid, u"Wrong value type, expected Dictionary"):
            validate([])

        validate = Schema({'one': 'two', 'three': 'four'})
        #with raises(MultipleInvalid, "not a valid value for dictionary value @ data['one']"):
        with raises(MultipleInvalid, u"Invalid value, expected two @ data['one']"):
            validate({'one': 'three'})

        #with raises(Invalid, "extra keys not allowed @ data['two']"):
        with raises(MultipleInvalid, u"Extra keys not allowed @ data['two']"):
            validate({'two': 'three'})

        validate = Schema({'one': 'two', 'three': 'four', int: str})
        v=validate({10: 'twenty'})
        self.assertEqual(v, {10: 'twenty'})

        #with raises(MultipleInvalid, "extra keys not allowed @ data['10']"):
        with raises(MultipleInvalid, u"Extra keys not allowed @ data['10']"):
            validate({'10': 'twenty'})

        validate = Schema({'one': 'two', 'three': 'four', Coerce(int): str})
        v=validate({'10': 'twenty'})
        self.assertEqual(v, {10: 'twenty'})

        validate = Schema({Required('one', 'required'): 'two'})
        #with raises(MultipleInvalid, "required @ data['one']"):
        with raises(MultipleInvalid, u"required, expected one @ data['one']"):
            validate({})

        validate = Schema({
            'adict': {
                'strfield': bytes,
                'intfield': int
            }
        })
        try:
            validate({
                'adict': {
                    'strfield': 123,
                    'intfield': 'one'
                }
            })
        except MultipleInvalid as ee:
            errors = sorted(str(e) for e in ee.errors)
            self.assertEqual(errors, [
                # "expected str for dictionary value @ data['adict']['strfield']",
                u"Wrong type, expected Binary String @ data['adict']['strfield']",
                #"expected int for dictionary value @ data['adict']['intfield']",
                u"Wrong type, expected Integer number @ data['adict']['intfield']",
            ])

    def test_compile_sequence(self):
        # Found: def _compile_sequence(self, schema, seq_type):
        validator = Schema(['one', 'two', int])

        v=validator(['one'])
        self.assertEqual(v, ['one'])

        #with raises(MultipleInvalid, 'invalid list value @ data[0]'):
        with raises(MultipleInvalid, u"Invalid value, expected List[one|two|Integer number] @ data[0]"):
            validator([3.5])

        v=validator([1])
        self.assertEqual(v, [1])

    def test_compile_tuple(self):
        # Found: def _compile_tuple(self, schema):
        validator = Schema(('one', 'two', int))

        v=validator(('one',))
        self.assertEqual(v, ('one',))

        #with raises(MultipleInvalid, 'invalid tuple value @ data[0]'):
        with raises(MultipleInvalid, u"Invalid value, expected Tuple[one|two|Integer number] @ data[0]"):
            validator((3.5,))

        v=validator((1,))
        self.assertEqual(v, (1,))

    def test_compile_list(self):
        # Found: def _compile_list(self, schema):
        validator = Schema(['one', 'two', int])

        v=validator(['one'])
        self.assertEqual(v, ['one'])

        #with raises(MultipleInvalid, 'invalid list value @ data[0]'):
        with raises(MultipleInvalid, u"Invalid value, expected List[one|two|Integer number] @ data[0]"):
            validator([3.5])

        v=validator([1])
        self.assertEqual(v, [1])

    def test_compile_scalar(self):
        def _compile_scalar(schema):
            schema = Schema(schema)
            return lambda path, v: schema(v)

        # Found: def _compile_scalar(schema):
        v=_compile_scalar(int)([], 1)
        self.assertEqual(v, 1)

        #with raises(Invalid, 'expected float'):
        with raises(MultipleInvalid, u"Wrong type, expected Fractional number"):
            _compile_scalar(float)([], '1')

        v=_compile_scalar(lambda v: float(v))([], '1')
        self.assertEqual(v, 1.0)

        # Remember what error message does Python use for float('a')
        try:
            float('a')
        except ValueError as e:
            PY_STR2FLOAT_MESSAGE = str(e)

        #with raises(Invalid, 'not a valid value'):
        with raises(MultipleInvalid, PY_STR2FLOAT_MESSAGE+u", expected <lambda>()"):  # yes, that's not user-friendly, but lambdas don't provide much info
            _compile_scalar(lambda v: float(v))([], 'a')

    def test_Required(self):
        # Found: class Required(Marker):

        schema = Schema({Required('key'): str})

        #with raises(MultipleInvalid, "required key not provided @ data['key']"):
        with raises(MultipleInvalid, u"Required key not provided, expected key @ data['key']"):
            schema({})

        schema = Schema({Required('key', default='value'): str})
        v = schema({})
        self.assertEqual(v, {'key': 'value'})

    def test_Msg(self):
        # Found: def Msg(schema, msg):
        validate = Schema(
          Msg(['one', 'two', int],
              'should be one of "one", "two" or an integer'))

        #with raises(MultipleInvalid, 'should be one of "one", "two" or an integer'):
        with raises(MultipleInvalid, u"should be one of \"one\", \"two\" or an integer, expected List[one|two|Integer number] @ data[0]"):
            validate(['three'])
    
        validate = Schema(Msg([['one', 'two', int]], 'not okay!'))
        #with raises(MultipleInvalid, 'invalid list value @ data[0][0]'):
        with raises(MultipleInvalid, u"not okay!, expected List[one|two|Integer number] @ data[0][0]"):
            validate([['three']])

    def test_message(self):
        # Found: def message(default=None):
        @message('not an integer')
        def isint(v):
            return int(v)

        validate = Schema(isint())
        #with raises(MultipleInvalid, 'not an integer'):
        with raises(MultipleInvalid, u"not an integer, expected isint()"):
            validate('a')

        validate = Schema(isint('bad'))
        #with raises(MultipleInvalid, 'bad'):
        with raises(MultipleInvalid, u"bad, expected isint()"):
            validate('a')

    def test_truth(self):
        # Found: def truth(f):
        @truth
        def isdir(v):
          return os.path.isdir(v)
        validate = Schema(isdir)

        v=validate('/')
        self.assertEqual(v, '/')

        #with raises(MultipleInvalid, 'not a valid value'):
        with raises(MultipleInvalid, u"not a valid value, expected isdir()"):
          validate('/notavaliddir')

    def test_Coerce(self):
        # Found: def Coerce(type, msg=None):
        validate = Schema(Coerce(int))

        #with raises(MultipleInvalid, 'expected int'):
        with raises(MultipleInvalid, u"Invalid value, expected *Integer number"):
            validate(None)

        #with raises(MultipleInvalid, 'expected int'):
        with raises(MultipleInvalid, u"Invalid value, expected *Integer number"):
            validate('foo')

        validate = Schema(Coerce(int, "moo"))
        #with raises(MultipleInvalid, 'moo'):
        with raises(MultipleInvalid, u"moo, expected *Integer number"):
            validate('foo')

    def test_IsTrue(self):
        # Found: def IsTrue(v):
        validate = Schema(IsTrue())

        #with raises(MultipleInvalid, "value was not true"):
        with raises(MultipleInvalid, u"Empty value, expected Truthy"):
            validate([])

        v=validate([1])
        self.assertEqual(v, [1])

        #with raises(MultipleInvalid, "value was not true"):
        with raises(MultipleInvalid, u"Empty value, expected Truthy"):
            validate(False)

    def test_IsFalse(self):
        # Found: def IsFalse(v):
        validate = Schema(IsFalse())

        v=validate([])
        self.assertEqual(v, [])

    def test_Boolean(self):
        # Found: def Boolean(v):
        validate = Schema(Boolean())

        v=validate(True)
        self.assertEqual(v, True)

        #with raises(MultipleInvalid, "expected boolean"):
        with raises(MultipleInvalid, u"Wrong boolean value, expected Boolean"):
            validate('moo')

    def test_Any(self):
        # Found: def Any(*validators, **kwargs):
        validate = Schema(Any(
            'true', 'false',
            All(
                Any(int, bool),
                Coerce(bool))
        ))

        v=validate('true')
        self.assertEqual(v, 'true')

        v=validate(1)
        self.assertEqual(v, True)

        #with raises(MultipleInvalid, "not a valid value"):
        with raises(MultipleInvalid, u"Invalid value, expected Any(true|false|All(Any(Integer number|Boolean) & *Boolean))"):
            validate('moo')

        validate = Schema(Any(1, 2, 3, msg="Expected 1 2 or 3"))

        v=validate(1)
        self.assertEqual(v, 1)

        #with raises(MultipleInvalid, "Expected 1 2 or 3"):
        with raises(MultipleInvalid, "Expected 1 2 or 3, expected Any(1|2|3)"):
            validate(4)

    def test_All(self):
        # Found: def All(*validators, **kwargs):
        validate = Schema(All('10', Coerce(int)))

        v=validate('10')
        self.assertEqual(v, 10)

    def test_Match(self):
        # Found: def Match(pattern, msg=None):
        validate = Schema(Match(r'^0x[A-F0-9]+$'))

        v=validate('0x123EF4')
        self.assertEqual(v, '0x123EF4')

        #with raises(MultipleInvalid, "does not match regular expression"):
        with raises(MultipleInvalid, u"Wrong format, expected (special format)"):
            validate('123EF4')

        #with raises(MultipleInvalid, 'expected string or buffer'):
        with raises(MultipleInvalid, u"Wrong value type, expected String"):
            validate(123)

        validate = Schema(Match(re.compile(r'0x[A-F0-9]+', re.I)))

        v=validate('0x123ef4')
        self.assertEqual(v, '0x123ef4')

    def test_Replace(self):
        # Found: def Replace(pattern, substitution, msg=None):
        validate = Schema(All(Replace('you', 'I'), Replace('hello', 'goodbye')))

        v=validate('you say hello')
        self.assertEqual(v, 'I say goodbye')

    def test_IsDir(self):
        # Found: def IsDir(v):
        v=IsDir()('/')
        self.assertEqual(v, '/')

    def test_Range(self):
        # Found: def Range(min=None, max=None, min_included=True, max_included=True, msg=None):
        s = Schema(Range(min=1, max=10, min_included=False))

        v=s(5)
        self.assertEqual(v, 5)

        v=s(10)
        self.assertEqual(v, 10)

        #with raises(MultipleInvalid, 'value must be at most 10'):
        with raises(MultipleInvalid, u"Value must be at most 10, expected 10"):
          s(20)

        #with raises(MultipleInvalid, 'value must be higher than 1'):
        with raises(MultipleInvalid, u"Value must be at least 2, expected 2"):
          s(1)

    def test_Lower(self):
        # Found: def Lower(v):
        s = Schema(Lower)

        v=s('HI')
        self.assertEqual(v, 'hi')

    def test_DefaultTo(self):
        # Found: def DefaultTo(default_value, msg=None):
        s = Schema(DefaultTo(42))

        v=s(None)
        self.assertEqual(v, 42)

    def tests_py(self):
        # Found: tests.py

        schema = Schema({Required('q'): 1})
        try:
            schema({})
        except Invalid as e:
            #self.assertEqual(str(e), "required key not provided @ data['q']")
            self.assertEqual(str(e), u"Required key not provided, expected q @ data['q']")
        else:
            assert False, "Did not raise Invalid"

        schema = Schema({Required('toaster'): str, Extra: str})
        r = schema({'toaster': 'blue', 'another_valid_key': u'another_valid_value'})
        self.assertEqual(
            r, {'toaster': 'blue', 'another_valid_key': u'another_valid_value'})

        schema = Schema({"color": In(frozenset(["blue", "red", "yellow"]))})
        schema({"color": "blue"})


