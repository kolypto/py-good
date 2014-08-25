
class EXTRA:
    """ Behavior constants for extra keys in a dictionary (e.g. keys that are not defined in the schema) """

    #: Fail on extra keys
    PREVENT_EXTRA = 0

    #: Allow extra keys (do not validate them)
    ALLOW_EXTRA = 1

    #: Silently remove extra keys
    REMOVE_EXTRA = 2
