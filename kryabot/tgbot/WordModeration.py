import re

moderation_logger = None

async def setLogger(logger):
    global moderation_logger
    moderation_logger = logger



async def letter_map(letter):
    return {
            # English to RU
            'a': u'\u0430',
            'b': u'\u0431',
            'g': u'\u0433',
            'd': u'\u0434',
            'e': u'\u0435',
            'z': u'\u0437',
            'i': u'\u0438',
            'y': u'\u0439',
            'k': u'\u043a',
            'l': u'\u043b',
            'm': u'\u043c',
            'n': u'\u043d',
            'o': u'\u043e',
            'p': u'\u043f',
            'r': u'\u0440',
            's': u'\u0441',
            't': u'\u0442',
            'u': u'\u0443',
            'f': u'\u0444',
            'v': u'\u0432',
            # Ukrainian to RU
            'і': u'\u0438',
            'ї': u'\u0438',
            'ґ': u'\u0433',
            ' ': ''
            }.get(letter, letter)


async def similar_letter_map(letter):
    return {'p': u'\u0440',
            't': u'\u0442',
            'c': u'\u0441',
            'o': u'\u043E',
            'h': u'\u043D',
            'm': u'\u043C',
            'k': u'\u043A',
            'n': u'\u0438',
            'b': u'\u0432',
            'a': u'\u0430',
            'e': u'\u0435',
            'y': u'\u0443',
            'x': u'\u0445',
            'й': u'\u0438',

            'і': u'\u0438',
            'ї': u'\u0438',
            'ґ': u'\u0433',
            '@': u'\u0430',
            ' ': ''
            }.get(letter, letter)


async def num_to_letter(letter):
    return {'1': u'\u0438',
            '3': u'\u0435',
            '4': u'\u0430',
            '5': u'\u0441',
            '0': u'\u043e',
    }.get(letter, letter)


async def num_to_letters(message):
    return await transform_message(message, num_to_letter)


async def transform_message(message, mapping):
    transformed = ''

    for ch in message:
        transformed += await mapping(ch)

    return transformed


async def remove_numbers(message):
    return ''.join(filter(lambda x: not x.isdigit(), message))


async def dbg(num, w, m):
    # moderation_logger.info(num)
    # moderation_logger.info(w.encode())
    # moderation_logger.info(m.encode())
    pass


async def check_rules(word, message)->int:
    # Default
    await dbg(1, word, message)
    if word in message:
        return 1
    await dbg(2, word, await remove_numbers(message))
    if word in (await remove_numbers(message)):
        return 2
    await dbg(3, word, await num_to_letters(message))
    if word in (await num_to_letters(message)):
        return 3
    await dbg(4, word, await remove_numbers(await num_to_letters(message)))
    if word in (await remove_numbers(await num_to_letters(message))):
        return 4
    await dbg(5, word, await remove_symbols(message))
    if word in await remove_symbols(message):
        return 5
    await dbg(6, word, await remove_symbols(await num_to_letters(message)))
    if word in await remove_symbols(await num_to_letters(message)):
        return 6
    await dbg(7, word, await remove_symbols(await num_to_letters(await remove_numbers(message))))
    if word in await remove_symbols(await num_to_letters(await remove_numbers(message))):
        return 7
    await dbg(8, word, await remove_symbols(await remove_numbers(message)))
    if word in await remove_symbols(await remove_numbers(message)):
        return 8
    await dbg(9, word, await remove_symbols(await remove_numbers(message)))
    if word in await remove_numbers(await remove_symbols(message)):
        return 9

    return 0


async def remove_symbols(message):
    return re.sub(r'[^\w]', '', message)

async def is_forbidden(word, message)->int:
    rule = await check_rules(word, message)
    if rule > 0:
        return 100 + rule

    transformed = await transform_message(message, letter_map)
    rule = await check_rules(word, transformed)
    if rule > 0:
        return 200 + rule

    transformed = await transform_message(message, similar_letter_map)
    rule = await check_rules(word, transformed)
    if rule > 0:
        return 200 + rule

    return 0