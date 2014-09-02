class ValidatorBase(object):
    """ Base for class-based validators """

    #: Validator name.
    #: Must be overridden in subclasses, and potentially hold the value
    name = u'???'

    def __call__(self, v):
        """ Do validation

        :param v: Input value
        :return: Sanitized value
        :raises Invalid: errors
        """
        raise NotImplementedError
