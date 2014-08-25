import good
from exdoc import doc, getmembers

import json


data = {
    'good': doc(good),
}

print json.dumps(data, indent=2)
