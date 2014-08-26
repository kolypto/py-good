import collections
import six
from functools import partial, wraps

from . import markers
from .errors import SchemaError, Invalid, MultipleInvalid
from .util import get_type_name


class CompiledSchema(object):
    """ Schema compiler.

    Converts a Schema into a callable, recursively.

    :param schema: Schema to use for validation
    :param path: Path to this schema
    :param default_keys: Default dictionary keys behavior (marker class)
    :param extra_keys: Default extra keys behavior (schema | marker class)
    """

    #: Types that are treated as literals
    _literal_types = six.integer_types + (six.text_type, six.binary_type) + (bool, float, complex, object, type(None))

    def __init__(self, schema, path, default_keys, extra_keys):
        assert issubclass(default_keys, markers.Marker), '`default_keys` value must be a Marker'

        self.path = path
        self.schema = schema
        self.default_keys = default_keys
        self.extra_keys = extra_keys

        # Compile
        self.name = None
        self.compiled = self.compile_schema(self.schema)
        assert isinstance(self.name, six.text_type), 'Compiler did not set a valid schema name: {!r} (must be unicode)'.format(self.name)

    def __call__(self, value):
        """ Validate value against the compiled schema

        :param value: The value to validate
        :return: Sanitized value
        """
        return self.compiled(value)

    def __repr__(self):
        return '{cls}({0.schema!r}, ' \
               '{0.path!r}, ' \
               '{default_keys}, ' \
               '{extra_keys})' \
            .format(
                self,
                cls=type(self).__name__,
                default_keys=self.default_keys.__name__,
                extra_keys=self.extra_keys.__name__ if isinstance(self.extra_keys, type) else repr(self.extra_keys)
            )

    def __unicode__(self):
        return self.name

    if six.PY3:
        __str__ = __unicode__

    #region Compilation

    def sub_compile(self, schema, path=None):
        """ Compile a sub-schema

        :param schema: Validation schema
        :type schema: *
        :param path: Path to this schema, if any
        :type path: list|None
        :rtype: CompiledSchema
        """
        return type(self)(
            schema,
            self.path + (path or []),
            self.default_keys,
            self.extra_keys
        )

    def Invalid(self, message, expected):
        """ Helper for Invalid errors.

        Typical use:

        err_type = self.Invalid(_(u'Message'), self.name)
        raise err_type(<provided-value>)

        Note: `provided` and `expected` are unicode-typecasted automatically

        :type message: unicode
        :type expected: unicode
        """
        def InvalidPartial(provided, path=None, **info):
            """ Create an Invalid exception

            :type provided: unicode
            :type path: list|None
            :rtype: Invalid
            """
            return Invalid(
                message,
                six.text_type(expected),
                six.text_type(provided),
                self.path + (path or []),
                self.schema,
                **info
            )
        return InvalidPartial

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
        elif issubclass(schema_type, six.class_types):
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
            raise SchemaError(_(u'Unsupported schema data type {!r}').format(schema_type.__name__))
        return compiler(schema)

    def _compile_literal(self, schema):
        """ Compile literal schema: type and value matching """
        self.name = six.text_type(schema)

        # Prepare
        schema_type = type(schema)
        err_type  = self.Invalid(_(u'Wrong value type'), get_type_name(schema_type))
        err_value = self.Invalid(_(u'Invalid value'), self.name)

        # Validator
        def validate_literal(v):
            # Type check
            if type(v) != schema_type:
                # expected=<type>, provided=<type>
                raise err_type(get_type_name(type(v)))
            # Equality check
            if v != schema:
                # expected=<value>, provided=<value>
                raise err_value(v)
            # Fine
            return v
        return validate_literal

    def _compile_type(self, schema):
        """ Compile type schema: plain type matching """
        self.name = get_type_name(schema)

        # Prepare
        err_type = self.Invalid(_(u'Wrong type'), self.name)

        # Validator
        def validate_type(v):
            # Type check
            if type(v) != schema:  # strict!
                # expected=<type>, provided=<type>
                raise err_type(get_type_name(type(v)))
            # Fine
            return v

        return validate_type

    def _compile_callable(self, schema):
        """ Compile callable: wrap exceptions with correct paths """
        if hasattr(schema, 'name'):
            self.name = six.text_type(schema.name)
        elif hasattr(schema, '__name__'):
            self.name = six.text_type(schema.__name__) + u'()'
        else:
            self.name = six.text_type(schema)

        # Prepare
        def enrich_exception(e, value):
            """ Enrich an exception """
            if e.expected is None:
                e.expected = _(u'<???>')
            if e.provided is None:
                e.provided = six.text_type(value)
            e.path = self.path + e.path
            if e.validator is None:
                e.validator = schema
            return e

        # Validator
        @wraps(schema)
        def validate_with_callable(value):
            try:
                # Try this callable
                return schema(value)
            except Invalid as e:
                # Enrich & re-raise
                enrich_exception(e, value)
                raise
            except Exception as e:
                e = Invalid(
                    _(u'{Exception}: {message}').format(
                        Exception=type(e).__name__,
                        message=six.text_type(e))
                )
                raise enrich_exception(e, value)

        return validate_with_callable

    def _compile_iterable(self, schema):
        """ Compile iterable: iterable of schemas treated as allowed values """
        # Compile each member as a schema
        schema_type = type(schema)
        schema_subs = tuple(map(self.sub_compile, schema))
        self.name = _(u'{iterable_cls}[{iterable_options}]').format(
            iterable_cls=get_type_name(schema_type),
            iterable_options=_(u'|').join(x.name for x in schema_subs)
        )

        # Prepare
        err_type = self.Invalid(_(u'Wrong value type'), get_type_name(schema_type))
        err_value = self.Invalid(_(u'Invalid value'), self.name)

        # Validator
        def validate_iterable(v):
            # Type check
            if not isinstance(v, schema_type):
                # expected=<type>, provided=<type>
                raise err_type(provided=get_type_name(type(v)))

            # Each `v` member should match to any `schema` member
            errors = []  # Errors for every value
            values = []  # Sanitized values
            for value_index, value in enumerate(v):
                # Walk through schema members and test if any of them match
                for member in schema_subs:
                    try:
                        # Try to validate
                        values.append(member(value))
                        break  # Success!
                    except Invalid as e:
                        # Ignore errors and hope other members will succeed better
                        pass
                else:
                    errors.append(err_value(value, path=[value_index]))

            # Errors?
            if errors:
                raise MultipleInvalid.if_multiple(errors)

            # Typecast and finish
            return schema_type(values)

        return validate_iterable

    def _compile_mapping(self, schema):
        """ Compile mapping: key-value matching """



    #endregion
