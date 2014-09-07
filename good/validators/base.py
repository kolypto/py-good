import six


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

    def __repr__(self):
        return self.name

    def __str__(self):
        return six.text_type(self).encode('utf8')

    def __unicode__(self):
        return self.name

    if six.PY3:
        __bytes__, __str__ = __str__, __unicode__
