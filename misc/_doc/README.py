import good, good.schema.errors, good.voluptuous
from exdoc import doc, getmembers

import json

# TODO: the whole library is Python3-compatible, but `exdoc` is not ; this file is Python2

doccls = lambda cls, *allowed_keys: {
    'cls': doc(cls),
    'attrs': {name: doc(m) for name, m in getmembers(cls, None, lambda key, value: key in allowed_keys or not key.startswith('_'))}
}

joindict = lambda *dicts: reduce(lambda memo, d: memo.update(d) or memo, dicts, {})

docmodule = lambda mod: {
    'module': doc(mod),
    'members': [ doc(getattr(mod, name)) for name in mod.__all__]
}

data = {
    'good': doc(good),
    'voluptuous': doc(good.voluptuous),

    'Schema': doccls(good.Schema, None, '__call__'),
    'errors': doc(good.schema.errors),
    'Invalid': doccls(good.Invalid),
    'MultipleInvalid': doccls(good.MultipleInvalid),
    'markers': docmodule(good.markers),

    'helpers': docmodule(good.helpers),

    'predicates': docmodule(good.validators.predicates),
    'types': docmodule(good.validators.types),
    'values': docmodule(good.validators.values),
    'boolean': docmodule(good.validators.boolean),
    'numbers': docmodule(good.validators.numbers),
    'strings': docmodule(good.validators.strings),
    'dates': docmodule(good.validators.dates),
    'files': docmodule(good.validators.files),
}

# Patches


class MyJsonEncoder(json.JSONEncoder):
    def default(self, o):
        # Classes
        if isinstance(o, type):
            return o.__name__
        return super(MyJsonEncoder, self).default(o)

print json.dumps(data, indent=2, cls=MyJsonEncoder)
