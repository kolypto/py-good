import os
from .base import ValidatorBase
from .. import Invalid


class PathExists(ValidatorBase):
    """ Verify that the path exists. """

    name = u'Existing path'

    def __init__(self):
        super(PathExists, self).__init__()

    def __call__(self, v):
        if not os.path.exists(v):
            raise Invalid(_(u'Path does not exist'), provided=u'Missing path')
        return v


class IsFile(PathExists):
    """ Verify that the file exists.

    ```python
    from good import Schema, IsFile

    schema = Schema(IsFile())

    schema('/etc/hosts')  #-> '/etc/hosts'
    schema('/etc')
    #-> Invalid: is not a file: expected Existing file path, got /etc
    ```
    """

    name = u'File path'

    def __call__(self, v):
        super(IsFile, self).__call__(v)
        if not os.path.isfile(v):
            raise Invalid(_(u'Is not a file'), provided=u'Not a file')
        return v


class IsDir(PathExists):
    """ Verify that the directory exists. """

    name = u'Directory path'

    def __call__(self, v):
        super(IsDir, self).__call__(v)
        if not os.path.isdir(v):
            raise Invalid(_(u'Is not a directory'), provided=u'Not a directory')
        return v



__all__ = ('IsFile', 'IsDir', 'PathExists',)
