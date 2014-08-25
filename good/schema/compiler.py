import collections
import six
from functools import partial

from . import markers
from .errors import SchemaError, Invalid, MultipleInvalid
from .util import get_type_name


class CompiledSchema(object):
    """ Schema compiler.

    Converts a Schema into a callable, recursively.

    :param path: Path to this schema
    :param schema: Schema to use for validation
    :param default_keys: Default dictionary keys behavior (marker class)
    :param extra_keys: Default extra keys behavior (schema)
    """

    #: Types that are treated as literals
    _literal_types = six.integer_types + (six.text_type, six.binary_type) + (bool, float, complex, object, type(None))

    def __init__(self, path, schema, default_keys, extra_keys):
        assert issubclass(default_keys, markers.Marker), '`default_keys` value must be a Marker'

        self.path = path
        self.schema = schema
        self.default_keys = default_keys
        self.extra_keys = extra_keys
        self.compiled = self.compile_schema(self.schema)

    def __call__(self, value):
        """ Validate value against the compiled schema

        :param value: The value to validate
        :return: Sanitized value
        """
        return self.compiled(value)

    #region Compilation

    def compile_schema(self, schema):
        """ Compile the current schema into a callable validator

        :return: Callable validator
        :rtype: callable
        :raises SchemaError: Schema compilation error
        """
        compiler = None
        schema_type = type(schema)

        # Literal
        if schema_type in self._literal_types:
            compiler = self._compile_literal
        # Type
        elif isinstance(schema_type, six.class_types):
            compiler = self._compile_type
        # Mapping
        elif isinstance(schema, collections.Mapping):
            compiler = self._compile_mapping
        # Iterable
        elif isinstance(schema, collections.Iterable):
            compiler = self._compile_iterable
        # Schema, CompiledSchema
        elif isinstance(schema, CompiledSchema):
            return schema.compiled
        # Callable
        elif callable(schema):
            compiler = self._compile_callable
        # Finish
        if compiler is None:
            raise SchemaError('Unsupported schema data type {!r}'.format(schema_type.__name__))
        return compiler(schema)

    def _compile_literal(self, schema):
        """ Compile literal schema: type and value matching """
        schema_type = type(schema)
        err = partial(Invalid, path=self.path, validator=schema)
        err_type = partial(err, _(u'Wrong value type'), expected=get_type_name(schema_type))
        err_value = partial(err, _(u'Invalid value'), expected=unicode(schema))

        def validate_literal(v):
            # Type check
            if not isinstance(v, schema_type):
                # expected=<type>, provided=<type>
                raise err_type(provided=get_type_name(type(v)))
            # Equality check
            if v != schema:
                # expected=<value>, provided=<value>
                raise err_value(provided=unicode(v))
            # Fine
            return v
        return validate_literal

    def _compile_type(self, schema):
        """ Compile type schema: plain type matching """
        err_type = partial(Invalid, expected=get_type_name(schema), path=self.path, validator=schema)

        def validate_type(v):
            # Type check
            if not isinstance(v, schema):
                # expected=<type>, provided=<type>
                raise err_type(_(u'Wrong type'), provided=get_type_name(type(v)))
            # Fine
            return v

        return validate_type



    #endregion
