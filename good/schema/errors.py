from .util import get_type_name, register_type_name


class BaseError(Exception):
    """ Base validation exception """


class SchemaError(BaseError):
    """ Schema error (e.g. malformed) """


class Invalid(BaseError):
    """ Validation error for a single value.

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

    def __init__(self, message, expected, provided, path, validator, **info):
        super(Invalid, self).__init__(message, expected, path, validator)
        self.expected = expected
        self.provided = provided
        self.path = path
        self.validator = validator
        self.info = info

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
