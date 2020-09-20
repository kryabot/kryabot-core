import json
import re
from datetime import date, datetime
from enum import Enum

import dateutil.parser


def json_to_dict(json_data):
    if json_data is None:
        return None

    return json.loads(json_data, object_hook=datetime_parser)


def dict_to_json(object):
    if object is None:
        return None

    return json.dumps(object, default=default_parser)


def default_parser(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.name
    raise TypeError("Type %s not serializable" % type(obj))


def datetime_parser(json_dict):
    for (key, value) in json_dict.items():
        if value is None:
            continue

        try:
            match = re.search(r'(^\d+-\d+-\d+)', value)
            if match.groups():
                json_dict[key] = dateutil.parser.parse(value)
        except (ValueError, AttributeError, TypeError, OverflowError):
            pass

        if isinstance(value, str) and value.isdigit():
            try:
                json_dict[key] = int(value)
            except (ValueError, AttributeError, TypeError, OverflowError):
                json_dict[key] = str(value)

    return json_dict
