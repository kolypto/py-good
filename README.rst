|Build Status|

Good
====

Slim yet handsome validation library.

Core features:

-  Simple
-  Customizable
-  Supports nested validation
-  User-friendly error messages
-  Internationalization!

Inspired by the amazing
`alecthomas/voluptuous <https://github.com/alecthomas/voluptuous>`__ and
100% compatible with it. The whole internals have been reworked towards
readability and robustness. And yeah, the docs are now exhaustive :)

Table of Contents
=================

Schema
======

Validation schema.

A schema is a Python structure where nodes are pattern-matched against
the corresponding values.

Once the Schema is defined, validation can be triggered by calling it:

.. code:: python

    schema = Schema({ 'a': str })
    # Test
    schema({ 'a': 'i am a valid string' })

The following rules exist:

1. Literal: plain value is validated with direct comparison (equality
   check):

   .. code:: python

       Schema(1)(1)  #-> 1
       Schema(1)(2)  #-> Incorrect value

2. Type: is tested with ``instanceof()`` check:

   .. code:: python

       Schema(int)(1)    #-> 1
       Schema(int)('1')  #-> Invalid: expecting an integer, string given

3. Callable: is applied to the value and the result is used as the final
   value. Any errors raised by the callable are treated as validation
   errors.

In addition, validators are allowed to mutate a value to a given form.
For instance, ```Coerce(int)`` <#coerce>`__ returns a callable which
will convert input values into ``int`` or fail.

\`\`\`python CoerceInt = lambda v: int(v) # naive Coerce(int)
implementation

Schema(CoerceInt)(1) #-> 2 Schema(CoerceInt)('1') # Invalid: invalid
value \`\`\`

If the callable trows ```Invalid`` <#invalid>`__ exception, it's used as
is. Other exceptions are wrapped into ``Invalid`` and re-raised.

4. ``Schema``: a schema may contain sub-schemas:

   .. code:: python

       Schema(Schema(int))

   Since ``Schema`` is callable, validation transparently by just
   calling it :)

Moreover, instances of the following types are converted to callables on
the compilation phase:

1. Iterables (``list``, ``tuple``, ``set``, custom iterables):

   Iterables are treated as a set of valid values, where each value in
   the input is compared against the given set of valid values.

   In addition, the input iterable must have the given type:

   .. code:: python

       schema = Schema([1, 2, 3])

       schema([1, 2, 2])  #-> [1]
       schema([1, 2, 4])  #-> Invalid: invalid list value @ [2]
       schema((1, 2, 2))  #-> Invalid: expecting a list, tuple given

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

   a. Validate that the input value has the matching type: ``list`` in
      this case
   b. For every member of the list, test that there is a matching value
      in the schema.

      Since lists are ordered, the first schema that didn't fail is
      used.

      E.g. for value ``1`` -- ``int`` matches (immediate
      ``instanceof()`` check). However, for value ``'3'`` -- ``int``
      fails, but the callable manages to do it with no errors.

2. Mappings (``dict``, custom mappings):

   Each key-value pair in the input mapping is validated against the
   corresponding schema pair:

   .. code:: python

       Schema({
           'name': str,
           'age': lambda v: int(v)
       })({
           'name':  'Alex',
           'age': '18',
       })  #-> {'name': 'Alex', 'age': 18}

   When validating, *both* keys and values are schemas, which allows to
   use nested schemas and interesting validation rules. For instance,
   let's use ```In`` <#in>`__ validator to match certain keys:

   .. code:: python

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

   a. Test that the input has a matching type (``dict``)
   b. For each key in the input mapping, matching keys are selected from
      the schema
   c. Validate input values with the corresponding value in the schema.

   In addition, certain keys can be marked as
   ```Required`` <#required>`__ and ```Optional`` <#optional>`__. The
   default behavior is to have all keys optional, but this can be
   changed by providing ``required=True`` argument to the Schema.

   Finally, a mapping does not allow any extra keys (keys not defined in
   the schema). To change this, provide ``extra=True`` to the ``Schema``
   constructor.

These are just the basic rules, and for sure ``Schema`` can do much more
than that! Additional logic is implemented through
`Markers <#markers>`__ and `Validators <#validators>`__, which are
described in the next chapters.

Creating a Schema
-----------------

.. code:: python

    Schema(schema, required=False, extra=False)

Create a ``Schema`` object from the given schema.

.. |Build Status| image:: https://api.travis-ci.org/kolypto/py-good.png?branch=master
   :target: https://travis-ci.org/kolypto/py-good
