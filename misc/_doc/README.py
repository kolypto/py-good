import good
from exdoc import doc, getmembers

import json

doccls = lambda cls, *predicates: {
    'cls': doc(cls),
    'attrs': {name: doc(m) for name, m in getmembers(cls, *predicates)}
}

data = {
    'good': doc(good),
    'Schema': doccls(good.Schema),
}


class MyJsonEncoder(json.JSONEncoder):
    def default(self, o):
        # Classes
        if isinstance(o, type):
            return o.__name__
        return super(MyJsonEncoder, self).default(o)

print json.dumps(data, indent=2, cls=MyJsonEncoder)
