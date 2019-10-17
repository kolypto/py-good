[![Build Status](https://api.travis-ci.org/kolypto/py-good.png?branch=master)](https://travis-ci.org/kolypto/py-good)
[![Pythons](https://img.shields.io/badge/python-3.5%E2%80%933.8%20%7C%20pypy3-blue.svg)](.travis.yml)







Good
====

Slim yet handsome validation library.

Core features:

* Simple
* Customizable
* Supports nested model validation
* Error paths (which field contains the error)
* User-friendly error messages
* Internationalization!
* Was created with performance in mind
* 100% documented and unit-tested

Inspired by the amazing [alecthomas/voluptuous](https://github.com/alecthomas/voluptuous) and 100% compatible with it.
The whole internals have been reworked towards readability and robustness. And yeah, the docs are now exhaustive :)

The rationale for a remake was to make it modular with a tiny core and everything else built on top of that,
ensure that all error messages are user-friendly out of the box, and tweak the performance.


Table of Contents
=================

* <a href="#voluptuous-drop-in-replacement">Voluptuous Drop-In Replacement</a>
* <a href="#schema">Schema</a>
    * <a href="#callables">Callables</a>
    * <a href="#priorities">Priorities</a>
    * <a href="#creating-a-schema">Creating a Schema</a>
    * <a href="#validating">Validating</a>
* <a href="#errors">Errors</a>
    * <a href="#invalid">Invalid</a>
        * <a href="#invalidenrich">Invalid.enrich()</a>
    * <a href="#multipleinvalid">MultipleInvalid</a>
* <a href="#markers">Markers</a>
    * <a href="#required">Required</a>
    * <a href="#optional">Optional</a>
    * <a href="#remove">Remove</a>
    * <a href="#reject">Reject</a>
    * <a href="#allow">Allow</a>
    * <a href="#extra">Extra</a>
    * <a href="#entire">Entire</a>
* <a href="#validation-tools">Validation Tools</a>
    * <a href="#helpers">Helpers</a>
        * <a href="#object">Object</a>
        * <a href="#msg">Msg</a>
        * <a href="#test">Test</a>
        * <a href="#message">message</a>
        * <a href="#name">name</a>
        * <a href="#truth">truth</a>
    * <a href="#predicates">Predicates</a>
        * <a href="#maybe">Maybe</a>
        * <a href="#any">Any</a>
        * <a href="#all">All</a>
        * <a href="#neither">Neither</a>
        * <a href="#inclusive">Inclusive</a>
        * <a href="#exclusive">Exclusive</a>
    * <a href="#types">Types</a>
        * <a href="#type">Type</a>
        * <a href="#coerce">Coerce</a>
    * <a href="#values">Values</a>
        * <a href="#in">In</a>
        * <a href="#length">Length</a>
        * <a href="#default">Default</a>
        * <a href="#fallback">Fallback</a>
        * <a href="#map">Map</a>
    * <a href="#boolean">Boolean</a>
        * <a href="#check">Check</a>
        * <a href="#truthy">Truthy</a>
        * <a href="#falsy">Falsy</a>
        * <a href="#boolean-1">Boolean</a>
    * <a href="#numbers">Numbers</a>
        * <a href="#range">Range</a>
        * <a href="#clamp">Clamp</a>
    * <a href="#strings">Strings</a>
        * <a href="#lower">Lower</a>
        * <a href="#upper">Upper</a>
        * <a href="#capitalize">Capitalize</a>
        * <a href="#title">Title</a>
        * <a href="#match">Match</a>
        * <a href="#replace">Replace</a>
        * <a href="#url">Url</a>
        * <a href="#email">Email</a>
    * <a href="#dates">Dates</a>
        * <a href="#datetime">DateTime</a>
        * <a href="#date">Date</a>
        * <a href="#time">Time</a>
    * <a href="#files">Files</a>
        * <a href="#isfile">IsFile</a>
        * <a href="#isdir">IsDir</a>
        * <a href="#pathexists">PathExists</a>


Voluptuous Drop-In Replacement
==============================

Despite Good is modelled after Voluptuous and is highly compatible,
there still are differences that would definitely break your project.

If you're not ready for such a change -- `good.voluptuous` is the solution:
compatibility layer for switching from [voluptuous 0.8.5](https://github.com/alecthomas/voluptuous)
with 100% compatibility.

This is a drop-in replacement that passes all voluptuous unit-tests and hence should work perfectly.
Here's how to use it

```python
#from voluptuous import *  # no more
from good.voluptuous import *  # replacement

# .. and use it like before
```

Includes all the features and is absolutely compatible, except for the error message texts,
which became much more user-friendly :)

Migration steps:

1. Replace `voluptuous` imports with `good.voluptuous`
2. Run your application tests and see how it behaves
3. Module by module, replace `good.voluptuous` with just `good`, keeping the differences in mind.

Also note the small differences that are still present:

* Settings for `required` and `extra` are not inherited by embedded mappings.

    If your top-level schema defines `required=False`, embedded mappings will still have the default `required=True`!
    And same with `extra`.

* Different error message texts, which are easier to understand :)
* Raises `Invalid` rather than `MultipleInvalid` for rejected extra mapping keys (see [`Extra`](#extra))

Good luck! :)

Schema
======

Validation schema.

A schema is a Python structure where nodes are pattern-matched against the corresponding values.
It leverages the full flexibility of Python, allowing you to match values, types, data structures and much more.

When a schema is created, it's compiled into a callable function which does the validation, hence it does not need
to analyze the schema every time.

Once the Schema is defined, validation can be triggered by calling it:

```python
from good import Schema

schema = Schema({ 'a': str })
# Test
schema({ 'a': 'i am a valid string' })
```

The following rules exist:

1. **Literal**: plain value is validated with direct comparison (equality check):

    ```python
    Schema(1)(1)  #-> 1
    Schema(1)(2)  #-> Invalid: Invalid value: expected 1, got 2
    ```

2. **Type**: type schema produces a strict `type(v) == schema` check on the input value:

    ```python
    Schema(int)(1)    #-> 1
    Schema(int)(True)
    #-> Invalid: Wrong type: expected Integer number, got Boolean
    Schema(int)('1')
    #-> Invalid: Wrong type: expected Integer number, got Binary String
    ```

    For Python2, there is an exception for `basestring`: it won't make strict type checks, but rather `isinstance()`.

    For a relaxed `isinstance()` check, see [`Type`](#type) validator.

3. **Enum**:
    [Python 3.4 Enums](https://docs.python.org/3/library/enum.html),
    or the backported [enum34](https://pypi.python.org/pypi/enum34).

    Tests whether the input value is a valid `Enum` value:

    ```python
    from enum import Enum

    class Colors(Enum):
        RED = 0xFF0000
        GREEN = 0x00FF00
        BLUE = 0x0000FF

    schema = Schema(Colors)

    schema(0xFF0000)  #-> <Colors.RED: 0xFF0000>
    schema(Colors.RED)  #-> <Colors.RED: 0xFF0000>
    schema(123)
    #-> Invalid: Invalid Colors value, expected Colors, got 123
    ```

    Output is always an instance of the provided `Enum` type value.

4. **Callable**: is applied to the value and the result is used as the final value.

   Callables should raise [`Invalid`](#invalid) errors in case of a failure, however some generic error types are
   converted automatically: see [Callables](#callables).

   In addition, validators are allowed to transform a value to the required form.
   For instance, [`Coerce(int)`](#coerce) returns a callable which will convert input values into `int` or fail.

   ```python
   def CoerceInt(v):  # naive Coerce(int) implementation
       return int(v)

   Schema(CoerceInt)(1)    #-> 1
   Schema(CoerceInt)('1')  #-> 1
   Schema(CoerceInt)('a')
   #-> Invalid: invalid literal for int(): expected CoerceInt(), got a
   ```

5. **`Schema`**: a schema may contain sub-schemas:

    ```python
    sub_schema = Schema(int)
    schema = Schema([None, sub_schema])

    schema([None, 1, 2])  #-> [None, 1, 2]
    schema([None, '1'])  #-> Invalid: invalid value
    ```

    Since `Schema` is callable, validation transparently by just calling it :)

Moreover, instances of the following types are converted to callables on the compilation phase:

1. **Iterables** (`list`, `tuple`, `set`, custom iterables):

    Iterables are treated as a set of valid values,
    where each value in the input is compared against each value in the schema.

    In order for the input to be valid, it needs to have the same iterable type, and all of its
    values should have at least one matching value in the schema.

    ```python
    schema = Schema([1, 2, 3])  # List of valid values

    schema([1, 2, 2])  #-> [1, 2, 2]
    schema([1, 2, 4])  #-> Invalid: Invalid value @ [2]: expected List[1|2|3], got 4
    schema((1, 2, 2))  #-> Invalid: Wrong value type: expected List, got Tuple
    ```

    Each value within the iterable is a schema as well, and validation requires that
    each member of the input value matches *any* of the schemas.
    Thus, an iterable is a way to define *OR* validation rule for every member of the iterable:

    ```python
    Schema([ # All values should be
        # .. int ..
        int,
        # .. or a string, casted to int ..
        lambda v: int(v)
    ])([ 1, 2, '3' ])  #-> [ 1, 2, 3 ]
    ```

    This example works like this:

    1. Validate that the input value has the matching type: `list` in this case
    2. For every member of the list, test that there is a matching value in the schema.

        E.g. for value `1` -- `int` matches (immediate `instanceof()` check).
        However, for value `'3'` -- `int` fails, but the callable manages to do it with no errors,
        and transforms the value as well.

        Since lists are ordered, the first schema that didn't fail is used.

2. **Mappings** (`dict`, custom mappings):

    Each key-value pair in the input mapping is validated against the corresponding schema pair:

    ```python
    Schema({
        'name': str,
        'age': lambda v: int(v)
    })({
        'name': 'Alex',
        'age': '18',
    })  #-> {'name': 'Alex', 'age': 18}
    ```

    When validating, *both* keys and values are schemas, which allows to use nested schemas and interesting validation rules.
    For instance, let's use [`In`](#in) validator to match certain keys:

    ```python
    from good import Schema, In

    Schema({
        # These two keys should have integer values
        In({'age', 'height'}): int,
        # All other string keys (other than 'age', 'height') should have string values
        All(str, Neither(In({'age', 'height'}))): str,
    })({
        'age': 18,
        'height': 173,
        'name': 'Alex',
    })
    ```

    This works like this:

    1. Test that the input has a matching type (`dict`)
    2. For each key in the input mapping, matching keys are selected from the schema
    3. Validate input values with the corresponding value in the schema.

    In addition, certain keys can be marked as [`Required`](#required) and [`Optional`](#optional).
    The default behavior is to have all keys required, but this can be changed by providing
    `default_keys=Optional` argument to the Schema.

    Finally, a mapping does not allow any extra keys (keys not defined in the schema). To change this, provide
    `extra_keys=Allow` to the `Schema` constructor.

    Please note that `default_keys` and `extra_keys` settings do not propagate to sub-schemas and are only applied
    to the top-level mapping. If required, wrap sub-schemas with another `Schema()` and feed the settings, or
    use [Markers](#markers) explicitly.

These are just the basic rules, and for sure `Schema` can do much more than that!
Additional logic is implemented through [Markers](#markers) and [Validators](#validation-tools),
which are described in the following chapters.

## Callables

Finally, here are the things to consider when using custom callables for validation:

* Throwing errors.

    If the callable throws [`Invalid`](#invalid) exception, it's used as is with all the rich info it provides.
    Schema is smart enough to fill into most of the arguments (see [`Invalid.enrich`](#invalidenrich)),
    so it's enough to use a custom message, and probably, set a human-friendly `expected` field.

    In addition, specific error types are wrapped into `Invalid` automatically: these are
    `AssertionError`, `TypeError`, `ValueError`.
    Schema tries to do its best, but such messages will probably be cryptic for the user.
    Hence, always raise meaningful errors when creating custom validators.
    Still, this opens the possibility to use Python typecasting with validators like `lambda v: int(v)`,
    since most of them are throwing `TypeError` or `ValueError`.

* Naming.

    If the provided callable does not specify `Invalid.expected` expected value,
    the `__name__` of the callable is be used instead.
    E.g. `def intify(v):pass` becomes `'intify()'` in reported errors.

    If a custom name is desired on the callable -- set the `name` attribute on the callable object.
    This works best with classes, however a function can accept `name` attribute as well.

    For convenience, [`@message`](#message) and [`@name`](#name) decorators can be used on callables
    to specify the name and override the error message used when the validator fails.

* Signals.

    A callable may decide that the value is soooo invalid that it should be dropped from the sanitized output.
    In this case, the callable should raise `good.schema.signals.RemoveValue`.

    This is used by the `Remove()` marker, but can be leveraged by other callables as well.

## Priorities

Every schema type has a priority ([source](good/schema/util.py)),
which define the sequence for matching keys in a mapping schema:

1. Literals have highest priority
2. Types has lower priorities than literals, hence schemas can define specific rules for individual keys,
    and then declare general rules by type-matching:

    ```python
    Schema({
        'name': str,  # Specific rule with a literal
        str: int,     # General rule with a type
    })
    ```
3. Callables, iterables, mappings -- have lower priorities.

In addition, [Markers](#markers) have individual priorities,
which can be higher that literals ([`Remove()`](#remove) marker) or lower than callables ([`Extra`](#extra) marker).

Creating a Schema
-----------------
```python
Schema(schema, default_keys=None, extra_keys=None)
```

Creates a compiled `Schema` object from the given schema definition.

Under the hood, it uses `SchemaCompiler`: see the [source](good/schema/compiler.py) if interested.

Arguments:

* `schema`: Schema definition
* `default_keys`: Default mapping keys behavior:
    a [`Marker`](#markers) class used as a default on mapping keys which are not Marker()ed with anything.

    Defaults to `markers.Required`.
* `extra_keys`: Default extra keys behavior: sub-schema, or a [`Marker`](#markers) class.

    Defaults to `markers.Reject`



Throws:

* `SchemaError`: Schema compilation error


Validating
----------

```python
Schema.__call__(value)
```

Having a [`Schema`](#schema), user input can be validated by calling the Schema on the input value.

When called, the Schema will return sanitized value, or raise exceptions.

Arguments:

* `value`: Input value to validate

Returns: `None` Sanitized value

Throws:

* `good.MultipleInvalid`: Validation error on multiple values. See [`MultipleInvalid`](#multipleinvalid).
* `good.Invalid`: Validation error on a single value. See [`Invalid`](#invalid).


Errors
======

Source: [good/schema/errors.py](good/schema/errors.py)

When [validating user input](#validating), [`Schema`](#schema) collects all errors and throws these
after the whole input value is validated. This makes sure that you can report *all* errors at once.

With simple schemas, like `Schema(int)`, only a single error is available: e.g. wrong value type.
In this case, [`Invalid`](#invalid) error is raised.

However, with complex schemas with embedded structures and such, multiple errors can occur:
then [`MultipleInvalid`] is reported.

All errors are available right at the top-level:

```python
from good import Invalid, MultipleInvalid
```

## Invalid
```python
Invalid(message, expected=None, provided=None, path=None,
        validator=None, **info)
```

Validation error for a single value.

This exception is guaranteed to contain text values which are meaningful for the user.

Arguments:

* `message`: Validation error message.
* `expected`: Expected value: info about the value the validator was expecting.

    If validator does not specify it -- the name of the validator is used.
* `provided`: Provided value: info about the value that was actually supplied by the user

    If validator does not specify it -- the input value is typecasted to string and stored here.
* `path`: Path to the error value.

    E.g. if an invalid value was encountered at ['a'].b[1], then path=['a', 'b', 1].
* `validator`: The validator that has failed: a schema item
* `**info`: Custom values that might be provided by the validator. No built-in validator uses this.





### `Invalid.enrich()`
```python
Invalid.enrich(expected=None, provided=None, path=None,
               validator=None)
```

Enrich this error with additional information.

This works with both Invalid and MultipleInvalid (thanks to `Invalid` being iterable):
in the latter case, the defaults are applied to all collected errors.

The specified arguments are only set on `Invalid` errors which do not have any value on the property.

One exclusion is `path`: if provided, it is prepended to `Invalid.path`.
This feature is especially useful when validating the whole input with multiple different schemas:

```python
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
```

This is used when validating a value within a container.

Arguments:

* `expected`: Invalid.expected default
* `provided`: Invalid.provided default
* `path`: Prefix to prepend to Invalid.path
* `validator`: Invalid.validator default

Returns: `Invalid|MultipleInvalid` 



## MultipleInvalid
```python
MultipleInvalid(errors)
```

Validation errors for multiple values.

This error is raised when the [`Schema`](#schema) has reported multiple errors, e.g. for several dictionary keys.

`MultipleInvalid` has the same attributes as [`Invalid`](#invalid),
but the values are taken from the first error in the list.

In addition, it has the `errors` attribute, which is a list of [`Invalid`](#invalid) errors collected by the schema.
The list is guaranteed to be plain: e.g. there will be no underlying hierarchy of `MultipleInvalid`.

Note that both `Invalid` and `MultipleInvalid` are iterable, which allows to process them in singularity:

```python
try:
    schema(input_value)
except Invalid as ee:
    reported_problems = {}
    for e in ee:  # Iterate over `Invalid`
        path_str = u'.'.join(e.path)  # 'a.b.c.d', JavaScript-friendly :)
        reported_problems[path_str] = e.message
    #.. send reported_problems to the user
```

In this example, we create a dictionary of paths (as strings) mapped to error strings for the user.

Arguments:

* `errors`: The reported errors.

    If it contains `MultipleInvalid` errors -- the list is recursively flattened
    so all of them are guaranteed to be instances of [`Invalid`](#invalid).












Markers
=======
A *Marker* is a proxy class which wraps some schema.

Immediately, the example is:

```python
from good import Schema, Required

Schema({
    'name': str,  # required key
    Optional('age'): int,  # optional key
}, default_keys=Required)
```

This way, keys marked with `Required()` will report errors if no value if provided.

Typically, a marker "decorates" a mapping key, but some of them can be "standalone":

```python
from good import Schema, Extra
Schema({
    'name': str,
    Extra: int  # allow any keys, provided their values are integer
})
```

Each marker can have it's own unique behavior since nothing is hardcoded into the core [`Schema`](#schema).
Keep on reading to learn how markers perform.


## `Required`
```python
Required(key)
```

`Required(key)` is used to decorate mapping keys and hence specify that these keys must always be present in
the input mapping.

When compiled, [`Schema`](#schema) uses `default_keys` as the default marker:

```python
from good import Schema, Required

schema = Schema({
    'name': str,
    'age': int
}, default_keys=Required)  # wrap with Required() by default

schema({'name': 'Mark'})
#-> Invalid: Required key not provided @ ['age']: expected age, got -none-
```

Remember that mapping keys are schemas as well, and `Require` will expect to always have a match:

```python
schema = Schema({
    Required(str): int,
})

schema({})  # no `str` keys provided
#-> Invalid: Required key not provided: expected String, got -none-
```

In addition, the `Required` marker has special behavior with [`Default`](#default) that allows to set the key
to a default value if the key was not provided. More details in the docs for [`Default`](#default).

Arguments:







## `Optional`
```python
Optional(key)
```

`Optional(key)` is controversial to [`Required(key)`](#required): specified that the mapping key is not required.

This only has meaning when a [`Schema`](#schema) has `default_keys=Required`:
then, it decorates all keys with `Required()`, unless a key is already decorated with some Marker.
`Optional()` steps in: those keys are already decorated and hence are not wrapped with `Required()`.

So, it's only used to prevent `Schema` from putting `Required()` on a key.
In all other senses, it has absolutely no special behavior.

As a result, optional key can be missing, but if it was provided -- its value must match the value schema.

Example: use as `default_keys`:

```python
schema = Schema({
    'name': str,
    'age': int
}, default_keys=Optional)  # Make all keys optional by default

schema({})  #-> {} -- okay
schema({'name': None})
#->  Invalid: Wrong type @ ['name']: expected String, got None
```

Example: use to mark specific keys are not required:

```python
schema = Schema({
    'name': str,
    Optional(str): int  # key is optional
})

schema({'name': 'Mark'})  # valid
schema({'name': 'Mark', 'age': 10})  # valid
schema({'name': 'Mark', 'age': 'X'})
#-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String
```

Arguments:







## `Remove`
```python
Remove(key)
```

`Remove(key)` marker is used to declare that the key, if encountered,
should be removed, without validating the value.

`Remove` has highest priority, so it operates before everything else in the schema.

Example:

```python
schema = Schema({
    Remove('name'): str, # `str` does not mean anything since the key is removed anyway
    'age': int
})

schema({'name': 111, 'age': 18})  #-> {'age': 18}
```

However, it's more natural to use `Remove()` on values.
Remember that in this case `'name'` will become [`Required()`](#required),
if not decorated with [`Optional()`](#optional):

```python
schema = Schema({
    Optional('name'): Remove
})

schema({'name': 111, 'age': 18})  #-> {'age': 18}
```

**Bonus**: `Remove()` can be used in iterables as well:

```python
schema = Schema([str, Remove(int)])
schema(['a', 'b', 1, 2])  #-> ['a', 'b']
```

Arguments:







## `Reject`
```python
Reject(key)
```

`Reject(key)` marker is used to report [`Invalid`](#invalid) errors every time is matches something in the input.

It has lower priority than most of other schemas, so rejection will only happen
if no other schemas has matched this value.

Example:

```python
schema = Schema({
    Reject('name'): None,  # Reject by key
    Optional('age'): Msg(Reject, u"Field is not supported anymore"), # alternative form
})

schema({'name': 111})
#-> Invalid: Field is not supported anymore @ ['name']: expected -none-, got name
```

Arguments:







## `Allow`
```python
Allow(key)
```

`Allow(key)` is a no-op marker that never complains on anything.

Designed to be used with [`Extra`](#extra).

Arguments:







## `Extra`
```python
Extra(key)
```

`Extra` is a catch-all marker to define the behavior for mapping keys not defined in the schema.

It has the lowest priority, and delegates its function to its value, which can be a schema, or another marker.

Given without argument, it's compiled with an identity function `lambda x:x` which is a catch-all:
it matches any value. Together with lowest priority, `Extra` will only catch values which did not match anything else.

Every mapping has an `Extra` implicitly, and `extra_keys` argument controls the default behavior.

Example with `Extra: <schema>`:

```python
schema = Schema({
    'name': str,
    Extra: int  # this will allow extra keys provided they're int
})

schema({'name': 'Alex', 'age': 18'})  #-> ok
schema({'name': 'Alex', 'age': 'X'})
#-> Invalid: Wrong type @ ['age']: expected Integer number, got Binary String
```

Example with `Extra: Reject`: reject all extra values:

```python
schema = Schema({
    'name': str,
    Extra: Reject
})

schema({'name': 'Alex', 'age': 'X'})
#-> Invalid: Extra keys not allowed @ ['age']: expected -none-, got age
```

Example with `Extra: Remove`: silently discard all extra values:

```python
schema = Schema({'name': str}, extra_keys=Remove)
schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex'}
```

Example with `Extra: Allow`: allow any extra values:

```python
schema = Schema({'name': str}, extra_keys=Allow)
schema({'name': 'Alex', 'age': 'X'})  #-> {'name': 'Alex', 'age': 'X'}
```

Arguments:







## `Entire`
```python
Entire(key)
```

`Entire` is a convenience marker that validates the entire mapping using validators provided as a value.

It has absolutely lowest priority, lower than `Extra`, hence it never matches any keys, but is still executed to
validate the mapping itself.

This opens the possibilities to define rules on multiple fields.
This feature is leveraged by the [`Inclusive`](#inclusive) and [`Exclusive`](#exclusive) group validators.

For example, let's require the mapping to have no more than 3 keys:

```python
from good import Schema, Entire

def maxkeys(n):
    # Return a validator function
    def validator(d):
        # `d` is the dictionary.
        # Validate it
        assert len(d) <= 3, 'Dict size should be <= 3'
        # Return the value since all callable schemas should do that
        return d
    return validator

schema = Schema({
    str: int,
    Entire: maxkeys(3)
})
```

In this example, `Entire` is executed for every input dictionary, and magically calls the schema it's mapped to.
The `maxkeys(n)` schema is a validator that complains on the dictionary size if it's too huge.
`Schema` catches the `AssertionError` thrown by it and converts it to [`Invalid`](#invalid).

Note that the schema this marker is mapped to can't replace the mapping object, but it can mutate the given mapping.

Arguments:








Validation Tools
================

All validators listed here inherit from `ValidatorBase` which defines the standard interface.
Currently it makes no difference whether it's just a callable, a class, or a subclass of `ValidatorBase`,
but in the future it may gain special features.

Helpers
-------
Collection of miscellaneous helpers to alter the validation process.


### `Object`
```python
Object(schema, cls=None)
```

Specify that the provided mapping should validate an object.

This uses the same mapping validation rules, but works with attributes instead:

```python
from good import Schema, Object

intify = lambda v: int(v)  # Naive Coerce(int) implementation

# Define a class to play with
class Person:
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
```

Internally, it validates the object's `__dict__`: hence, class attributes are excluded from validation.
Validation is performed with the help of a wrapper class which proxies object attributes as mapping keys,
and then Schema validates it as a mapping.

This inherits the default required/extra keys behavior of the Schema.
To override, use [`Optional()`](#optional) and [`Extra`](#extra) markers.

Arguments:

* `schema`: Object schema, given as a mapping
* `cls`: Require instances of a specific class. If `None`, allows all classes.





### `Msg`
```python
Msg(schema, message)
```

Override the error message reported by the wrapped schema in case of validation errors.

On validation, if the schema throws [`Invalid`](#invalid) -- the message is overridden with `msg`.

Some other error types are converted to `Invalid`: see notes on [Schema Callables](#callables).

```python
from good import Schema, Msg

intify = lambda v: int(v)  # Naive Coerce(int) implementation
intify.name = u'Number'

schema = Schema(Msg(intify, u'Need a number'))
schema(1)  #-> 1
schema('a')
#-> Invalid: Need a number: expected Number, got a
```

Arguments:

* `schema`: The wrapped schema to modify the error for
* `message`: Error message to use instead of the one that's reported by the underlying schema





### `Test`
```python
Test(fun)
```

Test the value with the provided function, expecting that it won't throw errors.

If no errors were thrown -- the value is valid and *the original input value is used*.
If any error was thrown -- the value is considered invalid.

This is especially useful to discard tranformations made by the wrapped validator:

```python
from good import Schema, Coerce

schema = Schema(Coerce(int))

schema(123)  #-> 123
schema('123')  #-> '123' -- still string
schema('abc')
#-> Invalid: Invalid value, expected *Integer number, got abc
```

Arguments:

* `fun`: Callable to test the value with, or a validator function.

    Note that this won't work with mutable input values since they're modified in-place!





### `message`
```python
message(message, name=None)
```

Convenience decorator that applies [`Msg()`](#msg) to a callable.

```python
from good import Schema, message

@message(u'Need a number')
def intify(v):
    return int(v)
```

Arguments:

* `message`: Error message to use instead
* `name`: Override schema name as well. See [`name`](#name).

Returns: `callable` decorator



### `name`
```python
name(name, validator=None)
```

Set a name on a validator callable.

Useful for user-friendly reporting when using lambdas to populate the [`Invalid.expected`](#invalid) field:

```python
from good import Schema, name

Schema(lambda x: int(x))('a')
#-> Invalid: invalid literal for int(): expected <lambda>(), got
Schema(name('int()', lambda x: int(x))('a')
#-> Invalid: invalid literal for int(): expected int(), got a
```

Note that it is only useful with lambdas, since function name is used if available:
see notes on [Schema Callables](#callables).

Arguments:

* `name`: Name to assign on the validator callable
* `validator`: Validator callable. If not provided -- a decorator is returned instead:

    ```python
    from good import name

    @name(u'int()')
    def int(v):
        return int(v)
    ```

Returns: `callable` The same validator callable



### `truth`
```python
truth(message, expected=None)
```

Convenience decorator that applies [`Check`](#check) to a callable.

```python
from good import truth

@truth(u'Must be an existing directory')
def isDir(v):
    return os.path.isdir(v)
```

Arguments:

* `message`: Validation error message
* `expected`: Expected value string representation, or `None` to get it from the wrapped callable

Returns: `callable` decorator




Predicates
----------



### `Maybe`
```python
Maybe(schema, none=None)
```

Validate the the value either matches the given schema or is None.

This supports *nullable* values and gives them a good representation.

```python
from good import Schema, Maybe, Email

schema = Schema(Maybe(Email))

schema(None)  #-> None
schema('user@example.com')  #-> 'user@example.com'
scheam('blahblah')
#-> Invalid: Wrong E-Mail: expected E-Mail?, got blahblah
```

Note that it also have the [`Default`-like behavior](#default)
that initializes the missing [`Required()`](#required) keys:

```python
schema = Schema({
    'email': Maybe(Email)
})

schema({})  #-> {'email': None}
```

Arguments:

* `schema`: Schema for a provided value
* `none`: Empty value literal





### `Any`
```python
Any(*schemas)
```

Try the provided schemas in order and use the first one that succeeds.

This is the *OR* condition predicate: any of the schemas should match.
[`Invalid`](#invalid) error is reported if neither of the schemas has matched.

```python
from good import Schema, Any

schema = Schema(Any(
    # allowed string constants
    'true', 'false',
    # otherwise coerce as a bool
    lambda v: 'true' if v else 'false'
))
schema('true')  #-> 'true'
schema(0)  #-> 'false'
```

Arguments:

* `*schemas`: List of schemas to try.





### `All`
```python
All(*schemas)
```

Value must pass all validators wrapped with `All()` predicate.

This is the *AND* condition predicate: all of the schemas should match in order,
which is in fact a composition of validators: `All(f,g)(value) = g(f(value))`.

```python
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
```

Arguments:

* `*schemas`: List of schemas to apply.





### `Neither`
```python
Neither(*schemas)
```

Value must not match any of the schemas.

This is the *NOT* condition predicate: a value is considered valid if each schema has raised an error.

```python
from good import Schema, All, Neither

schema = Schema(All(
    # Integer
    int,
    # But not zero
    Neither(0)
))

schema(1)  #-> 1
schema(0)
#-> Invalid: Value not allowed: expected Not(0), got 0
```

Arguments:

* `*schemas`: List of schemas to check against.





### `Inclusive`
```python
Inclusive(*keys)
```

`Inclusive` validates the defined inclusive group of mapping keys:
if any of them was provided -- then all of them become required.

This exists to support "sub-structures" within the mapping which only make sense if specified together.
Since this validator works on the entire mapping, the best way is to use it together with the [`Entire`](#entire)
marker:

```python
from good import Schema, Entire, Inclusive

schema = Schema({
    # Fields for all files
    'name': str,
    # Fields for images only
    Optional('width'): int,
    Optional('height'): int,
    # Now put a validator on the entire mapping
    Entire: Inclusive('width', 'height')
})

schema({'name': 'monica.jpg'})  #-> ok
schema({'name': 'monica.jpg', 'width': 800, 'height': 600})  #-> ok
schema({'name': 'monica.jpg', 'width': 800})
#-> Invalid: Required key not provided: expected height, got -none-
```

Note that `Inclusive` only supports literals.

Arguments:

* `*keys`: List of mutually inclusive keys (literals).





### `Exclusive`
```python
Exclusive(*keys)
```

`Exclusive` validates the defined exclusive group of mapping keys:
if any of them was provided -- then none of the remaining keys can be used.

This supports "sub-structures" with choice: if the user chooses a field from one of them --
then he cannot use others.
It works on the entire mapping and hence best to use with the [`Entire`](#entire) marker.

By default, `Exclusive` requires the user to choose one of the options,
but this can be overridden with [`Optional`](#optional) marker class given as an argument:

```python
from good import Exclusive, Required, Optional

# Requires either of them
Exclusive('login', 'password')
Exclusive(Required, 'login', 'password')  # the default

# Requires either of them, or none
Exclusive(Optional, 'login', 'password')
```

Let's demonstrate with the API that supports multiple types of authentication,
but requires the user to choose just one:

```python
from good import Schema, Entire, Exclusive

schema = Schema({
    # Authentication types: login+password | email+password
    Optional('login'): str,
    Optional('email'): str,
    'password': str,
    # Now put a validator on the entire mapping
    # that forces the user to choose
    Entire: Msg(  # also override the message
        Exclusive('login', 'email'),
        u'Choose one'
    )
})

schema({'login': 'kolypto', 'password': 'qwerty'})  #-> ok
schema({'email': 'kolypto', 'password': 'qwerty'})  #-> ok
schema({'login': 'a', 'email': 'b', 'password': 'c'})
#-> MultipleInvalid:
#->     Invalid: Choose one @ [login]: expected login|email, got login
#->     Invalid: Choose one @ [email]: expected login|email, got email
```

Note that `Exclusive` only supports literals.

Arguments:

* `*keys`: List of mutually exclusive keys (literals).

    Can contain [`Required`](#required) or [`Optional`](#optional) marker classes,
    which defines the behavior when no keys are provided. Default is `Required`.






Types
-----



### `Type`
```python
Type(*types)
```

Check if the value has the specific type with `isinstance()` check.

In contrast to [Schema types](#schema) which performs a strict check, this check is relaxed and accepts subtypes
as well.

```python
from good import Schema, Type

schema = Schema(Type(int))
schema(1)  #-> 1
schema(True)  #-> True
```

Arguments:

* `*types`: The type to check instances against.

    If multiple types are provided, then any of them is acceptable.





### `Coerce`
```python
Coerce(constructor)
```

Coerce a value to a type with the provided callable.

`Coerce` applies the *constructor* to the input value and returns a value cast to the provided type.

If *constructor* fails with `TypeError` or `ValueError`, the value is considered invalid and `Coerce` complains
on that with a custom message.

However, if *constructor* raises [`Invalid`](#invalid) -- the error object is used as it.

```python
from good import Schema, Coerce

schema = Schema(Coerce(int))
schema(u'1')  #-> 1
schema(u'a')
#-> Invalid: Invalid value: expected *Integer number, got a
```

Arguments:

* `constructor`: Callable that typecasts the input value






Values
------



### `In`
```python
In(container)
```

Validate that a value is in a collection.

This is a plain simple `value in container` check, where `container` is a collection of literals.

In contrast to [`Any`](#any), it does not compile its arguments into schemas,
and hence achieves better performance.

```python
from good import Schema, In

schema = Schema(In({1, 2, 3}))

schema(1)  #-> 1
schema(99)
#-> Invalid: Unsupported value: expected In(1,2,3), got 99
```

The same example will work with [`Any`](#any), but slower :-)

Arguments:

* `container`: Collection of allowed values.

    In addition to naive tuple/list/set/dict, this can be any object that supports `in` operation.





### `Length`
```python
Length(min=None, max=None)
```

Validate that the provided collection has length in a certain range.

```python
from good import Schema, Length

schema = Schema(All(
    # Ensure it's a list (and not any other iterable type)
    list,
    # Validate length
    Length(max=3),
))
```

Since mappings also have length, they can be validated as well:

```python
schema = Schema({
    # Strings mapped to integers
    str: int,
    # Size = 1..3
    # Empty dicts are not allowed since `str` is implicitly `Required(str)`
    Entire: Length(max=3)
})

schema([1])  #-> ok
schema([1,2,3,4])
#-> Invalid: Too long (3 is the most): expected Length(..3), got 4
```

Arguments:

* `min`: Minimal allowed length, or `None` to impose no limits.
* `max`: Maximal allowed length, or `None` to impose no limits.





### `Default`
```python
Default(default)
```

Initialize a value to a default if it's not provided.

"Not provided" means `None`, so basically it replaces `None`s with the default:

```python
from good import Schema, Any, Default

schema = Schema(Any(
    # Accept ints
    int,
    # Replace `None` with 0
    Default(0)
))

schema(1)  #-> 1
schema(None)  #-> 0
```

It raises [`Invalid`](#invalid) on all values except for `None` and `default`:

```python
schema = Schema(Default(42))

schema(42)  #-> 42
schema(None)  #-> 42
schema(1)
#-> Invalid: Invalid value
```

In addition, `Default` has special behavior with `Required` marker which is built into it:
if a required key was not provided -- it's created with the default value:

```python
from good import Schema, Default

schema = Schema({
    # remember that keys are implicitly required
    'name': str,
    'age': Any(int, Default(0))
})

schema({'name': 'Alex'})  #-> {'name': 'Alex', 'age': 0}
```

Arguments:

* `default`: The default value to use





### `Fallback`
```python
Fallback(default)
```

Always returns the default value.

Works like [`Default`](#default), but does not fail on any values.

Typical usage is to terminate [`Any`](#any) chain in case nothing worked:

```python
from good import Schema, Any, Fallback

schema = Schema(Any(
    int,
    # All non-integer numbers are replaced with `None`
    Fallback(None)
))
```

Like [`Default`](#default), it also works with mappings.

Internally, `Default` and `Fallback` work by feeding the schema with a special [`Undefined`](good/schema/util.py) value:
if the schema manages to return some value without errors -- then it has the named "default behavior",
and this validator just leverages the feature.

A "fallback value" may be provided manually, and will work absolutely the same
(since value schema manages to succeed even though `Undefined` was given):

```python
schema = Schema({
    'name': str,
    'age': Any(int, lambda v: 42)
})
```

Arguments:

* `default`: The value that's always returned





### `Map`
```python
Map(enum, mode=1)
```

Convert Enumerations that map names to values.

Supports three kinds of enumerations:

1. Mapping.

    Provided a mapping from names to values,
    converts the input to values by mapping key:

    ```python
    from good import Schema, Map
    schema = Schema(Map({
        'RED': 0xFF0000,
        'GREEN': 0x00FF00,
        'BLUE': 0x0000FF
    }))

    schema('RED')  #-> 0xFF0000
    schema('BLACK')
    #-> Invalid: Unsupported value: expected Constant, provided BLACK
    ```

2. Class.

    Provided a class with attributes (names) initialized with values,
    converts the input to values matching by attribute name:

    ```python
    class Colors:
        RED = 0xFF0000
        GREEN = 0x00FF00
        BLUE = 0x0000FF

    schema = Schema(Map(Colors))

    schema('RED')  #-> 0xFF0000
    schema('BLACK')
    #-> Invalid: Unsupported value: expected Colors, provided BLACK
    ```

    Note that all attributes of the class are used, except for protected (`_name`) and callables.

3. Enum.

    Supports [Python 3.4 Enums](https://docs.python.org/3/library/enum.html)
    and the backported [enum34](https://pypi.python.org/pypi/enum34).

    Provided an enumeration, converts the input to values by name.
    In addition, enumeration value can pass through safely:

    ```python
    from enum import Enum

    class Colors(Enum):
        RED = 0xFF0000
        GREEN = 0x00FF00
        BLUE = 0x0000FF

    schema = Schema(Map(Colors))
    schema('RED')  #-> <Colors.RED: 0xFF0000>
    schema('BLACK')
    #-> Invalid: Unsupported value: expected Colors, provided BLACK
    ```

    Note that in `mode=Map.VAL` it works precisely like `Schema(Enum)`.

In addition to the "straignt" mode (lookup by key), it supports reverse matching:

* When `mode=Map.KEY`, does only forward matching (by key) -- the default
* When `mode=Map.VAL`, does only reverse matching (by value)
* When `mode=Map.BOTH`, does bidirectional matching (by key first, then by value)

Another neat feature is that `Map` supports `in` containment checks,
which works great together with [`In`](#in): `In(Map(enum-value))` will test if a value is convertible, but won't
actually do the convertion.

```python
from good import Schema, Map, In

schema = Schema(In(Map(Colors)))

schema('RED') #-> 'RED'
schema('BLACK')
#-> Invalid: Unsupported value, expected Colors, got BLACK
```

Arguments:

* `enum`: Enumeration: dict, object, of Enum
* `mode`: Matching mode: one of Map.KEY, Map.VAL, Map.BOTH






Boolean
-------



### `Check`
```python
Check(bvalidator, message, expected)
```

Use the provided boolean function as a validator and raise errors when it's `False`.

```python
import os.path
from good import Schema, Check

schema = Schema(
    Check(os.path.isdir, u'Must be an existing directory'))
schema('/')  #-> '/'
schema('/404')
#-> Invalid: Must be an existing directory: expected isDir(), got /404
```

Arguments:

* `bvalidator`: Boolean validator function
* `message`: Error message to report when `False`
* `expected`: Expected value string representation, or `None` to get it from the wrapped callable





### `Truthy`
```python
Truthy()
```

Assert that the value is truthy, in the Python sense.

This fails on all "falsy" values: `False`, `0`, empty collections, etc.

```python
from good import Schema, Truthy

schema = Schema(Truthy())

schema(1)  #-> 1
schema([1,2,3])  #-> [1,2,3]
schema(None)
#-> Invalid: Empty value: expected truthy(), got None
```






### `Falsy`
```python
Falsy()
```

Assert that the value is falsy, in the Python sense.

Supplementary to [`Truthy`](#truthy).






### `Boolean`
```python
Boolean()
```

Convert human-readable boolean values to a `bool`.

The following values are supported:

* `None`: `False`
* `bool`: direct
* `int`: `0` = `False`, everything else is `True`
* `str`: Textual boolean values, compatible with [YAML 1.1 boolean literals](http://yaml.org/type/bool.html), namely:

        y|Y|yes|Yes|YES|n|N|no|No|NO|
        true|True|TRUE|false|False|FALSE|
        on|On|ON|off|Off|OFF

    [`Invalid`](#invalid) is thrown if an unknown string literal is provided.

Example:

```python
from good import Schema, Boolean

schema = Schema(Boolean())

schema(None)  #-> False
schema(0)  #-> False
schema(1)  #-> True
schema(True)  #-> True
schema(u'yes')  #-> True
```







Numbers
-------



### `Range`
```python
Range(min=None, max=None)
```

Validate that the value is within the defined range, inclusive.
Raise [`Invalid`](#invalid) error if not.

```python
from good import Schema, Range

schema = Schema(Range(1, 10))

schema(1)  #-> 1
schema(10)  #-> 10
schema(15)
#-> Invalid: Value must be at most 10: expected Range(1..10), got 15
```

If the value cannot be compared to a number -- raises [`Invalid`](#invalid).
Note that in Python2 almost everything can be compared to a number, including strings, dicts and lists!

Arguments:

* `min`: Minimal allowed value, or `None` to impose no limits.
* `max`: Maximal allowed value, or `None` to impose no limits.





### `Clamp`
```python
Clamp(min=None, max=None)
```

Clamp a value to the defined range, inclusive.

```python
from good import Schema, Clamp

schema = Schema(Clamp(1, 10))

schema(-1)  #-> 1
schema(1)  #-> 1
schema(10)  #-> 10
schema(15)  #-> 10
```

If the value cannot be compared to a number -- raises [`Invalid`](#invalid).
Note that in Python2 almost everything can be compared to a number, including strings, dicts and lists!

Arguments:

* `min`: Minimal allowed value, or `None` to impose no limits.
* `max`: Maximal allowed value, or `None` to impose no limits.






Strings
-------



### `Lower`
```python
Lower()
```

Casts the provided string to lowercase, fails is the input value is not a string.

Supports both binary and unicode strings.

```python
from good import Schema, Lower

schema = Schema(Lower())

schema(u'ABC')  #-> u'abc'
schema(123)
#-> Invalid: Not a string: expected String, provided Integer number
```






### `Upper`
```python
Upper()
```

Casts the input string to UPPERCASE.






### `Capitalize`
```python
Capitalize()
```

Capitalizes the input string.






### `Title`
```python
Title()
```

Casts The Input String To Title Case






### `Match`
```python
Match(pattern, message=None, expected=None)
```

Validate the input string against a regular expression.

```python
from good import Schema, Match

schema = Schema(All(
    unicode,
    Match(r'^0x[A-F0-9]+$', 'hex number')
))

schema('0xDEADBEEF')  #-> '0xDEADBEEF'
schema('0x')
#-> Invalid: Wrong format: expected hex number, got 0xDEADBEEF
```

Arguments:

* `pattern`: RegExp pattern to match with: a string, or a compiled pattern
* `message`: Error message override
* `expected`: Textual representation of what's expected from the user





### `Replace`
```python
Replace(pattern, repl, message=None, expected=None)
```

RegExp substitution.

```python
from good import Schema, Replace

schema = Schema(Replace(
    # Grab domain name
    r'^https?://([^/]+)/.*'
    # Replace
    r'',
    # Tell the user that we're expecting a URL
    u'URL'
))

schema('http://example.com/a/b/c')  #-> 'example.com'
schema('user@example.com')
#-> Invalid: Wrong format: expected URL, got user@example.com
```

Arguments:

* `pattern`: RegExp pattern to match with: a string, or a compiled pattern
* `repl`: Replacement pattern.

    Backreferences are supported, just like in the [`re`](https://docs.python.org/2/library/re.html) module.
* `message`: Error message override
* `expected`: Textual representation of what's expected from the user





### `Url`
```python
Url(protocols=('http', 'https'))
```

Validate a URL, make sure it's in the absolute format, including the protocol.

```python
from good import Schema, Url

schema = Schema(Url('https'))

schema('example.com')  #-> 'https://example.com'
schema('http://example.com')  #-> 'http://example.com'
```

Arguments:

* `protocols`: List of allowed protocols.

    If no protocol is provided by the user -- the first protocol is used by default.





### `Email`
```python
Email()
```

Validate that a value is an e-mail address.

This simply tests for the presence of the '@' sign, surrounded by some characters.

```python
from good import Email

schema = Schema(Email())

schema('user@example.com')  #-> 'user@example.com'
schema('user@localhost')  #-> 'user@localhost'
schema('user')
#-> Invalid: Invalid e-mail: expected E-Mail, got user
```







Dates
-----



### `DateTime`
```python
DateTime(formats, localize=None, astz=None)
```

Validate that the input is a Python `datetime`.

Supports the following input values:

1. `datetime`: passthrough
2. string: parses the string with any of the specified formats
    (see [strptime()](https://docs.python.org/3.4/library/datetime.html#strftime-and-strptime-behavior))

```python
from datetime import datetime
from good import Schema, DateTime

schema = Schema(DateTime('%Y-%m-%d %H:%M:%S'))

schema('2014-09-06 21:22:23')  #-> datetime.datetime(2014, 9, 6, 21, 22, 23)
schema(datetime.now())  #-> datetime.datetime(2014, 9, 6, 21, 22, 23)
schema('2014')
#-> Invalid: Invalid datetime format, expected DateTime, got 2014.
```

Notes on timezones:

* If the format does not support timezones, it always returns *naive* `datetime` objects (without `tzinfo`).
* If timezones are supported by the format (with `%z`/`%Z`),
   it returns an *aware* `datetime` objects (with `tzinfo`).
* Since Python2 does not always support `%z` -- `DateTime` does this manually.
  Due to the limited nature of this workaround, the support for `%z` only works if it's at the end of the string!

As a result, '00:00:00' is parsed into a *naive* datetime, and '00:00:00 +0200' results in an *aware* datetime.

If your application wants different rules, use `localize` and `astz`:

* `localize` argument is the default timezone to set on *naive* datetimes,
    or a callable which is applied to the input and should return adjusted `datetime`.
* `astz` argument is the timezone to adjust the *aware* datetime to, or a callable.

Then the generic recipe is:

* Set `localize` to the timezone (or a callable) that you expect the user to input the datetime in
* Set `astz` to the timezone you wish to have in the result.

This works best with the excellent [pytz](http://pytz.sourceforge.net/) library:

```python
import pytz
from good import Schema, DateTime

# Formats: with and without timezone
formats = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S%z'
]

# The used timezones
UTC = pytz.timezone('UTC')
Oslo = pytz.timezone('Europe/Oslo')

### Example: Use Europe/Oslo by default
schema = Schema(DateTime(
    formats,
    localize=Oslo
))

schema('2014-01-01 00:00:00')
#-> datetime.datetime(2014, 1, 1, 0, 0, tzinfo='Europe/Oslo')
schema('2014-01-01 00:00:00-0100')
#-> datetime.datetime(2014, 1, 1, 0, 0, tzinfo=-0100)

### Example: Use Europe/Oslo by default and convert to an aware UTC
schema = Schema(DateTime(
    formats,
    localize=Oslo,
    astz=UTC
))

schema('2014-01-01 00:00:00')
#-> datetime.datetime(2013, 12, 31, 23, 17, tzinfo=<UTC>)
schema('2014-01-01 00:00:00-0100')
#-> datetime.datetime(2014, 1, 1, 1, 0, tzinfo=<UTC>)

### Example: Use Europe/Oslo by default, convert to a naive UTC
# This is the recommended way
schema = Schema(DateTime(
    formats,
    localize=Oslo,
    astz=lambda v: v.astimezone(UTC).replace(tzinfo=None)
))

schema('2014-01-01 00:00:00')
#-> datetime.datetime(2013, 12, 31, 23, 17)
schema('2014-01-01 00:00:00-0100')
#-> datetime.datetime(2014, 1, 1, 1, 0)
```

Note: to save some pain, make sure to *always* work with naive `datetimes` adjusted to UTC!
Armin Ronacher [explains it here](http://lucumr.pocoo.org/2011/7/15/eppur-si-muove/).

Summarizing all the above, the validation procedure is a 3-step process:

1. Parse (only with strings)
2. If is *naive* -- apply `localize` and make it *aware* (if `localize` is specified)
3. If is *aware* -- apply `astz` to convert it (if `astz` is specified)

Arguments:

* `formats`: Supported format string, or an iterable of formats to try them all.
* `localize`: Adjust *naive* `datetimes` to a timezone, making it *aware*.

    A `tzinfo` timezone object,
    or a callable which is applied to a *naive* datetime and should return an adjusted value.

    Only called for *naive* `datetime`s.
* `astz`: Adjust *aware* `datetimes` to another timezone.

    A `tzinfo` timezone object,
    or a callable which is applied to an *aware* datetime and should return an adjusted value.

    Only called for *aware* `datetime`s, including those created by `localize`





### `Date`
```python
Date(formats, localize=None, astz=None)
```

Validate that the input is a Python `date`.

Supports the following input values:

1. `date`: passthrough
2. `datetime`: takes the `.date()` part
2. string: parses (see [`DateTime`](#datetime))

```python
from datetime import date
from good import Schema, Date

schema = Schema(Date('%Y-%m-%d'))

schema('2014-09-06')  #-> datetime.date(2014, 9, 6)
schema(date(2014, 9, 6))  #-> datetime.date(2014, 9, 6)
schema('2014')
#-> Invalid: Invalid date format, expected Date, got 2014.
```

Arguments:









### `Time`
```python
Time(formats, localize=None, astz=None)
```

Validate that the input is a Python `time`.

Supports the following input values:

1. `time`: passthrough
2. `datetime`: takes the `.timetz()` part
2. string: parses (see [`DateTime`](#datetime))

Since `time` is subject to timezone problems,
make sure you've read the notes in the relevant section of [`DateTime`](#datetime) docs.

Arguments:










Files
-----



### `IsFile`
```python
IsFile()
```

Verify that the file exists.

```python
from good import Schema, IsFile

schema = Schema(IsFile())

schema('/etc/hosts')  #-> '/etc/hosts'
schema('/etc')
#-> Invalid: is not a file: expected Existing file path, got /etc
```






### `IsDir`
```python
IsDir()
```

Verify that the directory exists.






### `PathExists`
```python
PathExists()
```

Verify that the path exists.






