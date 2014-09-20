import six

from . import markers, signals
from .errors import SchemaError, Invalid, MultipleInvalid
from .util import get_type_name, get_literal_name, get_callable_name,  const, primitive_type


def Identity(v):
    """ Identity function.

    Special `identity` function which matches everything.
    Is primarily used for the `Extra` marker, as well as all other markers specified as classes.
    """
    return v
Identity.name = _(u'*')  # Set a name on it (for repr())


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

    def __init__(self, schema, path, default_keys=None, extra_keys=None, matcher=False):
        assert default_keys is None or issubclass(default_keys, markers.Marker), '`default_keys` value must be a Marker or None'

        self.path = path
        self.schema = schema
        self.default_keys = default_keys or markers.Required
        self.extra_keys = extra_keys or markers.Reject
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

    @property
    def supports_undefined(self):
        """ Test whether this schema supports Undefined.

        A Schema that supports `Undefined`, when given `Undefined`, should return some value (other than `Undefined`)
        without raising errors.

        This is designed to support a very special case like that:

        ```python
        Schema(Default(0)).supports_undefined  #-> True
        ```

        This way a validator can declare that it has a default in case no value was provided,
        and this case happens when:

        1. A [`Required`](#required) mapping key was not provided, and it's mapped to `Default()`
        2. .. no more supported cases. Yet.

        :rtype: bool
        """
        # Test
        try:
            yes = self(const.UNDEFINED) is not const.UNDEFINED
        except (Invalid, SchemaError):
            yes = False

        # Remember (lame @cached_property)
        self.__dict__['supports_undefined'] = yes
        return yes

    #region Compilation Utils

    @classmethod
    def get_schema_type(cls, schema):
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
        # CompiledSchema
        elif isinstance(schema, CompiledSchema):
            return const.COMPILED_TYPE.SCHEMA
        else:
            return primitive_type(schema)

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
                          # Top-level priority:
                          # priority of the schema itself
                          x.priority,
                          # Second-level priority (for markers of the common type)
                          # This ensures that Optional(1) always goes before Optional(int)
                          x.compiled.key_schema.priority if x.compiled_type == const.COMPILED_TYPE.MARKER else 0
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
            None,
            None,
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
                expected, #six.text_type(expected),  # -- must be unicode
                provided, #six.text_type(provided),  # -- must be unicode
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
            const.COMPILED_TYPE.ENUM: self._compile_enum,
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
        self.name = get_literal_name(schema)

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
                raise err_value(get_literal_name(v))
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

        # Type check function
        if six.PY2 and schema is basestring:
            # Relaxed rule for Python2 basestring
            typecheck = lambda v: isinstance(v, schema)
        else:
            # Strict type check for everything else
            typecheck = lambda v: type(v) == schema

        # Matcher
        if self.matcher:
            def match_type(v):
                return typecheck(v), v
            return match_type

        # Validator
        def validate_type(v):
            # Type check
            if not typecheck(v):
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

    def _compile_enum(self, schema):
        assert not self.matcher, 'Enum cannot be a matcher'

        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.ENUM
        self.name = six.text_type(schema.__name__)

        # Error partials
        err_value = self.Invalid(_(u'Invalid {enum} value').format(enum=self.name), self.name)

        # Validator
        def validate_enum(v):
            try:
                return schema(v)
            except ValueError:
                raise err_value(get_literal_name(v))
        return validate_enum


    def _compile_callable(self, schema):
        """ Compile callable: wrap exceptions with correct paths """
        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.CALLABLE
        self.name = get_callable_name(schema)

        # Error utils
        enrich_exception = lambda e, value: e.enrich(
            expected=self.name,
            provided=get_literal_name(value),
            path=self.path,
            validator=schema)

        # Validator
        def validate_with_callable(v):
            try:
                # Try this callable
                return schema(v)
            except Invalid as e:
                # Enrich & re-raise
                enrich_exception(e, v)
                raise
            except const.transformed_exceptions as e:
                message = _(u'{message}').format(
                    Exception=type(e).__name__,
                    message=six.text_type(e))
                e = Invalid(message)
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

        # When the schema is an iterable with a single item (e.g. [dict(...)]),
        # Invalid errors from schema members should be immediately used.
        # This allows to report sane errors with `Schema([{'age': int}])`
        error_passthrough = len(schema_subs) == 1

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
            for value_index, value in list(enumerate(l)):
                # Walk through schema members and test if any of them match
                for value_schema in schema_subs:
                    try:
                        # Try to validate
                        values.append(value_schema(value))
                        break  # Success!
                    except signals.RemoveValue:
                        # `value_schema` commanded to drop this value
                        break
                    except Invalid as e:
                        if error_passthrough:
                            # Error-Passthrough enabled: add the original error
                            errors.append(e.enrich(path=[value_index]))
                            break
                        else:
                            # Error-Passthrough disabled: Ignore errors and hope other members will succeed better
                            pass
                else:
                    errors.append(err_value(get_literal_name(value), path=[value_index]))

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
            schema = schema(Identity)  \
                .on_compiled(name=Identity.name)  # Set a special name on it

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
                key_schema.compiled.on_compiled(value_schema=value_schema, as_mapping_key=True)

        # Sort key schemas for matching.

        # Since various schema types have different priority, we need to sort these accordingly.
        # Then, literals match before types, and Markers can define execution order using `priority`.
        # For instance, Remove() should be called first (before any validation takes place),
        # while Extra() should be checked last so it catches all extra keys that did not match other key schemas.

        # In addition, since mapping keys are mostly literals, we want direct matching instead of the costly function calls.
        # Hence, remember which of them are literals or 'catch-all' markers.
        is_literal  = lambda key_schema: key_schema.compiled.key_schema.compiled_type == const.COMPILED_TYPE.LITERAL
        is_identity = lambda identity: key_schema.compiled.key_schema is Identity

        compiled = [ (key_schema, compiled[key_schema], is_literal(key_schema), is_identity(key_schema))
                     for key_schema in self.sort_schemas(compiled.keys())]
        ''' :var  compiled: Sorted list of CompiledSchemas: (key-schema, value-schema, is-literal),
            :type compiled: list[CompiledSchema, CompiledSchema, bool]
        '''

        # Prepare self
        self.compiled_type = const.COMPILED_TYPE.MAPPING
        self.name = _(u'{mapping_cls}[{mapping_keys}]').format(
            mapping_cls=get_type_name(type(schema)),
            mapping_keys=_(u',').join(key_schema.name for key_schema, value_schema, is_literal, is_identity in compiled)
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

            # For each schema key, pick matching input key-value pairs.
            # Since we always have Extra which is a catch-all -- this will always result into a full input coverage.
            # Also, key schemas are sorted according to the priority, we're handling each set of matching keys in order.

            errors = []  # Collect errors on the fly
            d_keys = set(d.keys())  # Make a copy of dict keys for destructive iteration

            for key_schema, value_schema, is_literal, is_identity in compiled:
                # First, collect matching (key, value) pairs for the `key_schema`.
                # Note that `key_schema` can change the value (e.g. `Coerce(int)`), so for every key
                # we store both the initial value (`input-key`) and the sanitized value (`sanitized-key`).
                # This results into a list of triples: [(input-key, sanitized-key, input-value), ...].

                matches = []

                if is_literal:  # (short-circuit for literals)
                    # Since mapping keys are mostly literals --
                    # save some iterations & function calls in favor of direct matching,
                    # which introduces a HUGE performance improvement
                    k = key_schema.schema.key  # get the literal from the marker
                    if k in d_keys:
                        # (See comments below)
                        matches.append(( k, k, d[k] ))
                        d_keys.remove(k)
                elif is_identity:  # (short-circuit for Marker(Identity))
                    # When this value is an identity function -- we plainly add all keys to it.
                    # This is to short-circuit catch-all markers like `Extra`, which, being executed last,
                    # just gets all remaining keys.
                    matches.extend((k, k, d[k]) for k in d_keys)
                    d_keys = None  # empty it since we've processed everything
                elif d_keys:
                    # For non-literal schemas we have to walk all input keys
                    # and detect those that match the current `key_schema`.
                    # In contrast to literals, such keys may have multiple matches (e.g. `{ int: 1 }`).

                    # Note that this condition branch includes the logic from the short-circuited logic implemented above,
                    # but is less performant.

                    for k in tuple(d_keys):
                        # Exec key schema on the input key.
                        # Since all key schemas are compiled as matchers -- we get a tuple (key-matched, sanitized-key)

                        okay, sanitized_k = key_schema(k)

                        # If this key has matched -- append it to the list of matches for the current `key_schema`.
                        # Also, remove the key from the original input so it does not match any other key schemas
                        # with lower priorities.
                        if okay:
                            matches.append(( k, sanitized_k, d[k] ))
                            d_keys.remove(k)

                # Now, having a `key_schema` and a list of matches for it, do validation.
                # If the key is a marker -- execute the marker first so it has a chance to modify the input,
                # and then proceed with value validation.

                # Execute Marker first.
                if key_schema.compiled_type == const.COMPILED_TYPE.MARKER:
                    # Note that Markers can raise errors as well.
                    # Since they're compiled - all marker errors are raised as `Invalid`.
                    try:
                        matches = key_schema.compiled.execute(d, matches)
                    except Invalid as e:
                        # Add marker errors to the list of Invalid reports for this schema.
                        # Using enrich(), we're also setting `path` prefix, and other info known at this step.
                        errors.append(e.enrich(
                            # Markers are responsible to set `expected`, `provided`, `validator`
                            expected=key_schema.name,
                            provided=None,  # Marker's required to set that
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
                        d[sanitized_k] = value_schema(v)

                        # Remove the original key in case `key_schema` has transformed it.
                        if k != sanitized_k:
                            del d[k]
                    except signals.RemoveValue:
                        # `value_schema` commanded to drop this value
                        del d[k]
                    except Invalid as e:
                        # Any value validation errors are appended to the list of Invalid reports for the schema
                        # enrich() adds more info on the collected errors.
                        errors.append(e.enrich(
                            expected=value_schema.name,
                            provided=get_literal_name(v),
                            path=self.path + [k],
                            validator=value_schema
                        ))

            assert not d_keys, 'Keys must be empty after destructive iteration. Remainder: {!r}'.format(d_keys)

            # Errors?
            if errors:
                # Note that we did not care about whether a sub-schema raised a single Invalid or MultipleInvalid,
                # since MultipleInvalid will flatten the list for us.
                raise MultipleInvalid.if_multiple(errors)

            # Finish
            return d

        return validate_mapping

    #endregion
