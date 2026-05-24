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

router = DefaultRouter()
log = logging.getLogger(__name__)


async def send(event: BotEvent, peer_id: int, text: str, keyboard: str = None) -> None:
    kwargs = {"peer_id": peer_id, "message": text, "random_id": 0}
    if keyboard:
        kwargs["keyboard"] = keyboard
    await event.api_ctx.messages.send(**kwargs)


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

        # ── Автоматическая регистрация при первом сообщении ──────────
        if not registered:
            try:
                user_data = await register(vk_id)
            except Exception:
                log.exception("Register failed")
                await send(event, vk_id, "❌ Не удалось зарегистрировать. Попробуйте позже.")
                return
            await send(
                event, vk_id,
                f"👋 Привет! Я бот программы лояльности магазина одежды База 76.\n\n"
                f"🎁 Что я умею:\n"
                f"• Дам тебе скидку 10% на первую покупку\n"
                f"• За каждого друга, который введёт твой реф-код, начислю тебе скидку 15%\n"
                f"  (друг при этом получит скидку 10% на первую покупку)\n"
                f"🔗 Твой реф-код: {user_data['ref_code']}\n\n"
                f"Нажми «🎁 Мои скидки» внизу чтобы активировать скидку 10% на кассе.",
                main_menu_keyboard(),
            )
            return

        # ── Главное меню ──────────────────────────────────────────────
        if text == "🎁 Мои скидки":
            has_first = user_data.get("has_first_discount", False)
            ref_count = user_data.get("friend_discounts_count", 0)
            active    = user_data.get("active_activation")

            lines = ["🎁 Ваши скидки:\n"]

            # Активная скидка отдельным блоком
            if active:
                import time as _t
                remaining = int(active["expires_at"] - _t.time())
                if remaining > 0:
                    h = remaining // 3600
                    m = (remaining % 3600) // 60
                    time_str = f"{h} ч {m:02d} мин" if h > 0 else f"{m} мин"
                    pct = "10%" if active["type"] == "first_10" else "15%"
                    lines.append(f"🟢 Скидка {pct} АКТИВИРОВАНА — покажите этот экран кассиру")
                    lines.append(f"   действует ещё {time_str}\n")

            if has_first:
                lines.append("✅ Скидка 10% на первую покупку — доступна")
            else:
                if not (active and active["type"] == "first_10"):
                    lines.append("☑️ Скидка 10% на первую покупку — использована")

            if ref_count > 0:
                lines.append(f"✅ Скидки 15% за друзей: {ref_count} шт.")
            else:
                if not (active and active["type"] == "referral_15"):
                    lines.append("• Скидки 15% за друзей: нет")

            if not has_first and ref_count == 0:
                lines.append(
                    f"\n🔗 Поделитесь реф-кодом {user_data['ref_code']}: "
                    f"друг получит 10% на первую покупку, вам — 15% за каждого."
                )
                await send(event, vk_id, "\n".join(lines), main_menu_keyboard())
                return

            # Есть что активировать — спрашиваем что именно
            if has_first and ref_count > 0:
                set_state(vk_id, "choose_discount")
                lines.append("\nКакую скидку активировать? Напиши «10» или «15»:")
            elif has_first:
                set_state(vk_id, "confirm_first_10")
                lines.append("\n⚠️ Активируйте только на кассе!\nНапишите «да» чтобы активировать скидку 10%:")
            else:
                set_state(vk_id, "confirm_referral_15")
                lines.append("\n⚠️ Активируйте только на кассе!\nНапишите «да» чтобы активировать одну скидку 15%:")
            await send(event, vk_id, "\n".join(lines), main_menu_keyboard())
            return

        if text == "👥 Ввести код друга":
            set_state(vk_id, "waiting_ref_code")
            await send(event, vk_id, "Введите реф-код друга (например, BRO-AB12):", main_menu_keyboard())
            return

        # Выбор скидки если доступны обе
        if state == "choose_discount":
            if text.strip() == "10":
                set_state(vk_id, "confirm_first_10")
                await send(event, vk_id, "Напишите «да» чтобы активировать скидку 10%:", main_menu_keyboard())
            elif text.strip() == "15":
                set_state(vk_id, "confirm_referral_15")
                await send(event, vk_id, "Напишите «да» чтобы активировать одну скидку 15%:", main_menu_keyboard())
            else:
                clear_state(vk_id)
                await send(event, vk_id, "Не понял. Открой «Мои скидки» снова и выбери.", main_menu_keyboard())
            return

        # ── Подтверждение скидок ──────────────────────────────────────
        if state == "confirm_first_10":
            clear_state(vk_id)
            if text.lower() == "да":
                ok = await activate_first(vk_id)
                if ok:
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    await send(
                        event, vk_id,
                        f"✅ Скидка 10% активирована\n\n🕐 {now}\n\nПокажите этот экран продавцу.",
                        main_menu_keyboard(),
                    )
                else:
                    await send(event, vk_id, "Скидка уже была использована.", main_menu_keyboard())
            else:
                await send(event, vk_id, "Активация отменена.", main_menu_keyboard())
            return

        if state == "confirm_referral_15":
            clear_state(vk_id)
            if text.lower() == "да":
                ok = await activate_referral(vk_id)
                if ok:
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    await send(
                        event, vk_id,
                        f"✅ Скидка 15% активирована\n\n🕐 {now}\n\nПокажите этот экран продавцу.",
                        main_menu_keyboard(),
                    )
                else:
                    await send(event, vk_id, "Реферальных скидок не осталось.", main_menu_keyboard())
            else:
                await send(event, vk_id, "Активация отменена.", main_menu_keyboard())
            return

        # ── Ввод реф-кода ─────────────────────────────────────────────
        if state == "waiting_ref_code":
            clear_state(vk_id)
            result = await apply_ref_code(vk_id, text)
            responses = {
                "ok":           "✅ Код принят! Вашему другу начислена скидка 15%.\n"
                                "У вас уже есть стандартная скидка 10% на первую покупку.",
                "own_code":     "❌ Нельзя использовать собственный реф-код.",
                "not_found":    "❌ Код не найден. Проверьте правильность ввода.",
                "already_used": "❌ Вы уже использовали реф-код ранее.",
            }
            await send(event, vk_id, responses.get(result, "Ошибка"), main_menu_keyboard())
            return

        # ── Неизвестная команда / приветствие ─────────────────────────
        await send(
            event, vk_id,
            f"🎁 База 76 — программа лояльности\n\n"
            f"🔗 Твой реф-код: {user_data['ref_code']}\n"
            f"📊 Скидка 10% на первую покупку: {'доступна' if user_data['has_first_discount'] else 'использована'}\n"
            f"👥 Скидок 15% накоплено: {user_data['friend_discounts_count']}\n\n"
            f"Используй кнопки внизу 👇",
            main_menu_keyboard(),
        )

    bot.dispatcher.add_router(router)
