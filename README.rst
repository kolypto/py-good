|Build Status|

Good
====

Slim yet handsome validation library.

Core features:

-  Simple
-  Customizable
-  Supports nested model validation
-  Error paths (which field contains the error)
-  User-friendly error messages
-  Internationalization!
-  `Robust <misc/performance/performance.md>`__: 10 000 validations per
   second
-  Python 2.7, 3.3+ compatible

Inspired by the amazing
`alecthomas/voluptuous <https://github.com/alecthomas/voluptuous>`__ and
100% compatible with it. The whole internals have been reworked towards
readability and robustness. And yeah, the docs are now exhaustive :)

Table of Contents
=================

-  Schema

   -  Callables
   -  Priorities
   -  Creating a Schema
   -  Validating

-  Errors

   -  Invalid

      -  Invalid.enrich()

   -  MultipleInvalid

-  Markers

   -  Required
   -  Optional
   -  Remove
   -  Reject
   -  Allow
   -  Extra

-  Validation Tools

   -  Helpers

      -  Object
      -  Msg
      -  message
      -  truth

Schema
======

Validation schema.

A schema is a Python structure where nodes are pattern-matched against
the corresponding values. It leverages the full flexibility of Python,
allowing you to match values, types, data sctructures and much more.

When a schema is created, it's compiled into a callable function which
does the validation, hence it does not need to analyze the schema every
time.

Once the Schema is defined, validation can be triggered by calling it:

.. code:: python

    from good import Schema

    schema = Schema({ 'a': str })
    # Test
    schema({ 'a': 'i am a valid string' })

The following rules exist:

1. **Literal**: plain value is validated with direct comparison
   (equality check):

   .. code:: python

       Schema(1)(1)  #-> 1
       Schema(1)(2)  #-> Invalid: Invalid value: expected 1, got 2

2. **Type**: type schema produces an ``instanceof()`` check on the input
   value:

   .. code:: python

       Schema(int)(1)    #-> 1
       Schema(int)('1')
       #-> Invalid: Wrong type: expected Integer number, got Binary String

3. **Callable**: is applied to the value and the result is used as the
   final value.

Callables should raise ```Invalid`` <#invalid>`__ errors in case of a
failure, however some generic error types are converted automatically:
see `Callables <#callables>`__.

In addition, validators are allowed to transform a value to the required
form. For instance, ```Coerce(int)`` <#coerce>`__ returns a callable
which will convert input values into ``int`` or fail.

\`\`\`python def CoerceInt(v): # naive Coerce(int) implementation return
int(v)

Schema(CoerceInt)(1) #-> 1 Schema(CoerceInt)('1') #-> 1
Schema(CoerceInt)('a') #-> Invalid: ValueError: invalid literal for
int(): expected CoerceInt(), got a \`\`\`

4. **``Schema``**: a schema may contain sub-schemas:

   .. code:: python

       sub_schema = Schema(int)
       schema = Schema([None, sub_schema])

       schema([None, 1, 2])  #-> [None, 1, 2]
       schema([None, '1'])  #-> Invalid: invalid value

   Since ``Schema`` is callable, validation transparently by just
   calling it :)

Moreover, instances of the following types are converted to callables on
the compilation phase:

1. **Iterables** (``list``, ``tuple``, ``set``, custom iterables):

   Iterables are treated as a set of valid values, where each value in
   the input is compared against each value in the schema.

   In order for the input to be valid, it needs to have the same
   iterable type, and all of its values should have at least one
   matching value in the schema.

   .. code:: python

       schema = Schema([1, 2, 3])  # List of valid values

       schema([1, 2, 2])  #-> [1, 2, 2]
       schema([1, 2, 4])  #-> Invalid: Invalid value @ [2]: expected List[1|2|3], got 4
       schema((1, 2, 2))  #-> Invalid: Wrong value type: expected List, got Tuple

   Each value within the iterable is a schema as well, and validation
   requires that each member of the input value matches *any* of the
   schemas. Thus, an iterable is a way to define *OR* validation rule
   for every member of the iterable:

   .. code:: python

       Schema([ # All values should be
           # .. int ..
           int,
           # .. or a string, casted to int ..
           lambda v: int(v)
       ])([ 1, 2, '3' ])  #-> [ 1, 2, 3 ]

   This example works like this:

   1. Validate that the input value has the matching type: ``list`` in
      this case
   2. For every member of the list, test that there is a matching value
      in the schema.

      E.g. for value ``1`` -- ``int`` matches (immediate
      ``instanceof()`` check). However, for value ``'3'`` -- ``int``
      fails, but the callable manages to do it with no errors, and
      transforms the value as well.

      Since lists are ordered, the first schema that didn't fail is
      used.

2. **Mappings** (``dict``, custom mappings):

   Each key-value pair in the input mapping is validated against the
   corresponding schema pair:

   .. code:: python

       Schema({
           'name': str,
           'age': lambda v: int(v)
       })({
           'name': 'Alex',
           'age': '18',
       })  #-> {'name': 'Alex', 'age': 18}

   When validating, *both* keys and values are schemas, which allows to
   use nested schemas and interesting validation rules. For instance,
   let's use ```In`` <#in>`__ validator to match certain keys:

   .. code:: python

       from good import Schema, In

       Schema({
           # These two keys should have integer values
           In('age', 'height'): int,
           # All other keys should have string values
           str: str,
       })({
           'age': 18,
           'height': 173,
           'name': 'Alex',
       })

   This works like this:

   1. Test that the input has a matching type (``dict``)
   2. For each key in the input mapping, matching keys are selected from
      the schema
   3. Validate input values with the corresponding value in the schema.

   In addition, certain keys can be marked as
   ```Required`` <#required>`__ and ```Optional`` <#optional>`__. The
   default behavior is to have all keys required, but this can be
   changed by providing ``default_keys=Optional`` argument to the
   Schema.

   Finally, a mapping does not allow any extra keys (keys not defined in
   the schema). To change this, provide ``extra_keys=Allow`` to the
   ``Schema`` constructor.

These are just the basic rules, and for sure ``Schema`` can do much more
than that! Additional logic is implemented through
`Markers <#markers>`__ and `Validators <#validators>`__, which are
described in the following chapters.

Callables
---------

Finally, here are the things to consider when using custom callables for
validation:

-  Throwing errors.

   If the callable throws ```Invalid`` <#invalid>`__ exception, it's
   used as is with all the rich info it provides. Schema is smart enough
   to fill into most of the arguments (see
   ```Invalid.enrich`` <#invalidenrich>`__), so it's enough to use a
   custom message, and probably, set a human-friendly ``expected``
   field.

   In addition, specific error types are wrapped into ``Invalid``
   automatically: these are ``AssertionError``, ``TypeError``,
   ``ValueError``. Schema tries to do its best, but such messages will
   probably be cryptic for the user. Hence, always raise meaningful
   errors when creating custom validators. Still, this opens the
   possibility to use Python typecasting with validators like
   ``lambda v: int(v)``, since most of them are throwing ``TypeError``
   or ``ValueError``.

-  Naming.

   If the provided callable does not specify ``Invalid.expected``
   expected value, the ``__name__`` of the callable is be used instead.
   E.g. ``def intify(v):pass`` becomes ``'intify()'`` in reported
   errors.

   If a custom name is desired on the callable -- set the ``name``
   attribute on the callable object. This works best with classes,
   however a function can accept ``name`` attribute as well.

   For convenience, ```@message`` <#message>`__ and
   ```@name`` <#name>`__ decorators can be used on callables to specify
   the name and override the error message used when the validator
   fails.

-  Signals.

   A callable may decide that the value is soooo invalid that it should
   be dropped from the sanitized output. In this case, the callable
   should raise ``good.schema.signals.RemoveValue``.

   This is used by the ``Remove()`` marker, but can be leveraged by
   other callables as well.

Priorities
----------

Every schema type has a priority (`source <good/schema/util.py>`__),
which define the sequence for matching keys in a mapping schema:

1. Literals have highest priority
2. Types has lower priorities than literals, hence schemas can define
   specific rules for individual keys, and then declare general rules by
   type-matching:

   .. code:: python

       Schema({
           'name': str,  # Specific rule with a literal
           str: int,     # General rule with a type
       })

3. Callables, iterables, mappings -- have lower priorities.

In addition, `Markers <#markers>`__ have individual priorities, which
can be higher that literals (```Remove()`` <#remove>`__ marker) or lower
than callables (```Extra`` <#extra>`__ marker).

Creating a Schema
-----------------

.. code:: python

    Schema(schema, default_keys=None, extra_keys=None)

Creates a compiled ``Schema`` object from the given schema definition.

Under the hood, it uses ``SchemaCompiler``: see the
`source <good/schema/compiler.py>`__ if interested.

Arguments: \* ``schema``: Schema definition \* ``default_keys``: Default
mapping keys behavior: a ```Marker`` <#markers>`__ class used as a
default on mapping keys which are not Marker()ed with anything.

::

    Defaults to `markers.Required`.

-  ``extra_keys``: Default extra keys behavior: sub-schema, or a
   ```Marker`` <#markers>`__ class.

   Defaults to ``markers.Reject``

Throws: \* ``SchemaError``: Schema compilation error

Validating
----------

.. code:: python

    Schema.__call__(value)

Having a ```Schema`` <#schema>`__, user input can be validated by
calling the Schema on the input value.

When called, the Schema will return sanitized value, or raise
exceptions.

Arguments: \* ``value``: Input value to validate

Returns: ``None`` Sanitized value

Throws: \* ``good.MultipleInvalid``: Validation error on multiple
values. See ```MultipleInvalid`` <#multipleinvalid>`__. \*
``good.Invalid``: Validation error on a single value. See
```Invalid`` <#invalid>`__.

Errors
======

Source: `good/schema/errors.py <good/schema/errors.py>`__

When `validating user input <#validating>`__, ```Schema`` <#schema>`__
collects all errors and throws these after the whole input value is
validated. This makes sure that you can report *all* errors at once.

With simple schemas, like ``Schema(int)``, only a single error is
available: e.g. wrong value type. In this case,
```Invalid`` <#invalid>`__ error is raised.

However, with complex schemas with embedded structures and such,
multiple errors can occur: then [``MultipleInvalid``\ ] is reported.

All errors are available right at the top-level:

.. code:: python

    from good import Invalid, MultipleInvalid

Invalid
-------

.. code:: python

    Invalid(message, expected=None, provided=None, path=None,
            validator=None, **info)

Validation error for a single value.

This exception is guaranteed to contain text values which are meaningful
for the user.

Arguments: \* ``message``: Validation error message. \* ``expected``:
Expected value: info about the value the validator was expecting.

::

    If validator does not specify it -- the name of the validator is used.

-  ``provided``: Provided value: info about the value that was actually
   supplied by the user

   If validator does not specify it -- the input value is typecasted to
   string and stored here.
-  ``path``: Path to the error value.

   E.g. if an invalid value was encountered at ['a'].b[1], then
   path=['a', 'b', 1].
-  ``validator``: The validator that has failed: a schema item

``Invalid.enrich()``
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Invalid.enrich(expected=None, provided=None, path=None,
                   validator=None)

Enrich this error with additional information.

This works with both Invalid and MultipleInvalid (thanks to ``Invalid``
being iterable): in the latter case, the defaults are applied to all
collected errors.

The specified arguments are only set on ``Invalid`` errors which do not
have any value on the property.

One exclusion is ``path``: if provided, it is prepended to
``Invalid.path``. This feature is especially useful when validating the
whole input with multiple different schemas:

.. code:: python

    from good import Schema, Invalid

    schema = Schema(int)
    input = {
        'user': {
            'age': 10,
        }
    }

    try:
        schema(input['user']['age'])
    except Invalid as e:
        e.enrich(path=['user', 'age'])  # Make the path reflect the reality
        raise  # re-raise the error with updated fields

This is used when validating a value within a container.

Arguments: \* ``expected``: Invalid.expected default \* ``provided``:
Invalid.provided default \* ``path``: Prefix to prepend to Invalid.path
\* ``validator``: Invalid.validator default

Returns: ``Invalid|MultipleInvalid``

MultipleInvalid
---------------

.. code:: python

    MultipleInvalid(errors)

Validation errors for multiple values.

This error is raised when the ```Schema`` <#schema>`__ has reported
multiple errors, e.g. for several dictionary keys.

``MultipleInvalid`` has the same attributes as
```Invalid`` <#invalid>`__, but the values are taken from the first
error in the list.

In addition, it has the ``errors`` attribute, which is a list of
```Invalid`` <#invalid>`__ errors collected by the schema. The list is
guaranteed to be plain: e.g. there will be no underlying hierarchy of
``MultipleInvalid``.

Note that both ``Invalid`` and ``MultipleInvalid`` are iterable, which
allows to process them in singularity:

.. code:: python

    try:
        schema(input_value)
    except Invalid as ee:
        reported_problems = {}
        for e in ee:  # Iterate over `Invalid`
            path_str = u'.'.join(e.path)  # 'a.b.c.d', JavaScript-friendly :)
            reported_problems[path_str] = e.message
        #.. send reported_problems to the user

In this example, we create a dictionary of paths (as strings) mapped to
error strings for the user.

Arguments: \* ``errors``: The reported errors.

::

    If it contains `MultipleInvalid` errors -- the list is recursively flattened
    so all of them are guaranteed to be instances of [`Invalid`](#invalid).

Markers
=======

A *Marker* is a proxy class which wraps some schema.

Immediately, the example is:

.. code:: python

    from good import Schema, Required

    Schema({
        'name': str,  # required key
        Optional('age'): int,  # optional key
    }, default_keys=Required)

This way, keys marked with ``Required()`` will report errors if no value
if provided.

Typically, a marker "decorates" a mapping key, but some of them can be
"standalone":

.. code:: python

    from good import Schema, Extra
    Schema({
        'name': str,
        Extra: int  # allow any keys, provided their values are integer
    })

Each marker can have it's own unique behavior since nothing is hardcoded
into the core ```Schema`` <#schema>`__. Keep on reading to learn how
markers perform.

``Required``
------------

.. code:: python

    Required(key)

``Required(key)`` is used to decorate mapping keys and hence specify
that these keys must always be present in the input mapping.

When compiled, ```Schema`` <#schema>`__ uses ``default_keys`` as the
default marker:

.. code:: python

    from good import Schema, Required

    schema = Schema({
        'name': str,
        'age': int
    }, default_keys=Required)  # wrap with Required() by default

    schema({'name': 'Mark'})
    #-> Invalid: Required key not provided @ ['age']: expected age, got -none-

Remember that mapping keys are schemas as well, and ``Require`` will
expect to always have a match:

.. code:: python

    schema = Schema({
        Required(str): int,
    })

    schema({})  # no `str` keys provided
    #-> Invalid: Required key not provided: expected String, got -none-

Arguments:

``Optional``
------------

.. code:: python

    Optional(key)

``Optional(key)`` is controversial to ```Required(key)`` <#required>`__:
specified that the mapping key is not required.

This only has meaning when a ```Schema`` <#schema>`__ has
``default_keys=Required``: then, it decorates all keys with
``Required()``, unless a key is already decorated with some Marker.
``Optional()`` steps in: those keys are already decorated and hence are
not wrapped with ``Required()``.

So, it's only used to prevent ``Schema`` from putting ``Required()`` on
a key. In all other senses, it has absolutely no special behavior.

As a result, optional key can be missing, but if it was provided -- its
value must match the value schema.

Example: use as ``default_keys``:

.. code:: python

    schema = Schema({
        'name': str,
        'age': int
    }, default_keys=Optional)  # Make all keys optional by default

    schema({})  #-> {} -- okay
    schema({'name': None})
    #->  Invalid: Wrong type @ ['name']: expected String, got None

Example: use to mark specific keys are not required:

.. code:: python

    schema = Schema({
        'name': str,
        Optional(str): int  # key is optional
    })

    schema({'name': 'Mark'})  # valid
    schema({'name': 'Mark', 'age': 10})  # valid
    schema({'name': 'Mark', 'age': 'X'})
    #-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String

Arguments:

``Remove``
----------

.. code:: python

    Remove(key)

``Remove(key)`` marker is used to declare that the key, if encountered,
should be removed, without validating the value.

``Remove`` has highest priority, so it operates before everything else
in the schema.

Example:

.. code:: python

    schema = Schema({
        Remove('name'): str, # `str` does not mean anything since the key is removed anyway
        'age': int
    })

    schema({'name': 111, 'age': 18})  #-> {'age': 18}

However, it's more natural to use ``Remove()`` on values. Remember that
in this case ``'name'`` will become ```Required()`` <#required>`__, if
not decorated with ```Optional()`` <#optional>`__:

.. code:: python

    schema = Schema({
        Optional('name'): Remove
    })

    schema({'name': 111, 'age': 18})  #-> {'age': 18}

**Bonus**: ``Remove()`` can be used in iterables as well:

.. code:: python

    schema = Schema([str, Remove(int)])
    schema(['a', 'b', 1, 2])  #-> ['a', 'b']

Arguments:

``Reject``
----------

.. code:: python

    Reject(key)

``Reject(key)`` marker is used to report ```Invalid`` <#invalid>`__
errors every time is matches something in the input.

It has lower priority than most of other schemas, so rejection will only
happen if no other schemas has matched this value.

Example:

.. code:: python

    schema = Schema({
        Reject('name'): None,  # Reject by key
        Optional('age'): Msg(Reject, u"Field is not supported anymore"), # alternative form
    })

    schema({'name': 111})
    #-> Invalid: Field is not supported anymore @ ['name']: expected -none-, got name

Arguments:

``Allow``
---------

.. code:: python

    Allow(key)

``Allow(key)`` is a no-op marker that never complains on anything.

Designed to be used with ```Extra`` <#extra>`__.

Arguments:

``Extra``
---------

.. code:: python

    Extra(key)

``Extra`` is a catch-all marker to define the behavior for mapping keys
not defined in the schema.

It has the lowest priority, and delegates its function to its value,
which can be a schema, or another marker.

Given without argument, it's compiled with an identity function
``lambda x:x`` which is a catch-all: it matches any value. Together with
lowest priority, ``Extra`` will only catch values which did not match
anything else.

Every mapping has an ``Extra`` implicitly, and ``extra_keys`` argument
controls the default behavior.

Example with ``Extra: <schema>``:

.. code:: python

    schema = Schema({
        'name': str,
        Extra: int  # this will allow extra keys provided they're int
    })

    schema({'name': 'Alex', 'age': 18'})  #-> ok
    schema({'name': 'Alex', 'age': 'X'})
    #-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String

Example with ``Extra: Reject``: reject all extra values:

.. code:: python

    schema = Schema({
        'name': str,
        Extra: Reject
    })

    schema({'name': 'Alex', 'age': 'X'})
    #-> Invalid: Extra keys not allowed @ ['age']: expected -none-, got age

Example with ``Extra: Remove``: silently discard all extra values:

.. code:: python

    schema = Schema({'name': str}, extra_keys=Remove)
    schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex'}

Example with ``Extra: Allow``: allow any extra values:

.. code:: python

    schema = Schema({'name': str}, extra_keys=Allow)
    schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex', 'age': 'X'}

Arguments:

Validation Tools
================

Helpers
-------

Collection of miscellaneous helpers to alter the validation process.

``Object``
~~~~~~~~~~

.. code:: python

    Object(schema, cls=None)

Specify that the provided mapping should validate an object.

This uses the same mapping validation rules, but works with attributes
instead:

.. code:: python

    from good import Schema, Object

    intify = lambda v: int(v)  # Naive Coerce(int) implementation

    # Define a class to play with
    class Person(object):
        category = u'Something'  # Not validated

        def __init__(self, name, age):
            self.name = name
            self.age = age

    # Schema
    schema = Schema(Object({
        'name': str,
        'age': intify,
    }))

    # Validate
    schema(Person(name=u'Alex', age='18'))  #-> Girl(name=u'Alex', age=18)

Internally, it validates the object's ``__dict__``: hence, class
attributes are excluded from validation. Validation is performed with
the help of a wrapper class which proxies object attributes as mapping
keys, and then Schema validates it as a mapping.

This inherits the default required/extra keys behavior of the Schema. To
override, use ```Optional()`` <#optional>`__ and ```Extra`` <#extra>`__
markers.

Arguments: \* ``schema``: Object schema, given as a mapping \* ``cls``:
Require instances of a specific class. If ``None``, allows all classes.

Returns: ``callable`` Validator

``Msg``
~~~~~~~

.. code:: python

    Msg(schema, message)

Override the error message reported by the wrapped schema in case of
validation errors.

On validation, if the schema throws ```Invalid`` <#invalid>`__ -- the
message is overridden with ``msg``.

Some other error types are converted to ``Invalid``: see notes on
`Schema Callables <#callables>`__.

.. code:: python

    from good import Schema, Msg

    intify = lambda v: int(v)  # Naive Coerce(int) implementation
    intify.name = u'Number'

    schema = Schema(Msg(intify, u'Need a number'))
    schema(1)  #-> 1
    schema('a')
    #-> Invalid: Need a number: expected Number, got a

Arguments: \* ``schema``: The wrapped schema to modify the error for \*
``message``: Error message to use instead of the one that's reported by
the underlying schema

Returns: ``callable`` Wrapped schema callable

``message``
~~~~~~~~~~~

.. code:: python

    message(message, name=None)

Convenience decorator that applies ```Msg()`` <#msg>`__ to a callable.

.. code:: python

    from good import Schema, message

    @message(u'Need a number')
    def intify(v):
        return int(v)

Arguments: \* ``message``: Error message to use instead \* ``name``:
Override schema name as well. See ```name`` <#name>`__.

Returns: ``callable`` Validator callable

``name``
~~~~~~~~

.. code:: python

    name(name, validator=None)

Set a name on a validator callable.

Useful for user-friendly reporting when using lambdas to populate the
```Invalid.expected`` <#invalid>`__ field:

.. code:: python

    from good import Schema, name

    Schema(lambda x: int(x))('a')
    #-> Invalid: ValueError: invalid literal for int(): expected <lambda>(), got
    Schema(name('int()', lambda x: int(x))('a')
    #-> Invalid: ValueError: invalid literal for int(): expected int(), got a

Note that it is only useful with lambdas, since function name is used if
available: see notes on `Schema Callables <#callables>`__.

Arguments: \* ``name``: Name to assign on the validator callable \*
``validator``: Validator callable. If not provided -- a decorator is
returned instead:

::

    ```python
    @name(u'int()')
    def int(v):
        return int(v)
    ```

Returns: ``callable`` The same validator callable

``truth``
~~~~~~~~~

.. code:: python

    truth(message, expected=None)

Convenience decorator that converts a boolean function into a validator.

.. code:: python

    import os.path
    from good import Schema, truth

    @truth(u'Must be an existing directory')
    def isDir(v):
        return os.path.isdir(v)

    schema = Schema(isDir)
    schema('/')  #-> '/'
    schema('/404')
    #-> Invalid: Must be an existing directory: expected isDir(), got /404

Arguments: \* ``message``: Validation error message \* ``expected``:
Expected value string representation, or ``None`` to get it from the
wrapped callable

Returns: ``callable`` Validator callable

Predicates
----------

``Any``
~~~~~~~

.. code:: python

    Any(*schemas)

Try the provided schemas in order and use the first one that succeeds.

This is the *OR* condition predicate: any of the schemas should match.

.. code:: python

    from good import Schema, Any

    schema = Schema(Any(
        # allowed string constants
        'true', 'false',
        # otherwise coerce as a bool
        lambda v: 'true' if v else 'false'
    ))
    schema('true')  #-> 'true'
    schema(0)  #-> 'false'

Arguments:

``All``
~~~~~~~

.. code:: python

    All(*schemas)

Value must pass all validators wrapped with ``All()`` predicate.

This is the *AND* condition predicate: all of the schemas should match
in order, which is in fact a composition of validators:
``All(f,g)(value) = g(f(value))``.

.. code:: python

    from good import Schema, All, Range

    schema = Schema(All(
        # Must be an integer ..
        int,
        # .. and in the allowed range
        Range(0, 10)
    ))

    schema(1)  #-> 1
    schema(99)
    #-> Invalid: Not in range: expected 0..10, got 99

Arguments:

Types
-----

Values
------

Boolean
-------

Numbers
-------

Strings
-------

Files
-----

.. |Build Status| image:: https://api.travis-ci.org/kolypto/py-good.png?branch=master
   :target: https://travis-ci.org/kolypto/py-good
