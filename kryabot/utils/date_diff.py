import dateutil


async def get_datetime_diff(datetime1, dateime2):
    return dateutil.relativedelta.relativedelta(datetime1, dateime2)


async def get_datetime_diff_text(datetime1, datetime2, lang='en', max_size=3):
    diff = await get_datetime_diff(datetime1, datetime2)

    current_size = 0
    return_string = ''

    if diff.years and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.years, await get_text('year', diff.years, lang))

    if diff.months and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.months, await get_text('month', diff.months, lang))

    if diff.days and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.days, await get_text('day', diff.days, lang))

    if diff.hours and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.hours, await get_text('hour', diff.hours, lang))

    if diff.minutes and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.minutes, await get_text('minute', diff.minutes, lang))

    if diff.seconds and current_size < max_size:
        current_size += 1
        return_string += '{} {}, '.format(diff.seconds, await get_text('second', diff.seconds, lang))

    return return_string.strip().strip(',')


async def get_text(part_type, count, lang):
    if lang == 'en':
        return await get_text_en(part_type, count)

    if lang == 'ru':
        return await get_text_ru(part_type, count)

    return await get_text_en(part_type, count)


async def get_text_ru(part_type, count):
    # TODO: RU logic
    return await get_text_en(part_type, count)


async def get_text_en(part_type, count):
    if part_type == 'year':
        return 'years' if count > 1 else 'year'

    if part_type == 'month':
        return 'months' if count > 1 else 'month'

    if part_type == 'day':
        return 'days' if count > 1 else 'day'

    if part_type == 'hour':
        return 'hours' if count > 1 else 'hour'

    if part_type == 'minute':
        return 'minutes' if count > 1 else 'minute'

    if part_type == 'second':
        return 'seconds' if count > 1 else 'second'

    return ''