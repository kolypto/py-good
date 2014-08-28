import six
from .errors import Invalid, MultipleInvalid
from .util import const


class Marker(object):
    #: Marker priority
    priority = 0

    #: The default marker error message
    error_message = None

    def __init__(self, key):
        #: The original key
        self.key = key
        #: Human-readable marker representation
        self.name = None
        #: CompiledSchema for the key
        self.key_schema = None
        #: CompiledSchema for value (if the Marker was used as a key in a mapping)
        self.value_schema = None

    def on_compiled(self, name=None, key_schema=None, value_schema=None):
        """ When CompiledSchema compiles this marker, it sets informational values onto it.

        Note that arguments may be provided in two incomplete sets,
        e.g. (name, key_schema, None) and then (None, None, value_schema).
        Thus, all assignments must be handled individually.

        It is possible that a marker may have no `value_schema` at all:
        e.g. in the case of { Extra: Reject } -- `Reject` will have no value schema,
        but `Extra` will have compiled `Reject` as the value.

        :param key_schema: Compiled key schema
        :type key_schema: CompiledSchema|None
        :param value_schema: Compiled value schema
        :type value_schema: CompiledSchema|None
        :param name: Human-friendly marker name
        :type name: unicode|None
        :rtype: Marker
        """
        if self.name is None:
            self.name = name
        if self.key_schema is None:
            self.key_schema = key_schema
        if self.value_schema is None:
            self.value_schema = value_schema

        return self

    def __repr__(self):
        return '{cls}({0})'.format(
            self.name,
            cls=type(self).__name__)

    #region Marker is a Proxy

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        # Marker equality comparison:
        #  key == key | key == Marker.key | key is Marker
        return self.key == (other.key if isinstance(other, Marker) else other) or other is type(self)

    def __str__(self):
        return six.binary_type(self.key)

    def __unicode__(self):
        return six.text_type(self.key)

    if six.PY3:
        __bytes__, __str__ = __str__, __unicode__

    #endregion

    def __call__(self, v):
        """ Validate a key using this Marker's schema """
        return self.key_schema(v)

    def execute(self, matches):
        """ Execute the marker against the input and the matching values

        :param matches: List of (input-key, sanitized-input-key, input-value) triples that matched the given marker
        :type matches: list[tuple]
        :returns: The list of matches, potentially modified
        :rtype: list[tuple]
        :raises: Invalid|MultipleInvalid
        """
        return matches  # No-op by default


#region Dictionary keys behavior

class Required(Marker):
    priority = 0
    error_message = _(u'Required key not provided')

    def execute(self, matches):
        # If a Required() key is present -- it expects to ALWAYS have one or more matches
        if not matches:
            path = [self.key] if self.key_schema.compiled_type == const.COMPILED_TYPE.LITERAL else []
            raise Invalid(self.error_message, self.name, _(u'-none-'), path)
        return matches


class Optional(Marker):
    priority = 0

    pass  # no-op


class Remove(Marker):
    priority = 1000  # We always want to remove keys prior to any other actions

    def execute(self, matches):
        # Remove all matching keys from the input
        return []


class Reject(Marker):
    priority = -50
    error_message = _(u'Value rejected')

    def execute(self, matches):
        # Complain on all values it gets
        if matches:
            errors = []
            for k, sanitized_k, v in matches:
                errors.append(Invalid(self.error_message, _(u'-none-'), six.text_type(k), [k]))
            raise MultipleInvalid.if_multiple(errors)
        return matches


class Allow(Marker):
    priority = 0

    pass  # no-op


class Extra(Marker):
    """ Catch-all marker for extra mapping keys """
    priority = -1000  # Extra should match last

    error_message = _(u'Extra keys not allowed')

    def on_compiled(self, name=None, key_schema=None, value_schema=None):
        # Special case
        # When { Extra: Reject }, use a customized error message
        if value_schema and isinstance(value_schema.compiled, Reject):
            value_schema.compiled.error_message = self.error_message
        return super(Extra, self).on_compiled(name, key_schema, value_schema)

    def execute(self, matches):
        # Delegate the decision to the value.

        # If the value is a marker -- call execute() on it
        # This is for the cases when `Extra` is mapped to a marker
        if isinstance(self.value_schema.compiled, Marker):
            return self.value_schema.compiled.execute(matches)

        # Otherwise, it's a schema, which must be called on every value to validate it.
        # However, CompiledSchema does this anyway at the next step, so doing nothing here
        return matches

#endregion

__all__ = ('Required', 'Optional', 'Remove', 'Reject', 'Allow', 'Extra')
