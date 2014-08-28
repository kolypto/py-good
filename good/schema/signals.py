class BaseSignal(Exception):
    """ Base for internal Schema signaling """


class RemoveValue(Exception):
    """ Signal SchemaCompiler to remove this value """
