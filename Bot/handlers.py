import logging
import sqlite3
from email.message import EmailMessage
from smtplib import SMTP_SSL

from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from email_validator import validate_email, EmailNotValidError

import random

DATABASE_PATH = 'mydeadlines.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


async def send_email(recipient, subject, body):
    message = EmailMessage()
    message["From"] = "mydeadlinesHSE@yandex.ru"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        server = SMTP_SSL('smtp.yandex.ru', 465)
        server.set_debuglevel(1)
        server.login("mydeadlinesHSE@yandex.ru", "xvcmawjoscpzzyyc")
        server.send_message(message)
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()


async def cmd_start(message: types.Message):
    logging.debug("cmd_start handler called")
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Я студент 🧑‍🎓')],
            [KeyboardButton(text='Я сотрудник 🧑‍💼')]
        ],
        resize_keyboard=True
    )
    await message.answer("Здравствуйте! Пожалуйста, выберите свою должность:", reply_markup=markup)


async def register_student(message: types.Message):
    logging.debug("register_student handler called")
    await message.answer("Пожалуйста, введите свою корпоротивную почту (например: user@edu.hse.ru):")


async def register_teacher(message: types.Message):
    logging.debug("register_teacher handler called")
    await message.answer("Пожалуйста, введите свою корпоротивную почту (например: user@hse.ru):")


async def process_email(message: types.Message):
    logging.debug("process_email handler called")
    email = message.text
    user_id = message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM Student WHERE email = ? UNION SELECT email FROM Teacher WHERE email = ?",
                   (email, email))
    if cursor.fetchone():
        await message.answer("Эта почта уже зарегистрирована.")
        conn.close()
        return

    if '@' not in email:
        await message.answer("Введите почту в корректном формате.")
        conn.close()
        return
    try:
        valid = validate_email(email)
        email = valid.normalized
        if email.endswith("@edu.hse.ru") or email.endswith("@hse.ru"):
            code = str(random.randint(100000, 999999))
            await send_email(email, "Код подтверждения", f"Ваш код подтверждения: {code}")

            cursor.execute("INSERT OR REPLACE INTO EmailCodes (userid, email, code, created) VALUES (?, ?, ?, datetime('now'))",
                           (user_id, email, code))
            conn.commit()
            await message.answer(
                "Код подтверждения выслан на Вашу почту. Если Вы ввели неправильную почту, нажмите /start. Иначе, введите код:")
        else:
            await message.answer("Пожалуйста, используйте корпоративную почту.")
    except EmailNotValidError:
        await message.answer("Почта, которую Вы ввели, имеет неверный формат. Пожалуйста, попробуйте снова.")
    finally:
        conn.close()


async def process_code(message: types.Message):
    logging.debug("process_code handler called")
    code = message.text
    user_id = message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM EmailCodes WHERE userid = ? AND code = ?", (user_id, code))
    result = cursor.fetchone()
    if result:
        email = result[0]
        if email.endswith("@edu.hse.ru"):
            await message.answer("Код подтвержден. Пожалуйста, введите ФИО и группу в формате: ФИО;группа")
        elif email.endswith("@hse.ru"):
            await message.answer("Код подтвержден. Пожалуйста, введите ФИО формате: ФИО;")
    else:
        await message.answer("Неправильный код. Пожалуйста, попробуйте снова.")
    conn.close()


async def process_name_and_group(message: types.Message):
    logging.debug("process_name_and_group handler called")
    try:
        user_id = message.from_user.id
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT email FROM EmailCodes WHERE userid = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            await message.answer(
                "Неправильный код или истек срок его действия. Пожалуйста, попробуйте зарегистрироваться заново.")
            conn.close()
            return

        email = result[0]

        if email.endswith("@edu.hse.ru"):
            name, group = message.text.split(';')
            cursor.execute("SELECT id FROM \"Group\" WHERE name = ?", (group,))
            group_result = cursor.fetchone()
            if not group_result:
                cursor.execute("INSERT INTO \"Group\" (name) VALUES (?)", (group,))
                conn.commit()
                group_id = cursor.lastrowid
            else:
                group_id = group_result[0]

            cursor.execute("INSERT INTO Student (fullName, email, groupid, userid) VALUES (?, ?, ?, ?)",
                           (name, email, group_id, user_id))
            await message.answer("Вы успешно зарегистрированы как студент. Используйте /menu, чтобы посмотреть доступные команды.")

        elif email.endswith("@hse.ru"):
            name = message.text.split(';')[0]
            cursor.execute("INSERT INTO Teacher (fullName, email, userid) VALUES (?, ?, ?)", (name, email, user_id))
            await message.answer("Вы успешно зарегистрированы как сотрудник. Используйте /menu, чтобы посмотреть доступные команды.")

        conn.commit()
        cursor.execute("DELETE FROM EmailCodes WHERE userid = ?", (user_id,))
        conn.commit()
        conn.close()

    except ValueError:
        await message.answer(
            "Пожалуйста, введите информацию в корректном формате: ФИО;группа для студентов и ФИО; для сотрудников.")


async def show_menu(message: types.Message):
    logging.debug("show_menu handler called")
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM Student WHERE userid = ?", (user_id,))
    is_student = cursor.fetchone()
    cursor.execute("SELECT email FROM Teacher WHERE userid = ?", (user_id,))
    is_teacher = cursor.fetchone()
    conn.close()

    if is_student:
        markup = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Мои дедлайны')],
                [KeyboardButton(text='Моя группа')],
                [KeyboardButton(text='Поменять группу')],
                [KeyboardButton(text='Удалить учетную запись')],
            ],
            resize_keyboard=True
        )
    elif is_teacher:
        markup = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Мои дедлайны')],
                [KeyboardButton(text='Добавить дедлайн')],
                [KeyboardButton(text='Удалить учетную запись')],
            ],
            resize_keyboard=True
        )
    else:
        await message.answer("Вы не зарегистрированы. Пожалуйста, используйте /start, чтобы начать использовать бот.")
        return

    await message.answer("Ваше меню:", reply_markup=markup)


async def access_web_app(message: types.Message):
    user_id = message.from_user.id
    access_url = f"http://127.0.0.1:8000/mydeadline/"
    await message.answer(f"Вы можете добавить дедлайн на сайте: {access_url}")


async def show_deadlines(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM Student WHERE userid = ? UNION SELECT email FROM Teacher WHERE userid = ?", (user_id, user_id))
    user_email_result = cursor.fetchone()
    if user_email_result:
        user_email = user_email_result[0]
    else:
        await message.answer("Вы не зарегистрированы.")
        conn.close()
        return

    cursor.execute("SELECT groupid FROM Student WHERE userid = ?", (user_id,))
    group_result = cursor.fetchone()
    group_id = group_result[0] if group_result else None

    deadlines = []
    if group_id:
        cursor.execute("""
            SELECT title, description, due_date, groups 
            FROM Deadline 
            WHERE due_date > datetime('now')
        """)
        all_deadlines = cursor.fetchall()
        for deadline in all_deadlines:
            title, description, due_date, groups = deadline
            cursor.execute("SELECT name FROM \"Group\" WHERE id = ?", (group_id,))
            group_name = cursor.fetchone()[0]
            if group_name in groups.split(","):
                deadlines.append((title, description, due_date))

    cursor.execute("""
        SELECT title, description, due_date 
        FROM Deadline 
        WHERE assigned_emails LIKE ? 
        AND due_date > datetime('now')
    """, (f"%{user_email}%",))
    deadlines += cursor.fetchall()

    if deadlines:
        response = "\n\n".join([f"{d[0]}\nОписание: {d[1]}\nСрок выполнения: {d[2]}" for d in deadlines])
        await message.answer(response)
    else:
        await message.answer("Не найдено дедлайнов.")

    conn.close()


async def view_group_members(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT groupid FROM Student WHERE userid = ?", (user_id,))
    group_result = cursor.fetchone()
    if group_result:
        group_id = group_result[0]

        cursor.execute("SELECT name FROM \"Group\" WHERE id = ?", (group_id,))
        group_name = cursor.fetchone()[0]

        cursor.execute("SELECT fullName FROM Student WHERE groupid = ?", (group_id,))
        students = cursor.fetchall()

        if students:
            response = f"{group_name}:\n" + "\n".join([student[0] for student in students])
            await message.answer(response)
        else:
            await message.answer("Не найдено студентов в Вашей группе.")
    else:
        await message.answer("У Вас нет группы.")

    conn.close()


async def change_group(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Student WHERE userid = ?", (user_id,))
    student_result = cursor.fetchone()

    if student_result:
        await message.answer('Пожалуйста, введите новое имя группы в формате "Новая группа: ..."')
    else:
        await message.answer("Только студенты могут изменять группу.")

    conn.close()


async def process_new_group(message: types.Message):
    new_group = message.text.split("Новая группа: ")[1]
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM \"Group\" WHERE name = ?", (new_group,))
    group_result = cursor.fetchone()
    if not group_result:
        cursor.execute("INSERT INTO \"Group\" (name) VALUES (?)", (new_group,))
        conn.commit()
        group_id = cursor.lastrowid
    else:
        group_id = group_result[0]

    cursor.execute("UPDATE Student SET groupid = ? WHERE userid = ?", (group_id, user_id))
    conn.commit()
    conn.close()

    await message.answer(f"Имя Вашей группы изменено: {new_group}.")


async def delete_account(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Student WHERE userid = ?", (user_id,))
    student_result = cursor.fetchone()

    cursor.execute("SELECT * FROM Teacher WHERE userid = ?", (user_id,))
    teacher_result = cursor.fetchone()

    if student_result:
        await message.answer(
            'Вы точно хотите удалить учетную запись? Если да, напишите: Подтверждаю, удалить учетную запись.')
    elif teacher_result:
        await message.answer(
            'Вы точно хотите удалить учетную запись? Если да, напишите: Подтверждаю, удалить учетную запись.')
    else:
        await message.answer("Вы не зарегистрированы.")

    conn.close()


async def confirm_delete_account(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()


    if 'Подтверждаю, удалить учетную запись' not in message.text:
        await message.answer("Отмена удаление учетной записи.")
        return

    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Student WHERE userid = ?", (user_id,))
    cursor.execute("DELETE FROM Teacher WHERE userid = ?", (user_id,))
    conn.commit()
    conn.close()

    await message.answer("Ваша учетная запись удалена.")


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command('start'))
    dp.message.register(register_student, lambda message: message.text == 'Я студент 🧑‍🎓')
    dp.message.register(register_teacher, lambda message: message.text == 'Я сотрудник 🧑‍💼')
    dp.message.register(process_email, lambda message: '@' in message.text)
    dp.message.register(process_code, lambda message: message.text.isdigit() and len(message.text) == 6)
    dp.message.register(process_name_and_group, lambda message: ';' in message.text)
    dp.message.register(show_menu, Command('menu'))
    dp.message.register(show_deadlines, lambda message: message.text == 'Мои дедлайны')
    dp.message.register(view_group_members, lambda message: message.text == 'Моя группа')
    dp.message.register(access_web_app, lambda message: message.text == 'Добавить дедлайн')
    dp.message.register(change_group, lambda message: message.text == 'Поменять группу')
    dp.message.register(process_new_group, lambda message: 'Новая группа:' in message.text)
    dp.message.register(delete_account, lambda message: message.text == 'Удалить учетную запись')
    dp.message.register(confirm_delete_account, lambda message: "Подтверждаю, удалить учетную запись" in message.text)
