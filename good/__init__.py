""" Slim yet handsome validation library.

Core features:

* Simple
* Customizable
* Supports nested model validation
* Error paths (which field contains the error)
* User-friendly error messages
* Internationalization!
* [Robust](misc/performance/performance.md): 10 000 validations per second
* Python 2.7, 3.3+ compatible
* 100% documented and unit-tested

Inspired by the amazing [alecthomas/voluptuous](https://github.com/alecthomas/voluptuous) and 100% compatible with it.
The whole internals have been reworked towards readability and robustness. And yeah, the docs are now exhaustive :)

The rationale for a remake was to make it modular with a tiny core and everything else built on top of that,
ensure that all error messages are user-friendly out of the box, and tweak the performance.
"""

# Init gettext translations, and do not litter the root scope
import gettext as _gettext, six as _six
_gettext.install('good', **({'unicode': True} if _six.PY2 else {}))


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
