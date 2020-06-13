def get_param_value(request, param_key):
    for arg in request.query_args:
        if str(arg[0]).lower() == param_key.lower():
            return arg[1]
    return None


def get_value(key, data):
    if key in data:
        return data[key]

    return None