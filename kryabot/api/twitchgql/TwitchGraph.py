from typing import List, Dict

from api.core import Core


_OPERATION_HASHES = {
        'CollectionSideBar': '27111f1b382effad0b6def325caef1909c733fe6a4fbabf54f8d491ef2cf2f14',
        'FilterableVideoTower_Videos': 'a937f1d22e269e39a03b509f65a7490f9fc247d7f83d6ac1421523e3b68042cb',
        'ClipsCards__User': 'b73ad2bfaecfd30a9e6c28fada15bd97032c83ec77a0440766a56fe0bd632777',
        'ChannelCollectionsContent': '07e3691a1bad77a36aba590c351180439a40baefc1c275356f40fc7082419a84',
        'StreamMetadata': '1c719a40e481453e5c48d9bb585d971b8b372f8ebb105b17076722264dfa5b3e',
        'ComscoreStreamingQuery': 'e1edae8122517d013405f237ffcc124515dc6ded82480a88daef69c83b53ac01',
        'VideoPreviewOverlay': '3006e77e51b128d838fa4e835723ca4dc9a05c5efd4466c1085215c6e437e65c',
        'VideoMetadata': '226edb3e692509f727fd56821f5653c05740242c82b0388883e0c0e75dcbf687',
        'ViewerCardModLogsMessagesBySender': '437f209626e6536555a08930f910274528a8dea7e6ccfbef0ce76d6721c5d0e7',
    }

_OPERATION_FIELD = 'operationName'

#
# https://github.com/mauricew/twitch-graphql-api/blob/master/USAGE.md
#


class TwitchGraph(Core):
    def __init__(self):
        super().__init__()
        self.endpoint: str = "https://gql.twitch.tv/gql"
        self.clientId: str = self.cfg.getTwitchConfig()['GQL_ID']
        self.clientToken: str = self.cfg.getTwitchConfig()['GQL_TOKEN']

    async def get_message_history(self, channel_login: str, user_id: int, cursor: str = None):
        operation = {
            _OPERATION_FIELD: "ViewerCardModLogsMessagesBySender",
            "variables": {
                "senderID": str(user_id),
                "channelLogin": str(channel_login),
            },
        }

        if cursor:
            operation["variables"]["cursor"] = cursor

        return await self._make_request([operation])

    async def get_mods(self, channel_names: List[str]):
        operations = []
        for channel_name in channel_names:
            operation = {
                "query": """
                    query {
                      user(login: \"""" + channel_name + """\") {
                         mods {
                          edges {
                            node {
                              login
                            }
                          }
                        }
                      }
                    }"""
            }
            operations.append(operation)

        return await self._make_request(operations)

    async def get_stream_technical_information(self, channel_name: str):
        operation = {
            "query": """
                query {
                  user(login: "%s") {
                    stream {
                      averageFPS
                      bitrate
                      broadcasterSoftware
                      codec
                      height
                      width
                    }
                  }
                }""" % channel_name
        }

        return await self._make_request([operation])

    async def get_headers(self, oauth_token=None):
        return {"Authorization": f"OAuth {self.clientToken}", "Client-ID": self.clientId}

    async def _make_request(self, operations: List[Dict]):
        for operation in operations:
            if _OPERATION_FIELD in operation and operation[_OPERATION_FIELD] in _OPERATION_HASHES:
                operation['extensions'] = {
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': _OPERATION_HASHES[operation[_OPERATION_FIELD]],
                    }
                }

        return await self.make_post_request(url=self.endpoint, body=operations)
