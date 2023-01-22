import uuid
from abc import ABC
from enum import Enum
from typing import Dict

from api.twitchv5.TopicInterface import TopicInterface
from utils.twitch import bot_auth, inject_moderator, broadcaster_auth, pagination


class ChatSetting(Enum):
    EMOTE_MODE = 'emote_mode'
    FOLLOWER_MODE = 'follower_mode'
    FOLLOWER_MODE_DURATION = 'follower_mode_duration'
    NON_MODERATOR_CHAT_DELAY = 'non_moderator_chat_delay'
    NON_MODERATOR_CHAT_DELAY_DURATION = 'non_moderator_chat_delay_duration'
    SLOW_MODE = 'slow_mode'
    SLOW_MODE_WAIT_TIME = 'slow_mode_wait_time'
    SUBSCRIBER_MODE = 'subscriber_mode'
    UNIQUE_CHAT_MODE = 'unique_chat_mode'


class Moderation(TopicInterface, ABC):
    @broadcaster_auth()
    async def check_automod_status(self, broadcaster_id: int, texts: [str], token: str):
        """
        https://dev.twitch.tv/docs/api/reference#check-automod-status

        :param broadcaster_id:
        :param texts:
        :param token:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        if not texts:
            raise ValueError('Texts must have atleast one entry')

        url = "{}moderation/enforcements/status".format(self.hostname)
        params = [("broadcaster_id", broadcaster_id)]
        headers = await self.get_json_headers(bearer_token=token)
        body = {
            "data": []
        }

        for text in texts:
            body["data"].append({"msg_id": str(uuid.uuid4()), "msg_text": text})

        response = await self.make_post_request(url=url, body=body, headers=headers, params=params)

        # Remap request with response so consumer could understand response for each requested text
        for entry in response["data"]:
            req = next(filter(lambda row: entry["msg_id"] == row["msg_id"], body["data"]))
            entry["text"] = req["msg_text"]

        return response

    @bot_auth()
    @inject_moderator()
    async def set_automod_settings(self, broadcaster_id: int, moderator_id: int, token: str, options: Dict):
        """
        https://dev.twitch.tv/docs/api/reference#update-automod-settings

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param options:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        url = "{}moderation/automod/settings".format(self.hostname)
        params = [("broadcaster_id", broadcaster_id), ("moderator_id", moderator_id)]
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_put_request(url=url, params=params, headers=headers, body=options)

    @bot_auth()
    @inject_moderator()
    async def get_automod_settings(self, broadcaster_id: int, moderator_id: int, token: str):
        """
        https://dev.twitch.tv/docs/api/reference#get-automod-settings

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        url = "{}moderation/automod/settings?broadcaster_id={}&moderator_id={}".format(self.hostname, broadcaster_id, moderator_id)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url=url, headers=headers)

    @broadcaster_auth()
    @pagination(first=100)
    async def get_banned_users(self, broadcaster_id: int, token: str, user_id: int = None, first: int = 1, after: str = None, before: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#get-banned-users

        :param broadcaster_id:
        :param user_id:
        :param token:
        :param first:
        :param after:
        :param before:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("first", first),
        ]

        if user_id:
            params.append(("user_id", user_id))

        if after:
            params.append(("after", after))
        elif before:
            params.append(("before", after))

        url = '{}moderation/banned'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url=url, params=params, headers=headers)

    @bot_auth()
    @inject_moderator()
    async def ban_user(self, broadcaster_id: int, moderator_id: int, user_id: int, duration: int = None, reason: str = None, token: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#ban-users

        :param broadcaster_id:
        :param moderator_id:
        :param user_id:
        :param duration:
        :param reason:
        :param token:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        if not user_id:
            raise ValueError('Missing user_id value!')

        action = {'user_id': user_id}

        if duration:
            # Two weeks limit, downgrade duration to avoid error 400
            duration = min(duration, 1209600)
            action['duration'] = duration

        if reason:
            # Reason can be up to 500 characters
            reason_max_length = 500
            if len(reason) > reason_max_length:
                reason = reason[0:reason_max_length - 1]
            action['reason'] = reason

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
        ]

        url = '{}moderation/bans'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        body = {'data': action}

        return await self.make_post_request(url=url, body=body, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    async def unban_user(self, broadcaster_id: int, moderator_id: int, user_id: int, token: str):
        """
        https://dev.twitch.tv/docs/api/reference#unban-user

        :param broadcaster_id:
        :param moderator_id:
        :param user_id:
        :param token:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
            ("user_id", user_id),
        ]
        url = '{}moderation/bans'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_delete_request_data(url=url, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    @pagination(first=100)
    async def get_blocked_terms(self, broadcaster_id: int, moderator_id: int, token: str, first: int = 20, after: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#get-blocked-terms

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param first:
        :param after:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
            ("first", first),
        ]
        if after:
            params.append(("after", after))

        url = '{}moderation/blocked_terms'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url=url, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    async def add_blocked_term(self, broadcaster_id: int, moderator_id: int, token: str, text: str):
        """
        https://dev.twitch.tv/docs/api/reference#add-blocked-term

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param text:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
        ]
        body = {"text": text}
        url = '{}moderation/blocked_terms'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_post_request(url=url, headers=headers, body=body, params=params)

    @bot_auth()
    @inject_moderator()
    async def remove_blocked_term(self, broadcaster_id: int, moderator_id: int, token: str, term_id: str):
        """
        https://dev.twitch.tv/docs/api/reference#remove-blocked-term

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param term_id:
        :return:
        """

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
            ("id", term_id),
        ]
        url = '{}moderation/blocked_terms'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_delete_request_data(url=url, headers=headers, params=params)

    @broadcaster_auth()
    @pagination(first=100)
    async def get_moderators(self, broadcaster_id: int, token: str, user_id: int = None, first: int = 100, after: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#get-moderators

        :param broadcaster_id:
        :param token:
        :param user_id:
        :param first:
        :param after:
        :return:
        """

        params = [
            ("broadcaster_id", broadcaster_id),
            ("first", first),
        ]

        if user_id:
            params.append(("user_id", user_id))

        if after:
            params.append(("after", after))

        url = '{}moderation/moderators'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url=url, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    @pagination()
    async def get_chatters(self, broadcaster_id: int, moderator_id: int, token: str, first: int = 100, after: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#get-chatters

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param first:
        :param after:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
            ("first", first),
        ]

        if after:
            params.append(("after", after))

        url = "{}chat/chatters".format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url=url, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    async def get_chat_settings(self, broadcaster_id: int, moderator_id: int, token: str):
        """
        https://dev.twitch.tv/docs/api/reference#get-chat-settings

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
        ]

        url = "{}chat/settings".format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url=url, headers=headers, params=params)

    @bot_auth()
    @inject_moderator()
    async def patch_chat_settings(self, broadcaster_id: int, moderator_id: int, token: str, options: Dict):
        """
        https://dev.twitch.tv/docs/api/reference#update-chat-settings

        :param broadcaster_id:
        :param moderator_id:
        :param token:
        :param options:
        :return:
        """

        if not token:
            raise ValueError('Missing token value!')

        params = [
            ("broadcaster_id", broadcaster_id),
            ("moderator_id", moderator_id),
        ]

        url = "{}chat/settings".format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_patch_request(url=url, headers=headers, params=params, body=options)
