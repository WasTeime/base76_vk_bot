"""
Простое in-memory хранилище состояний для VK-бота.
Ключ — vk_id пользователя, значение — название текущего состояния.
"""

_states: dict[int, str] = {}


def get_state(vk_id: int) -> str | None:
    return _states.get(vk_id)


def set_state(vk_id: int, state: str | None) -> None:
    if state is None:
        _states.pop(vk_id, None)
    else:
        _states[vk_id] = state


def clear_state(vk_id: int) -> None:
    _states.pop(vk_id, None)
