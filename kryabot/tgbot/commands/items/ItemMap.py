
item_map = {"egg": "🥚",
            "pumpkin": "🎃",
            "pumpkin_2021": "🎃",
            "snowball": "⚪️",
            "snowman": "⛄️"
            }
default_emote = "📦"


def get_item_emote(item_keyword):
    return item_map.get(item_keyword, default_emote)


def is_item_message(text):
    return any([x for x in item_map.keys() if text.startswith(item_map.get(x))])
