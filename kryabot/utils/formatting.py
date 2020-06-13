from utils.value_check import avoid_none


async def format_html_user_mention(tg_user):
    label = await avoid_none(tg_user.username)
    if label is None or label == '':
        label = await avoid_none(tg_user.first_name) + ' ' + await avoid_none(tg_user.last_name)
    label.strip()

    return '<a href="tg://user?id={id}">{lb}</a>'.format(id=tg_user.id, lb=label)


async def format_user_label(tg_user):
    label = await avoid_none(tg_user.username)
    if label is None or label == '':
        label = await avoid_none(tg_user.first_name) + ' ' + await avoid_none(tg_user.last_name)
    label.strip()

    return label


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)