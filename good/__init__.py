""" Slim yet handsome validation library.

Core features:

* Simple
* Customizable
* Supports nested validation
* User-friendly error messages
* Internationalization!

Inspired by the amazing [alecthomas/voluptuous](https://github.com/alecthomas/voluptuous) and 100% compatible with it.
The whole internals have been reworked towards readability and robustness. And yeah, the docs are now exhaustive :)
"""

import gettext
gettext.install('good', unicode=True)


from .schema.errors import SchemaError, Invalid, MultipleInvalid
from .schema.util import register_type_name

from .schema import Schema
from .schema.markers import *
