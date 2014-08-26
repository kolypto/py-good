""" Slim yet handsome validation library.

Core features:

* Simple
* Customizable
* Supports nested validation
* User-friendly error messages
* Internationalization!
* Python 2.7, 3.3+ compatible

Inspired by the amazing [alecthomas/voluptuous](https://github.com/alecthomas/voluptuous) and 100% compatible with it.
The whole internals have been reworked towards readability and robustness. And yeah, the docs are now exhaustive :)
"""

import gettext
import six

gettext.install('good', **({'unicode': True} if six.PY2 else {}))

from .schema.errors import SchemaError, Invalid, MultipleInvalid
from .schema.util import register_type_name

from .schema import Schema
from .schema.markers import *
