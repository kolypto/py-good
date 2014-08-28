import six


class BaseError(Exception):
    """ Base validation exception """


class SchemaError(BaseError):
    """ Schema error (e.g. malformed) """


class Invalid(BaseError):
    """ Validation error for a single value.

    Note: validators can skip `provided`, `path`, `validator`: Schema will set it dynamically

    :param message: Validation error message
    :type message: unicode
    :param expected: Expectation message (which can be messy in some cases)
    :type expected: unicode
    :param provided: Provided value representation
    :param provided: unicode
    :param path: Path to the error value.

        E.g. if an invalid value was encountered at ['a'].b[1], then path=['a', 'b', 1]

    :type path: list[str]
    :param validator: The validator that has failed: a schema item
    :type validator: *
    :param info: Custom values that might be supplied by the validator
    :type info: dict
    """

    def __init__(self, message, expected=None, provided=None, path=None, validator=None, **info):
        super(Invalid, self).__init__(message, expected, path, validator)
        self.message = message
        self.expected = expected
        self.provided = provided
        self.path = path or []
        self.validator = validator
        self.info = info

    def __iter__(self):
        """ Iterate over container errors.

        For `Invalid`, just yields self, however for `MultipleInvalid` it yields every contained errors.
        """
        yield self

    def __repr__(self):
        return '{cls}({0.message!r}, ' \
               'expected={0.expected!r}, ' \
               'provided={0.provided!r}, ' \
               'path={0.path!r}, ' \
               'validator={0.validator!r}, ' \
               'info={0.info!r})' \
            .format(self, cls=type(self).__name__,)

    def __unicode__(self):
        return u'{0.message} @ {path}: expected {0.expected}, got {0.provided}'.format(
            self,
            path=u''.join(map(
                lambda v: u'[{!r}]'.format(v),
                self.path
            )),
        )

    def enrich(self, expected=None, provided=None, path=None, validator=None, path_prefix=True):
        """ Enrich the error.

        This works with both Invalid and MultipleInvalid (thanks to __iter__ method).

        :param expected: Invalid.expected default
        :param provided: Invalid.provided default
        :param path: Invalid.path chunk
        :param validator: Invalid.validator default
        :param path_prefix: Whether `path` should be prepended? Otherwise, it's appended
        :type path_prefix: bool
        :rtype: Invalid|MultipleInvalid
        """
        for e in self:
            if e.expected is None and expected is not None:
                e.expected = expected
            if e.provided is None and provided is not None:
                e.provided = provided
            if e.validator is None and validator is not None:
                e.validator = validator

            if path_prefix:
                e.path = (path or []) + e.path
            else:
                e.path = (path or []) + e.path
        return self

    if six.PY3:
        __str__ = __unicode__


class MultipleInvalid(Invalid):
    """ Validation errors for multiple values.

    It wraps multiple validation errors, given as `errors`.
    Inherited methods (e.g. `__unicode__()`) are proxied to the first reported error.

    :param errors: The reported errors.

        If it contains MultipleInvalid errors -- the list is recursively flattened so all of them are guaranteed to be instances of `Invalid`

    :type errors: list[Invalid]
    """
    def __init__(self, errors):
        # Flatten errors
        errors = self.flatten(errors)

        # Create from errors
        e = errors[0]
        super(MultipleInvalid, self).__init__(e.message, e.expected, e.provided, e.path, e.validator, **e.info)

        #: The collected errors
        self.errors = errors

    def __iter__(self):
        return iter(self.errors)

    def __repr__(self):
        return '{cls}({0!r})'.format(self.errors, cls=type(self).__name__)

    @classmethod
    def flatten(cls, errors):
        """ Unwind `MultipleErrors` to have a plain list of `Invalid`

        :type errors: list[Invalid|MultipleInvalid]
        :rtype: list[Invalid]
        """
        ers = []
        for e in errors:
            if isinstance(e, MultipleInvalid):
                ers.extend(cls.flatten(e.errors))
            else:
                ers.append(e)
        return ers

    @classmethod
    def if_multiple(cls, errors):
        """ Provided a list of errors, choose which one to throw: `Invalid` or `MultipleInvalid`.

        `MultipleInvalid` is only used for multiple errors.

        :param errors: The list of collected errors
        :type errors: list[Invalid]
        :rtype: Invalid|MultipleInvalid
        """
        assert errors, 'Errors list is empty'
        return errors[0] if len(errors) == 1 else MultipleInvalid(errors)
