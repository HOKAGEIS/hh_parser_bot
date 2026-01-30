from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from hh_api import hh
from config import config

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
        f"🔔 <b>Подписки</b> ({len(subs)}/{config.MAX_SUBSCRIPTIONS})\n\n"
        "Выберите подписку для управления:",
        reply_markup=kb.subscriptions_list_kb(subs),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sub_"))
async def show_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("sub_", ""))
    
    subs = await db.get_subscriptions(callback.from_user.id, active_only=False)
    
    sub = None
    for s in subs:
        if s.id == sub_id:
            sub = s
            break
    
    if not sub:
        await callback.answer("Подписка не найдена")
        return
    
    city_name = config.CITIES.get(sub.city, "Любой") if sub.city else "Любой"
    exp_name = config.EXPERIENCE.get(sub.experience, "Любой") if sub.experience else "Любой"
    schedule_name = config.SCHEDULE.get(sub.schedule, "Любой") if sub.schedule else "Любой"
    salary_text = f"от {sub.min_salary}₽" if sub.min_salary else "Любая"
    status = "🟢 Активна" if sub.active else "🔴 Приостановлена"
    
    text = (
        f"🔔 <b>Подписка #{sub.id}</b>\n\n"
        f"🔍 Запрос: <b>{sub.query}</b>\n"
        f"📍 Город: {city_name}\n"
        f"💼 Опыт: {exp_name}\n"
        f"⏰ График: {schedule_name}\n"
        f"💰 Зарплата: {salary_text}\n\n"
        f"Статус: {status}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.subscription_item_kb(sub.id, sub.active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pause_sub_"))
async def pause_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("pause_sub_", ""))
    
    await db.toggle_subscription(sub_id, callback.from_user.id)
    
    await callback.answer("⏸ Подписка приостановлена")
    
    # Обновляем отображение
    await callback.message.edit_reply_markup(
        reply_markup=kb.subscription_item_kb(sub_id, False)
    )


@router.callback_query(F.data.startswith("resume_sub_"))
async def resume_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("resume_sub_", ""))
    
    await db.toggle_subscription(sub_id, callback.from_user.id)
    
    await callback.answer("▶️ Подписка возобновлена")
    
    await callback.message.edit_reply_markup(
        reply_markup=kb.subscription_item_kb(sub_id, True)
    )


@router.callback_query(F.data.startswith("check_sub_"))
async def check_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("check_sub_", ""))
    
    subs = await db.get_subscriptions(callback.from_user.id, active_only=False)
    
    sub = None
    for s in subs:
        if s.id == sub_id:
            sub = s
            break
    
    if not sub:
        await callback.answer("Подписка не найдена")
        return
    
    await callback.answer("🔄 Проверяю...")
    
    vacancies, total = await hh.search_vacancies(
        text=sub.query,
        area=sub.city,
        experience=sub.experience,
        schedule=sub.schedule,
        salary=sub.min_salary,
        per_page=3
    )
    
    if not vacancies:
        await callback.message.answer(
            f"📭 По запросу «{sub.query}» новых вакансий не найдено"
        )
        return
    
    await callback.message.answer(
        f"🔔 Найдено {total} вакансий по запросу «{sub.query}»:\n"
    )
    
    for v in vacancies[:3]:
        await callback.message.answer(
            v.to_message(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )


@router.callback_query(F.data.startswith("delete_sub_"))
async def delete_subscription(callback: CallbackQuery):
    sub_id = int(callback.data.replace("delete_sub_", ""))
    
    await db.delete_subscription(sub_id, callback.from_user.id)
    
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
            f"🔔 <b>Подписки</b> ({len(subs)}/{config.MAX_SUBSCRIPTIONS})\n\n"
            "Выберите подписку:",
            reply_markup=kb.subscriptions_list_kb(subs),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_subs")
async def back_to_subs(callback: CallbackQuery):
    subs = await db.get_subscriptions(callback.from_user.id)
    
    await callback.message.edit_text(
        f"🔔 <b>Подписки</b> ({len(subs)}/{config.MAX_SUBSCRIPTIONS})\n\n"
        "Выберите подписку:",
        reply_markup=kb.subscriptions_list_kb(subs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "new_subscription")
async def new_subscription(callback: CallbackQuery, state: FSMContext):
    count = await db.get_subscriptions_count(callback.from_user.id)
    
    if count >= config.MAX_SUBSCRIPTIONS:
        await callback.answer(
            f"⚠️ Максимум {config.MAX_SUBSCRIPTIONS} подписок. Удалите лишние.",
            show_alert=True
        )
        return
    
    await state.set_state(SubscriptionStates.entering_query)
    
    await callback.message.edit_text(
        "🔔 <b>Новая подписка</b>\n\n"
        "Введите поисковый запрос:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SubscriptionStates.entering_query)
async def process_subscription_query(message: Message, state: FSMContext):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий")
        return
    
    user = await db.get_user(message.from_user.id)
    
    sub_id = await db.add_subscription(
        user_id=message.from_user.id,
        query=query,
        city=user.default_city if user else None,
        experience=user.default_experience if user else None
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Подписка создана!</b>\n\n"
        f"🔍 Запрос: {query}\n\n"
        f"Вы будете получать уведомления о новых вакансиях.",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )
