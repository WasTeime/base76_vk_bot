"""
Единый роутер VK-бота. Все входящие сообщения обрабатываются здесь.
"""
import logging
from datetime import datetime

from vkwave.bots import SimpleLongPollBot, DefaultRouter, BotEvent

from vk_bot.api_client import (
    get_user, register,
    activate_first, activate_referral, apply_ref_code,
)
from vk_bot.keyboards import main_menu_keyboard, remove_keyboard
from vk_bot.state import get_state, set_state, clear_state
from vk_bot.utils import is_valid_phone

router = DefaultRouter()
log = logging.getLogger(__name__)


async def send(bot: SimpleLongPollBot, peer_id: int, text: str, keyboard: str = None) -> None:
    kwargs = {"peer_id": peer_id, "message": text, "random_id": 0}
    if keyboard:
        kwargs["keyboard"] = keyboard
    api = bot.api_session.get_context()
    await api.messages.send(**kwargs)


def register_handlers(bot: SimpleLongPollBot) -> None:

    @router.registrar.with_decorator(
        lambda event: event.object.object.message.text is not None
    )
    async def handle_message(event: BotEvent) -> None:
        msg   = event.object.object.message
        text  = (msg.text or "").strip()
        vk_id = msg.from_id

        state = get_state(vk_id)
        user_data = await get_user(vk_id)
        registered = user_data.get("registered", False)

        # ── Незарегистрированный пользователь ─────────────────────────
        if not registered and state != "waiting_phone":
            set_state(vk_id, "waiting_phone")
            await send(
                bot, vk_id,
                "👋 Добро пожаловать в программу лояльности База 76!\n\n"
                "Введите ваш номер телефона для регистрации (например, +79001234567):",
                remove_keyboard(),
            )
            return

        # ── Ожидаем номер телефона ────────────────────────────────────
        if state == "waiting_phone":
            if not is_valid_phone(text):
                await send(
                    bot, vk_id,
                    "❌ Неверный формат номера. Введите в формате +79001234567:",
                )
                return

            try:
                user_data = await register(vk_id, text)
            except Exception as e:
                log.exception("Register failed")
                await send(
                    bot, vk_id,
                    "❌ Этот телефон уже зарегистрирован на другой аккаунт.",
                )
                return
            clear_state(vk_id)

            await send(
                bot, vk_id,
                f"✅ Вы зарегистрированы!\n\n"
                f"🎁 Вам доступна скидка 10% на первую покупку.\n"
                f"🔗 Ваш реф-код: {user_data['ref_code']}\n\n"
                f"Поделитесь кодом с друзьями — за каждого получите скидку 15%!",
                main_menu_keyboard(),
            )
            return

        # ── Главное меню ──────────────────────────────────────────────
        if text == "🎁 Мои скидки":
            has_first = user_data.get("has_first_discount", False)
            ref_count = user_data.get("friend_discounts_count", 0)

            if not has_first and ref_count == 0:
                await send(
                    bot, vk_id,
                    f"😔 У вас пока нет активных скидок.\n\n"
                    f"🔗 Поделитесь реф-кодом {user_data['ref_code']} с друзьями "
                    f"— за каждого получите скидку 15%!",
                    main_menu_keyboard(),
                )
                return

            if has_first:
                set_state(vk_id, "confirm_first_10")
                await send(
                    bot, vk_id,
                    "🎁 Скидка 10% на первую покупку\n\n"
                    "Напишите «да» чтобы активировать скидку на кассе:",
                )
                return

            if ref_count > 0:
                set_state(vk_id, "confirm_referral_15")
                await send(
                    bot, vk_id,
                    f"👥 Реферальных скидок 15%: {ref_count} шт.\n\n"
                    "Напишите «да» чтобы активировать одну скидку на кассе:",
                )
                return

        if text == "👥 Ввести код друга":
            set_state(vk_id, "waiting_ref_code")
            await send(bot, vk_id, "Введите реф-код друга (например, BRO-AB12):")
            return

        # ── Подтверждение скидок ──────────────────────────────────────
        if state == "confirm_first_10":
            clear_state(vk_id)
            if text.lower() == "да":
                ok = await activate_first(vk_id)
                if ok:
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    await send(
                        bot, vk_id,
                        f"✅ Скидка 10% активирована\n\n🕐 {now}\n\nПокажите этот экран продавцу.",
                        main_menu_keyboard(),
                    )
                else:
                    await send(bot, vk_id, "Скидка уже была использована.", main_menu_keyboard())
            else:
                await send(bot, vk_id, "Активация отменена.", main_menu_keyboard())
            return

        if state == "confirm_referral_15":
            clear_state(vk_id)
            if text.lower() == "да":
                ok = await activate_referral(vk_id)
                if ok:
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    await send(
                        bot, vk_id,
                        f"✅ Скидка 15% активирована\n\n🕐 {now}\n\nПокажите этот экран продавцу.",
                        main_menu_keyboard(),
                    )
                else:
                    await send(bot, vk_id, "Реферальных скидок не осталось.", main_menu_keyboard())
            else:
                await send(bot, vk_id, "Активация отменена.", main_menu_keyboard())
            return

        # ── Ввод реф-кода ─────────────────────────────────────────────
        if state == "waiting_ref_code":
            clear_state(vk_id)
            result = await apply_ref_code(vk_id, text)
            responses = {
                "ok":           "✅ Код принят! Вашему другу начислена скидка 15%.",
                "own_code":     "❌ Нельзя использовать собственный реф-код.",
                "not_found":    "❌ Код не найден. Проверьте правильность ввода.",
                "already_used": "❌ Вы уже использовали реф-код ранее.",
            }
            await send(bot, vk_id, responses.get(result, "Ошибка"), main_menu_keyboard())
            return

        # ── Неизвестная команда ───────────────────────────────────────
        await send(bot, vk_id, "Воспользуйтесь кнопками меню 👇", main_menu_keyboard())

    bot.dispatcher.add_router(router)
