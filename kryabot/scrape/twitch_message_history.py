import dateutil.parser
from sqlalchemy.exc import IntegrityError

from api.twitchgql.TwitchGraph import TwitchGraph
from models.dao.TwitchMessage import TwitchMessage


async def replicate_messages(channel_name: str, user_id: int) -> int:
    client = TwitchGraph()
    count = 0
    cursor = None

    while True:
        content = []
        can_continue: bool = False
        responses = await client.get_message_history(channel_login=channel_name, user_id=user_id, cursor=cursor)
        for response in responses:
            if 'error' in response:
                raise ValueError(response)

            if 'data' not in response:
                raise ValueError(response)

            channel_id = int(response['data']['channel']['id'])
            can_continue = False
            for row in response['data']['channel']['modLogs']['messagesBySender']['edges']:
                if 'content' not in row['node']:
                    continue

                message_text = row['node']['content']['text']
                sender_id = int(row['node']['sender']['id'])
                sent_at = dateutil.parser.isoparse(row['node']['sentAt'])
                sent_at = sent_at.replace(tzinfo=None)
                message_id = row['node']['id']

                message = TwitchMessage(channel_id=channel_id, user_id=sender_id, message_id=message_id, text=message_text, sent_at=sent_at)
                content.append(message)
                cursor = "{}|{}".format(row['node']['sentAt'], row['node']['id'])
                can_continue = True

        if content:
            try:
                await content[0].save(content)
                count = count + len(content)
            except IntegrityError as integrityErr:
                if 'UniqueViolationError' in str(integrityErr.orig):
                    # We reached messages which we already have,
                    # but as we save in a batch, we need to go one by one now to ensure consistency
                    for item in content:
                        try:
                            await item.save()
                            count += 1
                        except IntegrityError:
                            break

                    # Now we can stop
                    can_continue = False
                else:
                    raise integrityErr

        if not can_continue:
            break

    client.logger.info("Replicted {} messages from twitch in channel {} for user {}".format(count, channel_name, user_id))
    return count
