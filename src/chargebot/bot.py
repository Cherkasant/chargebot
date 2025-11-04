from __future__ import annotations

import asyncio
from typing import Any

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .config import load_settings
from .db import init_db, upsert_stations
from .providers.openchargemap import fetch_nearby as ocm_fetch_nearby, normalize_record as ocm_normalize_record
from .providers.plugshare import fetch_nearby as ps_fetch_nearby, normalize_record as ps_normalize_record
from .providers.belarus_networks import fetch_nearby as by_fetch_nearby, normalize_record as by_normalize_record, add_user_station
from .utils.geo import haversine_km


def _format_station_human(st: dict[str, Any], user_lat: float, user_lon: float) -> tuple[str, InlineKeyboardMarkup]:
    d_km = haversine_km(user_lat, user_lon, st["latitude"], st["longitude"]) if user_lat and user_lon else None
    title = st.get("name") or "Зарядная станция"
    addr = st.get("address") or "—"
    oper = st.get("operator") or "—"
    power = f"≈ {st['power_kw']} кВт" if st.get("power_kw") else "—"
    status = st.get("status") or "—"
    dist = f" (~{d_km:.1f} км)" if d_km is not None else ""

    text = (
        f"⚡ <b>{title}</b>{dist}\n"
        f"🏠 Адрес: {addr}\n"
        f"🏢 Оператор: {oper}\n"
        f"🔌 Мощность: {power}\n"
        f"📊 Статус: {status}"
    )
    map_url = f"https://maps.google.com/?q={st['latitude']},{st['longitude']}"
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="🗺️ Открыть на карте", url=map_url)]]
    )
    return text, kb


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Main menu keyboard
    keyboard = [
        [KeyboardButton("🔍 Найти станции", request_location=True)],
        [KeyboardButton("🏙️ Поиск по городу"), KeyboardButton("📍 Минск")],
        [KeyboardButton("➕ Добавить станцию"), KeyboardButton("❓ Помощь")]
    ]
    kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.effective_message.reply_text(
        "🚗 <b>Зарядные станции РБ</b>\n\n"
        "Я помогу найти ближайшие электрозарядки в Беларуси!\n\n"
        "Выберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🚗 <b>Зарядные станции РБ</b>\n\n"
        "📋 <b>Команды:</b>\n"
        "/start — показать меню\n"
        "/test_minsk — протестировать поиск в Минске\n"
        "/add_station — добавить новую станцию\n\n"
        "🎯 <b>Как пользоваться:</b>\n"
        "• <b>🔍 Найти станции</b> - поделитесь геолокацией для поиска рядом\n"
        "• <b>🏙️ Поиск по городу</b> - введите название города\n"
        "• <b>📍 Минск</b> - быстрый поиск в Минске\n"
        "• <b>➕ Добавить станцию</b> - добавить недостающую станцию\n\n"
        "💡 <b>Полезно знать:</b>\n"
        "• Бот ищет станции в радиусе 50 км\n"
        "• Данные обновляются регулярно\n"
        "• Вы можете добавить недостающие станции\n\n"
        "❓ По вопросам: пишите разработчику"
    )
    await update.effective_message.reply_text(help_text, parse_mode="HTML")


async def cmd_test_minsk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command with Minsk coordinates"""
    # Mock location for Minsk center
    from telegram import Location
    mock_location = Location(latitude=53.9045, longitude=27.5615)

    # Create mock update with location
    class MockMessage:
        def __init__(self, location):
            self.location = location

        async def reply_text(self, text, **kwargs):
            await update.effective_message.reply_text(text, **kwargs)

        async def reply_html(self, text, **kwargs):
            await update.effective_message.reply_html(text, **kwargs)

    class MockUpdate:
        def __init__(self, message):
            self.effective_message = message

    mock_update = MockUpdate(MockMessage(mock_location))

    await on_location(mock_update, context)


async def cmd_add_station(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start adding a new station"""
    await update.effective_message.reply_text(
        "➕ <b>Добавление станции</b>\n\n"
        "Чтобы добавить новую зарядную станцию:\n\n"
        "1. 📍 Отправьте геолокацию станции\n"
        "2. 📝 Укажите название станции\n"
        "3. 🏢 Укажите оператора (Malanka, A-100, Белоруснефть, Частная)\n\n"
        "После добавления станция станет доступна всем пользователям!",
        parse_mode="HTML"
    )


async def on_location_for_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location when user is adding a station"""
    if not update.effective_message or not update.effective_message.location:
        return

    # Store location for later use
    context.user_data['pending_station_lat'] = update.effective_message.location.latitude
    context.user_data['pending_station_lon'] = update.effective_message.location.longitude

    await update.effective_message.reply_text(
        f"Геолокация получена: {update.effective_message.location.latitude:.6f}, {update.effective_message.location.longitude:.6f}\n\n"
        "Теперь введите название станции (например: 'Malanka ЭЗС ТЦ Галерея'):"
    )


async def on_text_for_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text input when user is adding a station"""
    if 'pending_station_lat' not in context.user_data:
        return

    text = update.message.text.strip()

    if 'pending_station_name' not in context.user_data:
        # This is the station name
        context.user_data['pending_station_name'] = text
        await update.effective_message.reply_text(
            f"Название: {text}\n\n"
            "Теперь введите оператора (например: 'Malanka', 'A-100', 'Белоруснефть' или 'Частная'):"
        )
    else:
        # This is the operator, add the station
        operator = text
        lat = context.user_data['pending_station_lat']
        lon = context.user_data['pending_station_lon']
        name = context.user_data['pending_station_name']

        # Add the station
        success = add_user_station(name, "", operator, lat, lon)

        if success:
            await update.effective_message.reply_text(
                f"✅ <b>Станция добавлена!</b>\n\n"
                f"📍 <b>{name}</b>\n"
                f"👤 <b>{operator}</b>\n"
                f"📍 Координаты: {lat:.6f}, {lon:.6f}\n\n"
                "🙏 Спасибо за вклад в развитие базы данных!\n"
                "Теперь эта станция доступна всем пользователям.",
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text("❌ Ошибка при добавлении станции. Попробуйте позже.")

        # Clear pending data
        for key in ['pending_station_lat', 'pending_station_lon', 'pending_station_name']:
            context.user_data.pop(key, None)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from menu buttons"""
    text = update.message.text

    if text == "📍 Минск":
        # Quick search for Minsk
        from telegram import Location
        mock_location = Location(latitude=53.9045, longitude=27.5615)

        # Create a proper mock message with location
        class MockMessage:
            def __init__(self, original_message, location):
                self.location = location
                # Copy other attributes from original message
                for attr in dir(original_message):
                    if not attr.startswith('_') and attr != 'location':
                        try:
                            setattr(self, attr, getattr(original_message, attr))
                        except:
                            pass

        mock_message = MockMessage(update.message, mock_location)
        mock_update = Update(update_id=update.update_id, message=mock_message)
        await on_location(mock_update, context)

    elif text == "🏙️ Поиск по городу":
        # Ask user to enter city name
        context.user_data['waiting_for_city'] = True
        await update.effective_message.reply_text(
            "🏙️ <b>Поиск по городу</b>\n\n"
            "Введите название города на русском или английском языке.\n"
            "Например: Минск, Гомель, Брест, Витебск, Могилев, Гродно",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True, one_time_keyboard=True)
        )

    elif text == "➕ Добавить станцию":
        await cmd_add_station(update, context)

    elif text == "❓ Помощь":
        await cmd_help(update, context)

    elif text == "🔍 Найти станции":
        # This button requests location, so we don't need to handle it here
        pass

    elif text == "❌ Отмена":
        # Cancel current operation
        context.user_data.clear()
        await update.effective_message.reply_text(
            "Операция отменена. Возвращаемся в главное меню.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🔍 Найти станции", request_location=True)],
                [KeyboardButton("🏙️ Поиск по городу"), KeyboardButton("📍 Минск")],
                [KeyboardButton("➕ Добавить станцию"), KeyboardButton("❓ Помощь")]
            ], resize_keyboard=True)
        )

    elif context.user_data.get('waiting_for_city'):
        # User entered a city name
        await search_by_city_name(update, context, text)

    else:
        # Check if user is in the process of adding a station
        await on_text_for_add(update, context)


async def search_by_city_name(update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str) -> None:
    """Search for charging stations by city name using geocoding"""
    # Simple geocoding for Belarusian cities
    city_coords = {
        # Major Belarusian cities
        'минск': (53.9045, 27.5615),
        'гомель': (52.4417, 30.9754),
        'брест': (52.0976, 23.7341),
        'витебск': (55.1904, 30.2049),
        'могилев': (53.9168, 30.3449),
        'гродно': (53.6694, 23.8133),
        'москва': (55.7558, 37.6176),  # For testing
        'киев': (50.4501, 30.5234),   # For testing

        # English variants
        'minsk': (53.9045, 27.5615),
        'gomel': (52.4417, 30.9754),
        'brest': (52.0976, 23.7341),
        'vitebsk': (55.1904, 30.2049),
        'mogilev': (53.9168, 30.3449),
        'grodno': (53.6694, 23.8133),
        'moscow': (55.7558, 37.6176),
        'kiev': (50.4501, 30.5234),
    }

    city_lower = city_name.lower().strip()

    if city_lower in city_coords:
        lat, lon = city_coords[city_lower]

        # Create mock location and search
        from telegram import Location
        mock_location = Location(latitude=lat, longitude=lon)

        class MockMessage:
            def __init__(self, original_message, location):
                self.location = location
                for attr in dir(original_message):
                    if not attr.startswith('_') and attr != 'location':
                        try:
                            setattr(self, attr, getattr(original_message, attr))
                        except:
                            pass

        mock_message = MockMessage(update.message, mock_location)
        mock_update = Update(update_id=update.update_id, message=mock_message)

        # Clear waiting state
        context.user_data.pop('waiting_for_city', None)

        await update.effective_message.reply_text(f"🔍 Ищу станции в городе: {city_name}")
        await on_location(mock_update, context)

    else:
        await update.effective_message.reply_text(
            f"❌ Город '{city_name}' не найден.\n\n"
            "Попробуйте ввести один из основных городов:\n"
            "🇧🇾 Минск, Гомель, Брест, Витебск, Могилев, Гродно\n"
            "🌍 Москва, Киев (для тестирования)\n\n"
            "Или нажмите '❌ Отмена' для возврата в меню.",
            reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True, one_time_keyboard=True)
        )


async def on_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.location:
        return
    user_loc = update.effective_message.location
    lat = user_loc.latitude
    lon = user_loc.longitude

    settings = context.application.bot_data["settings"]

    await update.effective_message.reply_text("🔍 Ищу ближайшие станции…")

    try:
        # Fetch from multiple providers
        all_items = []
        print(f"🔍 Fetching stations from providers (lat={lat:.4f}, lon={lon:.4f}, radius={settings.default_search_radius_km}km)...")

        # OpenChargeMap
        try:
            print("🌐 Fetching from OpenChargeMap...")
            ocm_items = await ocm_fetch_nearby(
                lat=lat,
                lon=lon,
                radius_km=settings.default_search_radius_km,
                max_results=settings.max_results,
                api_key=settings.openchargemap_api_key,
            )
            all_items.extend(ocm_items)
            print(f"✅ OpenChargeMap: {len(ocm_items)} stations")
        except Exception as e:
            print(f"❌ OpenChargeMap error: {e}")

        # PlugShare
        try:
            print("🔌 Fetching from PlugShare...")
            ps_items = await ps_fetch_nearby(
                lat=lat,
                lon=lon,
                radius_km=settings.default_search_radius_km,
                max_results=settings.max_results,
                api_key=settings.plugshare_api_key,
            )
            all_items.extend(ps_items)
            print(f"✅ PlugShare: {len(ps_items)} stations")
        except Exception as e:
            print(f"❌ PlugShare error: {e}")

        # Belarusian networks (no API key needed)
        try:
            print("🇧🇾 Fetching from Belarusian networks...")
            by_items = await by_fetch_nearby(
                lat=lat,
                lon=lon,
                radius_km=settings.default_search_radius_km,
                max_results=settings.max_results,
                api_key=None,
            )
            all_items.extend(by_items)
            print(f"✅ Belarus networks: {len(by_items)} stations")
        except Exception as e:
            print(f"❌ Belarus networks error: {e}")

        print(f"📊 Total raw stations fetched: {len(all_items)}")

        if not all_items:
            await update.effective_message.reply_text("Рядом ничего не найдено. Попробуйте увеличить радиус поиска или проверьте координаты.")
            return

    except Exception as e:
        await update.effective_message.reply_text(f"Ошибка запроса: {e}")
        return

    # Normalize all items
    normalized = []
    for item in all_items:
        try:
            if "AddressInfo" in item:  # OpenChargeMap format
                normalized.append(ocm_normalize_record(item))
            elif "stations" in item or "address" in item and isinstance(item.get("address"), dict):  # PlugShare format
                normalized.append(ps_normalize_record(item))
            else:  # Belarus networks format
                normalized.append(by_normalize_record(item))
        except Exception as e:
            print(f"Normalization error: {e}")
            continue

    # Remove duplicates by location (within 100m)
    unique_stations = []
    for station in normalized:
        is_duplicate = False
        for existing in unique_stations:
            if (abs(station["latitude"] - existing["latitude"]) < 0.001 and
                abs(station["longitude"] - existing["longitude"]) < 0.001):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_stations.append(station)

    if not unique_stations:
        await update.effective_message.reply_text("Рядом ничего не найдено. Попробуйте увеличить радиус поиска или проверьте координаты.")
        return

    normalized = unique_stations

    # Cache into SQLite (best-effort, ignore errors)
    try:
        upsert_stations(
            settings.db_url,
            (
                (
                    n["ext_id"],
                    n.get("name"),
                    n.get("address"),
                    n.get("operator"),
                    n["latitude"],
                    n["longitude"],
                    n.get("power_kw"),
                    n.get("status"),
                    n.get("last_seen_utc"),
                )
                for n in normalized
            ),
        )
    except Exception:
        pass

    if not normalized:
        await update.effective_message.reply_text(
            "🔍 <b>Станции не найдены</b>\n\n"
            "Возможные причины:\n"
            "• В этом районе пока нет зарегистрированных станций\n"
            "• Радиус поиска слишком мал (текущий: 50 км)\n"
            "• Координаты указаны неверно\n\n"
            "💡 <b>Что делать:</b>\n"
            "• Попробуйте поиск из другого места\n"
            "• Добавьте недостающую станцию через меню\n"
            "• Проверьте данные на сайтах операторов",
            parse_mode="HTML"
        )
        return

    # Send top 5 with formatting
    top = normalized[:5]
    for st in top:
        text, kb = _format_station_human(st, lat, lon)
        await update.effective_message.reply_html(text, reply_markup=kb, disable_web_page_preview=True)


async def create_application() -> Application:
    print("🔧 Loading settings...")
    settings = load_settings()
    print("✅ Settings loaded successfully")

    # Initialize DB (sqlite only) if path points to sqlite
    if settings.db_url.startswith("sqlite///") or settings.db_url.startswith("sqlite:///"):
        print("🗄️  Initializing database...")
        try:
            init_db(settings.db_url)
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"⚠️  Database initialization failed (non-critical): {e}")

    print("🤖 Creating Telegram application...")
    app = (
        Application.builder()
        .token(settings.telegram_token)
        .concurrent_updates(True)
        .build()
    )
    app.bot_data["settings"] = settings
    print("✅ Telegram application created")

    print("📡 Adding handlers...")
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("test_minsk", cmd_test_minsk))
    app.add_handler(CommandHandler("add_station", cmd_add_station))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("✅ Handlers added")

    return app


async def run_bot() -> None:
    print("🚀 Starting bot application...")
    app = await create_application()
    print("🔄 Initializing application...")
    await app.initialize()
    print("▶️  Starting application...")
    await app.start()
    print("✅ Bot started successfully!")

    # Test connection before full startup
    print("🔗 Testing Telegram connection...")
    try:
        # Test bot connection with timeout
        await asyncio.wait_for(app.bot.get_me(), timeout=10.0)
        print("✅ Telegram connection test passed")
    except asyncio.TimeoutError:
        print("❌ Telegram connection test timed out")
        raise Exception("Failed to connect to Telegram API")
    except Exception as e:
        print(f"❌ Telegram connection test failed: {e}")
        raise

    try:
        print("📡 Starting polling...")
        await app.updater.start_polling(drop_pending_updates=True)
        print("📡 Polling started, bot is running!")
        await asyncio.Event().wait()
    except Exception as e:
        print(f"❌ Error during polling: {e}")
        raise
    finally:
        print("🛑 Stopping bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("✅ Bot stopped")


if __name__ == "__main__":
    asyncio.run(run_bot())


