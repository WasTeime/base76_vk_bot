import json


def main_menu_keyboard() -> str:
    kb = {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "🎁 Мои скидки"},  "color": "positive"}],
            [{"action": {"type": "text", "label": "👥 Ввести код друга"}, "color": "primary"}],
        ],
    }
    return json.dumps(kb, ensure_ascii=False)


def remove_keyboard() -> str:
    return json.dumps({"buttons": [], "one_time": True})
