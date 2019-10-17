""" Slim yet handsome validation library.

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
"""
# Core

from .schema.errors import SchemaError, Invalid, MultipleInvalid
from .schema.util import register_type_name

from .schema import Schema

from .schema import markers
from .schema.markers import *

# Helpers
from .helpers import *

# Validators
from .validators import *
