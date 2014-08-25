from .util import get_type_name, register_type_name


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

    def __init__(self, message, expected, provided=None, path=None, validator=None, **info):
        super(Invalid, self).__init__(message, expected, path, validator)
        self.message = message
        self.expected = expected
        self.provided = provided
        self.path = path
        self.validator = validator
        self.info = info

    def __repr__(self):
        return '{cls}({0.message!r}, ' \
               'expected={0.expected!r}, ' \
               'provided={0.provided!r}, ' \
               'path={0.path!r}, ' \
               'validator={0.validator!r}, ' \
               'info={0.info!r})' \
            .format(self, cls=type(self).__name__,)
    __str__ = __repr__

    def __unicode__(self):
        return u'{0.message} @ {path}: expected {0.expected}, got {0.provided}'.format(
            self,
            path=u''.join(map(
                lambda (i, v): u'[{!r}]'.format(v),
                self.path
            )),
        )


class MultipleInvalid(Invalid):
    """ Validation errors for multiple values.

    It wraps multiple validation errors, given as `errors`.
    Inherited methods (e.g. `__unicode__()`) are proxied to the first reported error

    :param errors: The reported errors
    :type errors: list[Invalid]
    """
    def __init__(self, errors):
        super(MultipleInvalid, self).__init__(*errors[0].args)

        #: The collected errors
        self.errors = errors

    def __repr__(self):
        return '{0}({1!r})'.format(type(self).__name__, self.errors)
