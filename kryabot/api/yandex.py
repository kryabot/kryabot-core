from api.core import Core


class Yandex(Core):
    def __init__(self):
        super().__init__()
        self.history = {}
        self.max_user_history: int = 200

    async def do_yalm_bot_query(self, query: str, user_id: int):
        user_history = []
        if user_id and user_id in self.history:
            user_history = self.history[user_id]

        url = 'https://yandex.ru/lab/api/yalm/bot'
        body = {
            'history': user_history,
            'query': query
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = await self.make_post_request(url=url, body=body, headers=headers)

        if user_id not in self.history:
            self.history[user_id] = []

        if response and 'bad_query' in response and response['bad_query'] == 1:
            response['text'] = 'Извините, нейросети запретили мне говорить на подобные темы. Может, поговорим о чем-то ещё?'
            return response

        self.history[user_id].append(query)
        if response and 'text' in response:
            self.history[user_id].append(response['text'])

        if len(self.history[user_id]) > self.max_user_history:
            diff = len(self.history[user_id]) - self.max_user_history
            self.history[user_id] = self.history[user_id][diff:]

        return response
