# handlers/subscriptions.py (ИСПРАВЛЕНО - правильное название константы)
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
import keyboards as kb
from hh_api import hh
from config import Config  # ИСПРАВЛЕНО: импортируем класс Config, а не экземпляр

router = Router()


class SubscriptionStates(StatesGroup):
    entering_query = State()


@router.message(F.text == "🔔 Подписки")
async def show_subscriptions(message: Message):
    subs = await db.get_subscriptions(message.from_user.id)

    if not subs:
        await message.answer(
            "🔔 <b>Подписки</b>\n\n"
            "У вас пока нет подписок.\n"
            "Создайте подписку, чтобы получать уведомления о новых вакансиях.",
            reply_markup=kb.subscriptions_list_kb([]),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"🔔 <b>Подписки ({len(subs)}/{Config.MAX_SUBSCRIPTIONS_PER_USER})</b>\n\n"  # ИСПРАВЛЕНО
        "Выберите подписку для управления:",
        reply_markup=kb.subscriptions_list_kb(subs),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sub_"))
async def show_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("sub_", ""))
    subs = await db.get_subscriptions(callback.from_user.id)

    sub = None
    for s in subs:
        if s.get('id') == sub_id:
            sub = s
            break

    if not sub:
        await callback.answer("Подписка не найдена")
        return

    # Получаем данные из фильтров
    filters = sub.get('filters') or {}
    city_id = filters.get('city')
    experience = filters.get('experience')
    schedule = filters.get('schedule')
    salary = filters.get('salary')

    city_name = Config.POPULAR_CITIES.get(str(city_id), "Любой") if city_id else "Любой"
    exp_name = Config.EXPERIENCE.get(experience, "Любой") if experience else "Любой"
    schedule_name = Config.SCHEDULE.get(schedule, "Любой") if schedule else "Любой"
    salary_text = f"от {salary:,}₽".replace(',', ' ') if salary else "Любая"

    # Проверяем активность (is_active в БД)
    is_active = sub.get('is_active', True)
    status = "🟢 Активна" if is_active else "🔴 Приостановлена"

    text = (
        f"🔔 <b>Подписка #{sub_id}</b>\n\n"
        f"🔍 <b>Запрос:</b> {sub.get('query', 'Не указан')}\n"
        f"📍 <b>Город:</b> {city_name}\n"
        f"💼 <b>Опыт:</b> {exp_name}\n"
        f"⏰ <b>График:</b> {schedule_name}\n"
        f"💰 <b>Зарплата:</b> {salary_text}\n\n"
        f"<b>Статус:</b> {status}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.subscription_item_kb(sub_id, is_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pause_sub_"))
async def pause_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("pause_sub_", ""))

    # Деактивируем подписку
    success = await db.delete_subscription(sub_id)

    if success:
        await callback.answer("⏸ Подписка приостановлена")
        await callback.message.edit_reply_markup(
            reply_markup=kb.subscription_item_kb(sub_id, False)
        )
    else:
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("resume_sub_"))
async def resume_subscription(callback: CallbackQuery):
    # TODO: Добавить функцию активации подписки в database.py
    await callback.answer("⚠️ Функция в разработке", show_alert=True)


@router.callback_query(F.data.startswith("delete_sub_"))
async def delete_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("delete_sub_", ""))

    await db.delete_subscription(sub_id)
    await callback.answer("🗑 Подписка удалена")

    # Возвращаемся к списку
    subs = await db.get_subscriptions(callback.from_user.id)

    if not subs:
        await callback.message.edit_text(
            "🔔 <b>Подписки</b>\n\n"
            "У вас пока нет подписок.",
            reply_markup=kb.subscriptions_list_kb([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"🔔 <b>Подписки ({len(subs)}/{Config.MAX_SUBSCRIPTIONS_PER_USER})</b>\n\n"  # ИСПРАВЛЕНО
            "Выберите подписку:",
            reply_markup=kb.subscriptions_list_kb(subs),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_subs")
async def back_to_subs(callback: CallbackQuery):
    subs = await db.get_subscriptions(callback.from_user.id)

    await callback.message.edit_text(
        f"🔔 <b>Подписки ({len(subs)}/{Config.MAX_SUBSCRIPTIONS_PER_USER})</b>\n\n"  # ИСПРАВЛЕНО
        "Выберите подписку:",
        reply_markup=kb.subscriptions_list_kb(subs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "new_subscription")
async def new_subscription(callback: CallbackQuery, state: FSMContext):
    # Получаем количество подписок
    subs = await db.get_subscriptions(callback.from_user.id)
    count = len(subs)

    if count >= Config.MAX_SUBSCRIPTIONS_PER_USER:  # ИСПРАВЛЕНО
        await callback.answer(
            f"⚠️ Максимум {Config.MAX_SUBSCRIPTIONS_PER_USER} подписок. Удалите лишние.",  # ИСПРАВЛЕНО
            show_alert=True
        )
        return

    await state.set_state(SubscriptionStates.entering_query)

    await callback.message.edit_text(
        "🔔 <b>Новая подписка</b>\n\n"
        "Введите поисковый запрос:\n"
        "<i>Например: Python разработчик, Frontend, DevOps</i>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SubscriptionStates.entering_query)
async def process_subscription_query(message: Message, state: FSMContext):
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий (минимум 2 символа)")
        return

    # Получаем настройки пользователя
    user_settings = await db.get_user_settings(message.from_user.id)

    # Создаем подписку
    filters = {
        "city": user_settings.get("city_id"),
        "city_name": user_settings.get("city_name"),
        "experience": user_settings.get("experience"),
        "schedule": user_settings.get("schedule"),
        "salary": user_settings.get("salary_from"),
        "only_with_salary": user_settings.get("only_with_salary", False),
        "exclude_words": user_settings.get("exclude_words", []),
    }

    sub_id = await db.add_subscription(
        user_id=message.from_user.id,
        name=f"Подписка: {query[:50]}",
        query=query,
        filters=filters
    )

    await state.clear()

    if sub_id:
        await message.answer(
            f"✅ <b>Подписка создана!</b>\n\n"
            f"🔍 <b>Запрос:</b> {query}\n\n"
            f"Вы будете получать уведомления о новых вакансиях.",
            reply_markup=kb.main_menu_kb(message.from_user.id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Ошибка при создании подписки. Попробуйте позже.",
            reply_markup=kb.main_menu_kb(message.from_user.id)
        )
