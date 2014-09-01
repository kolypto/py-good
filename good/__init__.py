""" Slim yet handsome validation library.

Core features:

* Simple
* Customizable
* Supports nested model validation
* Error paths (which field contains the error)
* User-friendly error messages
* Internationalization!
* Python 2.7, 3.3+ compatible

Inspired by the amazing [alecthomas/voluptuous](https://github.com/alecthomas/voluptuous) and 100% compatible with it.
The whole internals have been reworked towards readability and robustness. And yeah, the docs are now exhaustive :)
"""

# Init gettext translations
import gettext
import six

gettext.install('good', **({'unicode': True} if six.PY2 else {}))

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
