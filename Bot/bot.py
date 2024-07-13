import asyncio

import sqlite3
from datetime import timedelta, datetime
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import sys

TOKEN = '7470088224:AAENY48ukVjlUsqiLzkf8_xPqak8rpZuYiI'

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
DATABASE_PATH = 'mydeadlines.db'
WEBDATABASE_PATH = 'db.sqlite3' # Изменяется в зависимости от конфигурации проекта


def get_db_connection(db_path):
    try:
        conn = sqlite3.connect(db_path)
        logging.debug(f"Database connection established to {db_path}.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection failed to {db_path}: {e}")
        return None


def transfer_deadlines():
    webapp_conn = get_db_connection(WEBDATABASE_PATH)
    bot_conn = get_db_connection(DATABASE_PATH)

    if not webapp_conn or not bot_conn:
        logging.error("Database connection failed. Exiting.")
        return

    webapp_cursor = webapp_conn.cursor()
    bot_cursor = bot_conn.cursor()

    webapp_cursor.execute(
        'SELECT id, your_name, your_email, title, description, due_date, "group", assigned_emails FROM mydeadline_deadline')
    deadlines = webapp_cursor.fetchall()

    for deadline in deadlines:
        id, your_name, your_email, title, description, due_date, groups, assigned_emails = deadline

        bot_cursor.execute("""
                INSERT OR REPLACE INTO Deadline (id, your_name, your_email, title, description, due_date, groups, assigned_emails)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (id, your_name, your_email, title, description, due_date, groups, assigned_emails))
        bot_conn.commit()

    webapp_conn.close()
    bot_conn.close()
    logging.info("Data transfer complete.")


async def send_notification(user_id, message):
    try:
        await bot.send_message(user_id, message)
        logging.info(f"Notification sent to {user_id}: {message}")
    except Exception as e:
        logging.error(f"Failed to send message to {user_id}: {e}")


async def check_deadlines():

    logging.info("Checking deadlines...")
    now = datetime.now()
    logging.debug(f"Current time: {now}")
    transfer_deadlines()

    conn = get_db_connection(DATABASE_PATH)
    if not conn:
        logging.error("No database connection.")
        return

    cursor = conn.cursor()

    transfer_deadlines()
    deadlines = [
        (now + timedelta(hours=24), 'осталось менее чем 24 часа'),
        (now + timedelta(days=3), 'осталось менее чем 3 дня'),
        (now + timedelta(days=7), 'осталось менее чем 7 дней')

    ]

    notified_deadlines = set()

    for due_date, time_left in deadlines:
        logging.debug(f"Checking deadlines for {time_left} (up to {due_date})")
        try:
            cursor.execute(
                "SELECT id, title, description, due_date, groups, assigned_emails FROM Deadline WHERE due_date < ? AND due_date >= ?",
                (due_date, now))
            all_deadlines = cursor.fetchall()
            logging.debug(f"Deadlines found: {all_deadlines}")

            for deadline in all_deadlines:
                deadline_id, title, description, deadline_date, groups, assigned_emails = deadline
                if (deadline_id, title, deadline_date) in notified_deadlines:
                    continue 

                for group_name in groups.split(','):
                    group_name = group_name.strip()
                    cursor.execute(
                        "SELECT userid FROM Student WHERE groupid IN (SELECT id FROM \"Group\" WHERE name = ?)",
                        (group_name,))
                    students = cursor.fetchall()
                    logging.debug(f"Students to notify in group {group_name}: {students}")

                    for student in students:
                        user_id = student[0]
                        message = f"Уведомление: До дедлайна '{title}' {time_left} ({deadline_date}).\nОписание: {description}.\nАдресант: {group_name}"
                        await send_notification(user_id, message)

                for email in assigned_emails.split(','):
                    email = email.strip()
                    cursor.execute(
                        "SELECT userid FROM Student WHERE email = ? UNION SELECT userid FROM Teacher WHERE email = ?",
                        (email, email))
                    user_result = cursor.fetchone()
                    if user_result:
                        user_id = user_result[0]
                        message = f"Уведомление: До дедлайна '{title}' {time_left} ({deadline_date}).\nОписание: {description}.\nАдресант: {email}"
                        await send_notification(user_id, message)

                notified_deadlines.add((deadline_id, title, deadline_date))

        except sqlite3.Error as e:
            logging.error(f"SQL query failed: {e}")

    conn.close()
    logging.debug("Database connection closed.")


async def periodic_check():
    while True:
        await check_deadlines()
        await asyncio.sleep(60*60*24) # Каждые 24 часа


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Зарегистрироваться"),
        BotCommand(command="menu", description="Открыть меню"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.info("Starting bot...")
    import handlers
    handlers.register_handlers(dp)
    dp.startup.register(set_commands)
    asyncio.create_task(periodic_check())
    await dp.start_polling(bot)
    await bot.session.close()
    logging.info("Bot session closed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error running main: {e}")
    finally:
        logging.info("Shutdown complete.")
