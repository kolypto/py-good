import collections
import six
from functools import wraps

from . import markers
from .errors import SchemaError, Invalid, MultipleInvalid
from .util import get_type_name, const


class CompiledSchema(object):
    """ Schema compiler.

    Converts a Schema into a callable, recursively.

    :param schema: Schema to use for validation
    :param path: Path to this schema
    :param default_keys: Default dictionary keys behavior (marker class)
    :param extra_keys: Default extra keys behavior (schema | marker class)
    :param matcher: Compile a "Matcher" schema: instead of throwing exceptions, it returns a boolean which indicates whether the value matches.

            This is used with mapping validation: a "matcher" is a lightweight alternative to CompiledSchema which economizes exceptions in favor of just returning booleans.

            Note that some values cannot be matchers: e.g. callables, which can typecast dictionary keys.
    """

    def __init__(self, schema, path, default_keys, extra_keys, matcher=False):
        assert issubclass(default_keys, markers.Marker), '`default_keys` value must be a Marker'

        self.path = path
        self.schema = schema
        self.default_keys = default_keys
        self.extra_keys = extra_keys
        self.matcher = matcher

        # Compile
        self.name = None
        self.compiled_type = None
        self.compiled = self.compile_schema(self.schema)

        assert self.compiled_type is not None, 'Compiler did not set a schema `compiled_type`'
        assert isinstance(self.name, six.text_type), 'Compiler did not set a valid schema name: {!r} (must be unicode)'.format(self.name)

    def __call__(self, value):
        """ Validate value against the compiled schema

        :param value: The value to validate
        :return: Sanitized value

            However, if the schema was compiled as "Matcher" (matcher=True) -- it returns:

            ( is-okay, sanitized-value )

            <is-okay> tells whether the matcher has matched, and <sanitized-value> is the final value (if it matched)
        """
        return self.compiled(value)

    def __repr__(self):
        return '{cls}{matcher}({0.schema!r}, ' \
               '{0.path!r}, ' \
               '{default_keys}, ' \
               '{extra_keys})' \
            .format(
                self,
                cls=type(self).__name__,
                matcher=':Matcher' if self.matcher else '',
                default_keys=self.default_keys.__name__,
                extra_keys=self.extra_keys.__name__ if isinstance(self.extra_keys, type) else repr(self.extra_keys)
            )

    def __unicode__(self):
        return self.name

    if six.PY3:
        __str__ = __unicode__

    #region Compilation Utils

    def get_schema_type(self, schema):
        """ Get schema type for the argument

        :param schema: Schema to analyze
        :return: COMPILED_TYPE constant
        :rtype: str|None
        """
        schema_type = type(schema)

        # Marker
        if issubclass(schema_type, markers.Marker):
            return const.COMPILED_TYPE.MARKER
        # Marker Type
        elif issubclass(schema_type, six.class_types) and issubclass(schema, markers.Marker):
            return const.COMPILED_TYPE.MARKER
        # Literal
        elif schema_type in const.literal_types:
            return const.COMPILED_TYPE.LITERAL
        # Type
        elif issubclass(schema_type, six.class_types):
            return const.COMPILED_TYPE.TYPE
        # Mapping
        elif isinstance(schema, collections.Mapping):
            return const.COMPILED_TYPE.MAPPING
        # Iterable
        elif isinstance(schema, collections.Iterable):
            return const.COMPILED_TYPE.ITERABLE
        # CompiledSchema
        elif isinstance(schema, CompiledSchema):
            return const.COMPILED_TYPE.SCHEMA
        # Schema
        # elif isinstance(schema, Schema):
        #    return const.COMPILED_TYPE.SCHEMA  # TODO: schema
        #Callable
        elif callable(schema):
            return const.COMPILED_TYPE.CALLABLE
        return None

    @property
    def priority(self):
        """ Get priority for this Schema.

        Used to sort mapping keys

        :rtype: int
        """
        # Markers have priority set on the class
        if self.compiled_type == const.COMPILED_TYPE.MARKER:
            return self.compiled.priority

        # Other types have static priority
        return const.compiled_type_priorities[self.compiled_type]

    @classmethod
    def sort_schemas(cls, schemas_list):
        """ Sort the provided list of schemas according to their priority.

        This also supports markers, and markers of a single type are also sorted according to the priority of the wrapped schema.

        :type schemas_list: list[CompiledSchema]
        :rtype: list[CompiledSchema]
        """
        return sorted(schemas_list,
                      key=lambda x: (
                          # Top-level priority
                          x.priority,
                          # Second-level priority (for markers of the common type)
                          # This ensures that Optional(1) always goes before Optional(int)
                          x.key_schema.priority if isinstance(x, markers.Marker) else 0
                      ), reverse=True)

    def sub_compile(self, schema, path=None, matcher=False):
        """ Compile a sub-schema

        :param schema: Validation schema
        :type schema: *
        :param path: Path to this schema, if any
        :type path: list|None
        :param matcher: Compile a matcher?
        :type matcher: bool
        :rtype: CompiledSchema
        """
        return type(self)(
            schema,
            self.path + (path or []),
            self.default_keys,
            self.extra_keys,
            matcher
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

    #endregion

    #region Compilation Procedure

    def get_schema_compiler(self, schema):
        """ Get compiler method for the provided schema

        :param schema: Schema to analyze
        :return: Callable compiled
        :rtype: callable|None
        """
        # Schema type
        schema_type = self.get_schema_type(schema)
        if schema_type is None:
            return None

        # Compiler
        compilers = {
            const.COMPILED_TYPE.LITERAL: self._compile_literal,
            const.COMPILED_TYPE.TYPE: self._compile_type,
            const.COMPILED_TYPE.SCHEMA: self._compile_schema,
            const.COMPILED_TYPE.CALLABLE: self._compile_callable,
            const.COMPILED_TYPE.ITERABLE: self._compile_iterable,
            const.COMPILED_TYPE.MAPPING: self._compile_mapping,
            const.COMPILED_TYPE.MARKER: self._compile_marker,
        }

        return compilers[schema_type]

    def compile_schema(self, schema):
        """ Compile the current schema into a callable validator

        :return: Callable validator
        :rtype: callable
        :raises SchemaError: Schema compilation error
        """
        compiler = self.get_schema_compiler(schema)

        if compiler is None:
            raise SchemaError(_(u'Unsupported schema data type {!r}').format(type(schema).__name__))

        return compiler(schema)

    def _compile_literal(self, schema):
        """ Compile literal schema: type and value matching """
        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.LITERAL
        self.name = six.text_type(schema)

        # Error partials
        schema_type = type(schema)
        err_type  = self.Invalid(_(u'Wrong value type'), get_type_name(schema_type))
        err_value = self.Invalid(_(u'Invalid value'), self.name)

        # Matcher
        if self.matcher:
            def match_literal(v):
                return type(v) == schema_type and v == schema, v
            return match_literal

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
        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.TYPE
        self.name = get_type_name(schema)

        # Error partials
        err_type = self.Invalid(_(u'Wrong type'), self.name)

        # Matcher
        if self.matcher:
            def match_type(v):
                return type(v) == schema, v
            return match_type

        # Validator
        def validate_type(v):
            # Type check
            if type(v) != schema:  # strict!
                # expected=<type>, provided=<type>
                raise err_type(get_type_name(type(v)))
            # Fine
            return v

        return validate_type

    def _compile_schema(self, schema):
        """ Compile another schema """
        assert self.matcher == schema.matcher

        self.name = schema.name
        self.compiled_type = schema.compiled_type

        return schema.compiled

    def _compile_callable(self, schema):
        """ Compile callable: wrap exceptions with correct paths """
        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.CALLABLE
        if hasattr(schema, 'name'):
            self.name = six.text_type(schema.name)
        elif hasattr(schema, '__name__'):
            self.name = six.text_type(schema.__name__) + u'()'
        else:
            self.name = six.text_type(schema)

        # Error utils
        enrich_exception = lambda e, value: e.enrich(
            expected=self.name,
            provided=six.text_type(value),
            path=self.path,
            validator=schema)

        # Validator
        @wraps(schema)
        def validate_with_callable(v):
            try:
                # Try this callable
                return schema(v)
            except Invalid as e:
                # Enrich & re-raise
                enrich_exception(e, v)
                raise
            except Exception as e:
                e = Invalid(
                    _(u'{Exception}: {message}').format(
                        Exception=type(e).__name__,
                        message=six.text_type(e))
                )
                raise enrich_exception(e, v)

        # Matcher
        if self.matcher:
            def match_with_callable(v):
                try:
                    return True, validate_with_callable(v)
                except Invalid:
                    return False, v
            return match_with_callable

        return validate_with_callable

    def _compile_iterable(self, schema):
        """ Compile iterable: iterable of schemas treated as allowed values """
        # Compile each member as a schema
        schema_type = type(schema)
        schema_subs = tuple(map(self.sub_compile, schema))

        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.ITERABLE
        self.name = _(u'{iterable_cls}[{iterable_options}]').format(
            iterable_cls=get_type_name(schema_type),
            iterable_options=_(u'|').join(x.name for x in schema_subs)
        )

        # Error partials
        err_type = self.Invalid(_(u'Wrong value type'), get_type_name(schema_type))
        err_value = self.Invalid(_(u'Invalid value'), self.name)

        # Validator
        def validate_iterable(l):
            # Type check
            if not isinstance(l, schema_type):
                # expected=<type>, provided=<type>
                raise err_type(provided=get_type_name(type(l)))

            # Each `v` member should match to any `schema` member
            errors = []  # Errors for every value
            values = []  # Sanitized values
            for value_index, value in enumerate(l):
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

        # Matcher
        if self.matcher:
            return self._compile_callable(validate_iterable)  # Stupidly use it as callable

        return validate_iterable

    def _compile_marker(self, schema):
        """ Compile marker: sub-schema with special type """
        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.MARKER

        # If this marker is not instantiated -- do it with an identity callable which is valid for everything
        if issubclass(type(schema), six.class_types):
            identity = lambda v: v
            schema = schema(identity).on_compiled(name=_(u'*'))

        # Compile Marker's schema
        key_schema = self.sub_compile(schema.key, matcher=self.matcher)
        schema.on_compiled(key_schema=key_schema, name=key_schema.name)

        # Marker is a callable
        self.name = schema.name
        return schema

    def _compile_mapping(self, schema):
        """ Compile mapping: key-value matching """
        assert not self.matcher, 'Mappings cannot be matchers'

        # This stuff is tricky, but thankfully, I like comments :)

        # Set default Marker on all keys.
        # This makes sure that all keys will still become markers, and hence have the correct default behavior
        schema = {self.default_keys(k) if self.get_schema_type(k) != const.COMPILED_TYPE.MARKER else k: v
                  for k, v in schema.items()}

        # Add `Extra`
        # Every Schema implicitly has an `Extra` that defaults to `extra_keys`.
        # Note that this is the only place in the code where Marker behavior is hardcoded :)
        schema.setdefault(markers.Extra, self.extra_keys)

        # Compile both keys & values as schemas.
        # Key schemas are compiled as "Matchers" for performance.
        compiled = {self.sub_compile(key, matcher=True): self.sub_compile(value)
                    for key, value in schema.items()}

        # Notify Markers that they were compiled.
        # _compile_marker() has already done part of the job: it only specified `key_schema`.
        # Here we let the Marker know its `value_schema` as well.
        for key_schema, value_schema in compiled.items():
            if key_schema.compiled_type == const.COMPILED_TYPE.MARKER:
                key_schema.compiled.on_compiled(value_schema=value_schema)

        # Sort key schemas for matching.
        # Since various schema types have different priority, we need to sort these accordingly.
        # Then, literals match before types, and Markers can define execution order using `priority`.
        # For instance, Remove() should be called first (before any validation takes place),
        # while Extra() should be checked last so it catches all extra keys that did not match other key schemas.
        compiled = [ (key_schema, compiled[key_schema])
                     for key_schema in self.sort_schemas(compiled.keys())]
        ''' :var  compiled: Sorted list of CompiledSchemas: (key-schema, value-schema),
            :type compiled: list[CompiledSchema, CompiledSchema]
        '''

        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.MAPPING
        self.name = _(u'{mapping_cls}[{mapping_keys}]').format(
            mapping_cls=get_type_name(type(schema)),
            mapping_keys=_(u',').join(key_schema.name for key_schema, value_schema in compiled)
        )

        # Error partials
        schema_type = type(schema)
        err_type = self.Invalid(_(u'Wrong value type'), get_type_name(schema_type))

        # Validator
        def validate_mapping(d):
            # Type check
            if not isinstance(d, schema_type):
                # expected=<type>, provided=<type>
                raise err_type(provided=get_type_name(type(d)))

            # We're going to iterate it destructively, so need to make a fresh copy
            d = d.copy()

            # For each schema key, pick matching input key-value pairs.
            # Since we always have Extra which is a catch-all -- this will always result into a full input coverage.
            # Also, key schemas are sorted according to the priority, we're handling each set of matching keys in order.

            errors = []  # Collect errors on the fly
            output = schema_type()  # Rebuild the input (since schemas may sanitize keys)

            for key_schema, value_schema in compiled:
                # First, collect matching (key, value) pairs for the `key_schema`.
                # Note that `key_schema` can change the value (e.g. `Coerce(int)`), so for every key
                # we store both the initial value (`input-key`) and the sanitized value (`sanitized-key`).
                # This results into a list of triples: [(input-key, sanitized-key, input-value), ...].

                matches = []

                # Walk all input values and pick those that match the current `key_schema`
                for k in list(d.keys()):
                    # Exec key schema on the input key.
                    # Since all key schemas are compiled as matchers -- we get a tuple (key-matched, sanitized-key)

                    okay, sanitized_k = key_schema(k)

                    # If this key has matched -- append it to the list of matches for the current `key_schema`.
                    # Also, remove the key from the original input so it does not match any other key schemas
                    # with lower priorities.
                    if okay:
                        matches.append(( k, sanitized_k, d.pop(k) ))

                # Now, having a `key_schema` and a list of matches for it, do validation.
                # If the key is a marker -- execute the marker first so it has a chance to modify the input,
                # and then proceed with value validation.

                # Execute Marker first.
                if key_schema.compiled_type == const.COMPILED_TYPE.MARKER:
                    # Note that Markers can raise errors as well.
                    # Since they're compiled -- all validation errors within the markers are `Invalid`, not anything else.
                    try:
                        matches = key_schema.compiled.execute(matches)
                    except Invalid as e:
                        # Add marker errors to the list of Invalid reports for this schema.
                        # Using enrich(), we're also setting `path` prefix, and other info known at this step.
                        errors.append(e.enrich(
                            # Markers are responsible to set `expected`, `provided`, `validator`
                            path=self.path,
                            validator=key_schema.compiled
                        ))
                        # If a marker raised an error -- the (key, value) pair is already Invalid, and no
                        # further validation is required.
                        continue

                # Proceed with validation.
                # Now, we validate values for every (key, value) pairs in the current list of matches,
                # and rebuild the mapping.
                for k, sanitized_k, v in matches:
                    try:
                        # Execute the value schema and store it into the rebuilt mapping
                        # using the sanitized key, which might be different from the original key.
                        output[sanitized_k] = value_schema(v)
                    except Invalid as e:
                        # Any value validation errors are appended to the list of Invalid reports for the schema
                        # enrich() adds more info on the collected errors.
                        errors.append(e.enrich(
                            expected=value_schema.name,
                            provided=six.text_type(v),
                            path=self.path + [k],
                            validator=value_schema
                        ))

            assert not d, 'Dict must be empty after destructive iteration: {!r}'.format(d)

            # Errors?
            if errors:
                # Note that we did not care about whether a sub-schema raised a single Invalid or MultipleInvalid,
                # since MultipleInvalid will flatten the list for us.
                raise MultipleInvalid.if_multiple(errors)

            # Finish
            return output

        return validate_mapping

    #endregion
