def split_array_into_parts(arr, part_size):
    for i in range(0, len(arr), part_size):
        yield arr[i:i + part_size]


async def get_first(array):
    try:
        return array[0]
    except:
        if array is None or array == [] or array == ():
            return None
        return array