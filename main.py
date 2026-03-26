import datetime
import random
import re
import shutil
import time
import sqlite3
from pathlib import Path
import MFRC522
from lgpio import gpiochip_open, gpio_claim_output, gpio_write, gpiochip_close, gpio_claim_input, gpio_read
import telebot
from telebot import types
import threading
import cv2
import os
import face_recognition
import pickle
import warnings
import numpy as np
from AntiSpoofing.src.anti_spoof_predict import AntiSpoofPredict
from AntiSpoofing.src.generate_patches import CropImage
from AntiSpoofing.src.utility import parse_model_name
from queue import Queue
import pandas as pd
from PIL import Image
import io
warnings.filterwarnings('ignore')

script_path = os.path.abspath(__file__)
dir_path = os.path.dirname(script_path)

MIFAREReader = MFRC522.MFRC522()
chip = 4
relay = 4
led_red = 26
led_green = 16
button = 17
speaker = 13
h = gpiochip_open(chip)
gpio_claim_output(h, relay)
gpio_claim_output(h, led_red)
gpio_claim_output(h, led_green)
gpio_claim_input(h, button)
gpio_claim_output(h, speaker)
gpio_write(h, led_red, 1)


conn = sqlite3.connect(f'{dir_path}/db.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('SELECT * FROM config')
config = cursor.fetchone()
notify_bool, address_cam, distanceRecognition, page_size, frame_skip, counter_cap, speaker_notify = config
try:
    address_cam = int(address_cam)
except ValueError:
    address_cam = str(address_cam)
cap = cv2.VideoCapture(address_cam)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
frame_queue = Queue(maxsize=15)
ADMIN_ID = 0
FaceRegisterTask = False
MsgForRegisterTask = 0, {}



API_TOKEN = ''
bot = telebot.TeleBot(API_TOKEN)

admin_menu = types.InlineKeyboardMarkup(row_width = 1)
back_menu_admin_markup = types.InlineKeyboardMarkup(row_width = 1)
main_menu = types.InlineKeyboardMarkup(row_width = 1)
back_menu_markup = types.InlineKeyboardMarkup(row_width = 1)
admin_reg = types.InlineKeyboardMarkup(row_width=1)
anket_person = types.InlineKeyboardMarkup(row_width=1)
service_menu = types.InlineKeyboardMarkup(row_width=1)
close_msg_markup = types.InlineKeyboardMarkup(row_width=1)

start_reg_admin = types.InlineKeyboardButton("⚙Начать регистрацию!", callback_data='reg_admin')
open_button = types.InlineKeyboardButton("🔓Открыть дверь", callback_data='open_door')
access_code_generate = types.InlineKeyboardButton("🔑Сгенерировать код доступа", callback_data='access_code_generate')
person_verify = types.InlineKeyboardButton("⚙️Активировать пользователя в системе", callback_data='add_person')
visitor_settings = types.InlineKeyboardButton("🪪Настройки пользователей", callback_data='visitor_settings')
statistics = types.InlineKeyboardButton("📚Статистика", callback_data='statistics')
visit_history = types.InlineKeyboardButton("🔍История посещений", callback_data='visit_history')
service_settings = types.InlineKeyboardButton("🛠️Сервисные функции", callback_data='service_settings')
back_menu_admin = types.InlineKeyboardButton("🔙Вернуться в меню", callback_data='back_menu_admin')
close_msg_button = types.InlineKeyboardButton("❌Закрыть", callback_data='close_msg')
visitor_modifiers = types.InlineKeyboardButton("🛡️Настройка модификаторов доступа",
                                              callback_data='set_access_modifiers')
delete_user = types.InlineKeyboardButton('🗑️Удалить пользователя из системы', callback_data='delete_person')
on_off_notify = types.InlineKeyboardButton('💬Настройка уведомлений', callback_data='on_off_notify')
camera_change = types.InlineKeyboardButton('🎥Настройка камеры', callback_data='camera_settings')
distanceRec = types.InlineKeyboardButton('📏Настройка детекции лица в кадре', callback_data='distance_settings')
pageSize = types.InlineKeyboardButton('📖Настройка пагинации списка', callback_data='pagination_settings')
frameSkipping = types.InlineKeyboardButton('🎞️Настройка задержки видеопотока', callback_data='frameskip_settings')
counterSpoof = types.InlineKeyboardButton('🛃Настройка системы антиспуфинга', callback_data='antispoofing_settings')
speaker_config_button = types.InlineKeyboardButton('📢Настройка звукового уведомления', callback_data='speaker_settings')
delete_history = types.InlineKeyboardButton('📜Очистить историю посещений', callback_data='delete_history')
reboot_rpi = types.InlineKeyboardButton('🔄️Перезагрузить RPi', callback_data='reboot_rpi')
back_menu = types.InlineKeyboardButton("Вернуться в меню", callback_data='back_menu')

close_msg_markup.add(close_msg_button)
admin_reg.add(start_reg_admin)
admin_menu.add(open_button, access_code_generate, person_verify, visitor_settings,
               visit_history, statistics, service_settings)
back_menu_admin_markup.add(back_menu_admin)
anket_person.add(visitor_modifiers, delete_user, back_menu_admin)
service_menu.add(on_off_notify, camera_change, distanceRec,
                 pageSize, frameSkipping, counterSpoof, speaker_config_button, delete_history, reboot_rpi, back_menu_admin)

main_menu.add(open_button)
back_menu_markup.add(back_menu)



def InsertUsersDB(user_id: int, user_name: str, user_surname: str, username: str, status_verified: bool, phone_number: str):
    cursor.execute(
        'INSERT INTO users (user_id, user_name, user_surname, username, status_verified, phone_number) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, user_name, user_surname, username, status_verified, phone_number))
    conn.commit()

def InserVisitorsDB(user_id: int, surname: str, name: str, middle_name: str, person_status: str, photo: str, uid: int):
    cursor.execute(
        'INSERT INTO visitors (user_id, surname, name, middle_name, person_status, photo, uid) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (user_id, surname, name, middle_name, person_status, photo, uid))
    conn.commit()

def InsertCodeDB(code: int, date_start: object, date_end: object):
    cursor.execute(
        'INSERT INTO list_access_codes (code, start_time, end_time, used_code) VALUES (?, ?, ?, ?)',
        (code, date_start, date_end, False))
    conn.commit()

def InsertModifiersDB(user_id: int, day_of_week: str, time_start: str, time_end: str):
    cursor.execute(
        'INSERT INTO access_modifiers (user_id, day_of_week, start_time, end_time) VALUES (?, ?, ?, ?)',
        (user_id, day_of_week, time_start, time_end))
    conn.commit()

def InsertVisitHistoryDB(user_id: int, date_entry: object, successful_entry: bool, type_entry: str,
                         spoofing_attack, successful_recognition, photo_confirmation: str,
                         access_code):
    cursor.execute(
        '''INSERT INTO visit_history (user_id, date_entry, successful_entry, type_entry, spoofing_attack,
        successful_recognition, photo_confirmation,
         access_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, date_entry, successful_entry, type_entry,
        spoofing_attack, successful_recognition, photo_confirmation,
         access_code))
    conn.commit()

def CheckExistDB(user_id: int):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchall()
    return result

def GetDB(req):
    cursor.execute(req)
    return cursor.fetchone()

def SetDB(req):
    cursor.execute(req)
    conn.commit()

def GetAllID(uid):
    cursor.execute("SELECT uid FROM visitors")
    rows = cursor.fetchall()
    for row in rows:
        if str(uid) == str(row[0]):
            return False
    return True

def DoorOpen():
    gpio_write(h, led_red, 0)
    gpio_write(h, led_green, 1)
    gpio_write(h, relay, 1)
    if speaker_notify:
        gpio_write(h, speaker, 1)
        time.sleep(0.1)
        gpio_write(h, speaker, 0)
    time.sleep(5)
    gpio_write(h, relay, 0)
    gpio_write(h, led_green, 0)
    gpio_write(h, led_red, 1)
    return


def UserActivateStep0(message, call, admin):
    global FaceRegisterTask
    global MsgForRegisterTask
    info_person = {}
    try:
        if admin:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            info_person['user_id'] = message.text
            info_person['admin'] = True
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🪪Приложите карту к считывателю для её регистрации в системе.',
                                  reply_markup=back_menu_admin_markup)
            FaceRegisterTask = True
            MsgForRegisterTask = call, info_person
            return
        if not GetDB(f"SELECT status_verified FROM users WHERE user_id = {message.text}")[0]:
            bot.delete_message(chat_id = message.chat.id, message_id = message.message_id)
            info_person['user_id'] = message.text
            info_person['admin'] = False
            bot.edit_message_text(chat_id = call.message.chat.id, message_id=call.message.message_id,
                                        text = '🪪Приложите карту к считывателю для её регистрации в системе.', reply_markup=back_menu_admin_markup)
            FaceRegisterTask = True
            MsgForRegisterTask = call, info_person
        else:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Пользователь уже зарегистрирован.', reply_markup=back_menu_admin_markup)
    except TypeError:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Пользователь не найден.', reply_markup=back_menu_admin_markup)

def UserActivateStep1(MsgForRegisterTask):
    call = MsgForRegisterTask[0]
    info_person = MsgForRegisterTask[1]
    uid = info_person['uid']
    if GetAllID(uid):
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text='✍️Введите фамилию посетителя', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, UserActivateStep2, call, info_person)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="❌Данная карта уже зарегистрирована в системе!",
                              reply_markup=back_menu_admin_markup)

def UserActivateStep2(message, call, info_person):
    bot.delete_message(chat_id = message.chat.id, message_id = message.message_id)
    msg = bot.edit_message_text(chat_id = call.message.chat.id, message_id= call.message.message_id,
                                text = '✍️Введите имя посетителя', reply_markup=back_menu_admin_markup)
    info_person['user_surname'] = message.text
    bot.register_next_step_handler(msg, UserActivateStep3, call, info_person)

def UserActivateStep3(message, call, info_person):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text='✍️Введите отчество посетителя', reply_markup=back_menu_admin_markup)
    info_person['user_name'] = message.text
    bot.register_next_step_handler(msg, UserActivateStep4, call, info_person)

def UserActivateStep4(message, call, info_person):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    info_person['user_middlename'] = message.text
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='🛄Выберите статус посетителя(введите соответствующую цифру):\n'
                               '🧑‍🏫Преподаватель - 1\n'
                               '🧑‍🎓Студент - 2\n'
                               '🧑‍🔧Обслуживающий персонал - 3\n'
                               '🧑‍💻Секретарь - 4',
                                reply_markup=back_menu_admin_markup)
    bot.register_next_step_handler(msg, UserActivateStep5, call, info_person)

def UserActivateStep5(message, call, info_person):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    if message.text == '1':
        info_person['person_status'] = 'Преподаватель'
    elif message.text == '2':
        info_person['person_status'] = 'Студент'
    elif message.text == '3':
        info_person['person_status'] = 'Обслуживающий персонал'
    elif message.text == '4':
        info_person['person_status'] = 'Секретарь'
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌Введено некорректное значение из предложенных вариантов!',
                              reply_markup=back_menu_admin_markup)
        return
    msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text='🖼️Отправьте фото посетителя, для регистрации биометрии лица',
                                reply_markup=back_menu_admin_markup)
    bot.register_next_step_handler(msg, UserActivateStep6, call, info_person)


@bot.message_handler(content_types=['photo'])
def UserActivateStep6(message, call, info_person):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    Path(f'{dir_path}/files/{info_person["user_id"]}/').mkdir(parents=True, exist_ok=True)
    file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    src = f'{dir_path}/files/{info_person["user_id"]}/' + os.path.basename(file_info.file_path)
    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file)
    info_person["photo"] = src
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='🌐 Проверка корректности изорбражения...',
                          reply_markup=back_menu_admin_markup)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='💽Регистрация биометрии...',
                          reply_markup=back_menu_admin_markup)
    os.system('sudo python FaceRegister.py')
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text='✅Биометрия лица зарегистрирована!',
                                reply_markup=back_menu_admin_markup)
    time.sleep(1)
    InserVisitorsDB(info_person['user_id'], info_person['user_surname'], info_person['user_name'],
                    info_person['user_middlename'], info_person['person_status'], info_person['photo'],
                    info_person['uid'])
    SetDB(f'UPDATE users SET status_verified = 1 WHERE user_id = {info_person["user_id"]}')
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='✅Посетитель зарегистрирован в системе!',
                          reply_markup=back_menu_admin_markup)

def uidToString(uid):
    tag_str = str(hex(uid[3])[2:]) + str(hex(uid[2])[2:]) + str(hex(uid[1])[2:]) + str(hex(uid[0])[2:])
    tag = int(tag_str, 16)
    return tag

def RFIDListener():
    print('RFIDListener Started')
    global FaceRegisterTask
    global MsgForRegisterTask
    frame = None
    while True:
        try:
            if gpio_read(h, button) == 1:
                DoorOpen()
            status, TagType = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
            if status == MIFAREReader.MI_OK:
                status, uid = MIFAREReader.MFRC522_SelectTagSN()
                if status == MIFAREReader.MI_OK:
                    uid_tag = uidToString(uid)
                    MsgForRegisterTask[1]['uid'] = uid_tag
                    if FaceRegisterTask:
                        UserActivateStep1(MsgForRegisterTask)
                        FaceRegisterTask = False
                    else:
                        user_id_tuple = GetDB(f"SELECT user_id FROM visitors WHERE uid = '{uid_tag}'")
                        user_id = user_id_tuple[0] if user_id_tuple else None
                        current_datetime = datetime.datetime.now().replace(microsecond=0)
                        if not frame_queue.empty():
                            frame = frame_queue.get()
                        if user_id == None:
                            gpio_write(h, speaker, 1)
                            time.sleep(0.1)
                            gpio_write(h, speaker, 0)
                            time.sleep(0.1)
                            gpio_write(h, speaker, 1)
                            time.sleep(0.1)
                            gpio_write(h, speaker, 0)
                            Path(f'{dir_path}/photo_entry/123456/').mkdir(parents=True, exist_ok=True)
                            InsertVisitHistoryDB(123456, current_datetime, False, 'RFID-карта', True,
                                                 False, f'photo_entry/123456/{current_datetime}.png', None)
                            cv2.imwrite(f'{dir_path}/photo_entry/123456/{current_datetime}.png', frame)
                            NotifyEntry(frame, '123456', 'RFID-карта', False)
                        else:
                            if IsEntryAllowed(user_id):
                                Path(f'{dir_path}/photo_entry/{user_id}/').mkdir(parents=True, exist_ok=True)
                                cv2.imwrite(f'{dir_path}/photo_entry/{user_id}/{current_datetime}.png', frame)
                                InsertVisitHistoryDB(user_id, current_datetime, True, 'RFID-карта', False,
                                                     None, f'photo_entry/{user_id}/{current_datetime}.png', None)
                                NotifyEntry(frame, user_id, 'RFID-карта', True)
                                DoorOpen()
                            else:
                                gpio_write(h, speaker, 1)
                                time.sleep(0.1)
                                gpio_write(h, speaker, 0)
                                time.sleep(0.1)
                                gpio_write(h, speaker, 1)
                                time.sleep(0.1)
                                gpio_write(h, speaker, 0)
                    time.sleep(1.5)
        except Exception as e:
            print(f"RFID EXCEPTION: {e}")
            pass

def CheckValidDate(date):
    date = date.split('-')
    date_format = "%d.%m.%Y %H:%M"
    try:
        date_start = datetime.datetime.strptime(date[0], date_format)
        date_end = datetime.datetime.strptime(date[1], date_format)
        if date_start<date_end:
            return True, date_start, date_end
        else:
            return False, None, None
    except ValueError:
        return False, None, None

def CheckValidTime(time_start, time_end):
    try:
        time_start = datetime.datetime.strptime(time_start, "%H:%M")
        time_end = datetime.datetime.strptime(time_end, "%H:%M")
        if time_start < time_end:
            return True
    except ValueError:
        return False

def GenerateCode(message, call):
    status, date_start, date_end = CheckValidDate(message.text)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    if status:
        code = random.randint(99999, 99999999)
        InsertCodeDB(code, date_start, date_end)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='🔃Генерация кода...', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        time.sleep(1)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f'🔑Код сгенерирован: `{code}`\n📅Срок действия кода:\n🟢_{date_start}\n🔴{date_end}_', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌Временной промежуток введен в неверном формате.',
                              reply_markup=back_menu_admin_markup)

def GenerateMarkupUsersList(page_number, users_list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    start_index = page_number * page_size
    end_index = start_index + page_size

    for person in users_list[start_index:end_index]:
        button = types.InlineKeyboardButton(text=f'{person[1]} {person[2]} {person[3]}', callback_data=person[0])
        markup.add(button)

    if page_number > 0 and end_index < len(users_list):
        markup.row_width = 2
        prev_button = types.InlineKeyboardButton("⬅️ Назад", callback_data=f'prev_{page_number - 1}')
        next_button = types.InlineKeyboardButton("Вперёд ➡️", callback_data=f'next_{page_number + 1}')
        markup.add(prev_button, next_button)
    elif page_number > 0:
        markup.row_width = 1
        prev_button = types.InlineKeyboardButton("⬅️ Назад", callback_data=f'prev_{page_number-1}')
        markup.add(prev_button)
    elif end_index < len(users_list):
        markup.row_width = 1
        next_button = types.InlineKeyboardButton("Вперёд ➡️", callback_data=f'next_{page_number+1}')
        markup.add(next_button)
    markup.row_width=1
    markup.add(back_menu_admin)
    return markup

def SetModifiers(message, call, user_id):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    pattern = r"^(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье): (\d{2}:\d{2})-(\d{2}:\d{2})$"
    lines = message.text.strip().split('\n')
    schedule_dict = {}
    valid_lines_count = 0
    for line in lines:
        if line.strip():
            valid_lines_count += 1
            match = re.match(pattern, line.strip())
            if not match:
                print(f"Ошибка: строка '{line}' некорректна.")
                continue
            day, time1, time2 = match.groups()
            if not (CheckValidTime(time1, time2)):
                print(f"Ошибка: некорректное время в строке '{line}'.")
                continue
            schedule_dict[day] = {'Время1': time1, 'Время2': time2}

    all_valid = len(schedule_dict) == valid_lines_count
    if all_valid:
        SetDB(f'DELETE FROM access_modifiers WHERE user_id = {user_id}')
        for day, times in schedule_dict.items():
            start_time = times['Время1']
            end_time = times['Время2']
            InsertModifiersDB(user_id, day, start_time, end_time)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f'✅Модифкаторы доступа обновлены!',
                              parse_mode='Markdown', reply_markup=back_menu_admin_markup)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌Модификаторы доступа введены в неверном формате.',
                              reply_markup=back_menu_admin_markup)

def IsEntryAllowed(user_id):
    query = '''
    SELECT day_of_week, start_time, end_time
    FROM access_modifiers
    WHERE user_id = ?
    ORDER BY day_of_week
    '''
    cursor.execute(query, (user_id,))
    results = cursor.fetchall()
    days = {
        "Понедельник": 0,
        "Вторник": 1,
        "Среда": 2,
        "Четверг": 3,
        "Пятница": 4,
        "Суббота": 5,
        "Воскресенье": 6
    }
    now = datetime.datetime.now()
    current_day_index = now.weekday()
    current_time = now.time()


    for day, start, end in results:
        if current_day_index == days[day]:
            start_time = datetime.datetime.strptime(start, "%H:%M").time()
            end_time = datetime.datetime.strptime(end, "%H:%M").time()
            if start_time <= current_time <= end_time:
                return True
    return False


def ConvertToBase64(url):
    import base64
    try:
        with open(url, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return "File not found"

def GetHistoryFile():
    query_users = """
        SELECT 
            u.user_id, 
            IFNULL(v.surname || ' ' || v.name || ' ' || IFNULL(v.middle_name, ''), '') AS full_name, 
            u.user_name, 
            u.user_surname, 
            IFNULL(v.uid, '') AS uid, 
            u.status_verified, 
            IFNULL(v.photo, '') AS visitor_photo,
            IFNULL(u.phone_number, '') AS phone_number
        FROM 
            users u
        LEFT JOIN 
            visitors v ON u.user_id = v.user_id
        GROUP BY 
            u.user_id
        ORDER BY 
            u.status_verified DESC, v.surname, v.name, IFNULL(v.middle_name, '')
        """

    query_history = """
        SELECT 
            u.user_id, 
            IFNULL(v.surname || ' ' || v.name || ' ' || IFNULL(v.middle_name, ''), '') AS full_name, 
            vh.date_entry, 
            vh.type_entry, 
            IFNULL(vh.photo_confirmation, '') AS photo_confirmation, 
            IFNULL(vh.access_code, '') AS access_code,
            vh.successful_entry
        FROM 
            users u
        LEFT JOIN 
            visitors v ON u.user_id = v.user_id
        LEFT JOIN 
            visit_history vh ON u.user_id = vh.user_id
        """

    df_users = pd.read_sql(query_users, conn)
    df_history = pd.read_sql(query_history, conn)

    def get_photo_base64(photo_path):
        if photo_path:
            return ConvertToBase64(photo_path)
        else:
            return ConvertToBase64(f"{dir_path}/files/123456/unknown.jpg")

    df_users['visitor_photo'] = df_users['visitor_photo'].apply(get_photo_base64)
    df_history['photo_confirmation'] = df_history['photo_confirmation'].apply(get_photo_base64)

    now = datetime.datetime.now()
    start_date = (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')
    start_time = '00:00'
    end_time = '23:59'

    with open(f'{dir_path}/reportHistory.html', 'w', encoding='utf-8') as file:
        file.write("""
            <html>
            <head>
            <meta charset="utf-8">
            <title>История посещений</title>
            <style>
                img {
                    width: 100px;
                    height: 100px;
                    border: 1px solid #000;
                }
                table {
                    margin-top: 20px;
                }
            </style>
            </head>
            <body>
            <h1>История посещений</h1>
            <table border="1">
            <tr>
                <th>UserID</th>
                <th>ФИО</th>
                <th>UserName</th>
                <th>UserSurname</th>
                <th>UID</th>
                <th>Статус верификации</th>
                <th>Фото пользователя</th>
                <th>Номер телефона</th>
            </tr>
            """)

        for index, row in df_users.iterrows():
            file.write(f"<tr>")
            file.write(f"<td>{row['user_id']}</td>")
            file.write(f"<td>{row['full_name']}</td>")
            file.write(f"<td>{row['user_name']}</td>")
            file.write(f"<td>{row['user_surname']}</td>")
            file.write(f"<td>{row['uid']}</td>")
            file.write(f"<td>{'Верифицирован' if row['status_verified'] else 'Не верифицирован'}</td>")
            file.write(f"<td><img src='data:image/jpeg;base64, {row['visitor_photo']}'/></td>")
            file.write(f"<td>{row['phone_number']}</td>")
            file.write(f"</tr>")
        file.write(f"""
            </table>
            <!-- Форма для динамического запроса истории посещений -->
            <form>
                <label for="search">Поиск по User ID или ФИО:</label><br>
                <input type="text" id="search" name="search"><br>
                <label for="date_start">Начальная дата:</label>
                <input type="date" id="date_start" name="date_start" value="{start_date}"><br>
                <label for="time_start">Начальное время:</label>
                <input type="time" id="time_start" name="time_start" value="{start_time}"><br>
                <label for="date_end">Конечная дата:</label>
                <input type="date" id="date_end" name="date_end" value="{end_date}"><br>
                <label for="time_end">Конечное время:</label>
                <input type="time" id="time_end" name="time_end" value="{end_time}"><br>
                <button type="button" onclick="filterData()">Показать историю посещений</button>
            </form>
            <div id="results"></div>
            <script>
            let usersData = """ + df_users.to_json(orient="records") + """;
            let historyData = """ + df_history.to_json(orient="records") + """;

            function filterData() {
                let search = document.getElementById('search').value.toLowerCase();
                let startDate = new Date(document.getElementById('date_start').value + 'T' + document.getElementById('time_start').value);
                let endDate = new Date(document.getElementById('date_end').value + 'T' + document.getElementById('time_end').value);
                endDate.setSeconds(endDate.getSeconds() + 1); // Включение конечной даты и времени в выборку

                let filteredData = historyData.filter(item => {
                    let dateEntry = new Date(item.date_entry);
                    return (item.full_name.toLowerCase().includes(search) || item.user_id.toString().includes(search))
                           && dateEntry >= startDate && dateEntry <= endDate;
                });

                filteredData = filteredData.map(item => {
                    let user = usersData.find(u => u.user_id === item.user_id);
                    if (!user) {
                        item.full_name = ' ';
                    }
                    return item;
                });

                displayResults(filteredData);
            }

            function displayResults(filteredData) {
                let html = '<table border="1"><tr><th>User ID</th><th>ФИО</th><th>Дата входа</th><th>Тип входа</th><th>Фото подтверждения</th><th>Использованный код</th><th>Успешный вход</th></tr>';
                filteredData.forEach(item => {
                    html += '<tr><td>' + item.user_id + '</td><td>' + item.full_name + '</td><td>' + item.date_entry + '</td><td>' + item.type_entry + '</td><td><img src="data:image/jpeg;base64,' + item.photo_confirmation + '"/></td><td>' + item.access_code + '</td><td>' + (item.successful_entry ? 'Да' : 'Нет') + '</td></tr>';
                });
                html += '</table>';
                document.getElementById('results').innerHTML = html;
            }
            </script>
            </body>
            </html>
            """)

def GetStatistics():
    query = """
    SELECT
        (SELECT COUNT(*) FROM users) AS total_users,
        (SELECT COUNT(*) FROM users WHERE status_verified = 1) AS verified_users,
        (SELECT COUNT(*) FROM users WHERE status_verified = 0) AS non_verified_users,
        (SELECT COUNT(*) FROM visitors WHERE person_status = 'Студент') AS total_students,
        (SELECT COUNT(*) FROM visitors WHERE person_status = 'Преподаватель') AS total_teachers,
        (SELECT COUNT(*) FROM visitors WHERE person_status = 'Обслуживающий персонал') AS total_staff,
        (SELECT COUNT(*) FROM visitors WHERE person_status = 'Секретарь') AS total_secretaries,
        (SELECT COUNT(*) FROM list_access_codes) AS total_one_time_codes,
        (SELECT COUNT(*) FROM list_access_codes WHERE used_code = 1) AS used_one_time_codes,
        (SELECT COUNT(*) FROM list_access_codes WHERE used_code = 0) AS unused_one_time_codes,
        (SELECT COUNT(*) FROM visit_history) AS total_visit_history,
        (SELECT COUNT(*) FROM visit_history WHERE successful_entry = 1) AS successful_entries,
        (SELECT COUNT(*) FROM visit_history WHERE successful_entry = 0) AS unsuccessful_entries,
        (SELECT COUNT(*) FROM visit_history WHERE type_entry = 'RFID-карта') AS rfid_entries,
        (SELECT COUNT(*) FROM visit_history WHERE type_entry = 'Биометрия лица') AS biometric_entries,
        (SELECT COUNT(*) FROM visit_history WHERE type_entry = 'Одноразовый код') AS one_time_code_entries,
        (SELECT COUNT(*) FROM visit_history WHERE type_entry = 'Админ панель') AS admin_panel_entries,
        (SELECT COUNT(*) FROM visit_history WHERE spoofing_attack = 1) AS spoofing_attacks
    """

    cursor.execute(query)
    result = cursor.fetchone()

    (total_users, verified_users, non_verified_users, total_students, total_teachers, total_staff,
     total_secretaries, total_one_time_codes, used_one_time_codes, unused_one_time_codes, total_visit_history,
     successful_entries, unsuccessful_entries, rfid_entries, biometric_entries, one_time_code_entries,
     admin_panel_entries, spoofing_attacks) = result
    info = '📚*Статистика:*\n\n' \
           f"_Всего пользователей:_ {total_users}\n" \
           f"_Верифицированных пользователей:_ {verified_users}\n" \
           f"_Неверифицированных пользователей:_ {non_verified_users}\n" \
           f"_Всего студентов:_ {total_students}\n" \
           f"_Всего преподавателей:_ {total_teachers}\n" \
           f"_Всего обслуживающего персонала:_ {total_staff}\n" \
           f"_Всего секретарей:_ {total_secretaries}\n" \
           f"_Всего одноразовых кодов:_ {total_one_time_codes}\n" \
           f"_Использованных одноразовых кодов:_ {used_one_time_codes}\n" \
           f"_Неиспользованных одноразовых кодов:_ {unused_one_time_codes}\n" \
           f"_Записей в истории посещений:_ {total_visit_history}\n" \
           f"_Успешных входов:_ {successful_entries}\n" \
           f"_Неуспешных входов:_ {unsuccessful_entries}\n" \
           f"_Входов с RFID-картой:_ {rfid_entries}\n" \
           f"_Входов по биометрии лица:_ {biometric_entries}\n" \
           f"_Входов с помощью одноразового кода:_ {one_time_code_entries}\n" \
           f"_Входов через админ панель:_ {admin_panel_entries}\n" \
           f"_Спуффинг атак:_ {spoofing_attacks}"
    return info

def NotifySettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    if message.text == '1':
        SetDB('UPDATE config SET notify = 1')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='✅Уведомления включены!', reply_markup=back_menu_admin_markup)
    elif message.text == '0':
        SetDB('UPDATE config SET notify = 0')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='✅Уведомления выключены!', reply_markup=back_menu_admin_markup)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌Неверный ввод!', reply_markup=back_menu_admin_markup)

def SpeakerNotifySettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    if message.text == '1':
        SetDB('UPDATE config SET speaker = 1')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='✅Звуковое уведомление включено!\nПерезагрузите устройство, чтобы изменения вступили в силу!', reply_markup=back_menu_admin_markup)
    elif message.text == '0':
        SetDB('UPDATE config SET speaker = 0')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='✅Звуковое уведомление выключено!\nПерезагрузите устройство, чтобы изменения вступили в силу!', reply_markup=back_menu_admin_markup)
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌Неверный ввод!', reply_markup=back_menu_admin_markup)

def CameraSettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    SetDB(f"UPDATE config SET camera = '{message.text}'")
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='✅Настройки обновлены!\nПерезагрузите устройство, чтобы изменения вступили в силу!', reply_markup=back_menu_admin_markup)

def DistanceSettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    try:
        distance = float(message.text)
        if 0 <= distance <= 1:
            SetDB(f"UPDATE config SET distanceRecognition = {distance}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='✅ Настройки обновлены!\nПерезагрузите устройство, чтобы изменения вступили в силу!',
                                  reply_markup=back_menu_admin_markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='❌ Ошибка!\nПожалуйста, введите десятичное число от 0 до 1.',
                                  reply_markup=back_menu_admin_markup)
    except ValueError:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌ Ошибка!\nПожалуйста, введите десятичное число от 0 до 1.',
                              reply_markup=back_menu_admin_markup)

def PageSizeSettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    try:
        pagecount = int(message.text)
        if 0 < pagecount <= 10:
            SetDB(f"UPDATE config SET pageSize = {pagecount}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='✅ Настройки обновлены!\nПерезагрузите устройство, чтобы изменения вступили в силу!',
                                  reply_markup=back_menu_admin_markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='❌ Ошибка!\nПожалуйста, введите число от 1 до 10.',
                                  reply_markup=back_menu_admin_markup)
    except ValueError:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌ Ошибка!\nПожалуйста, введите число от 1 до 10.',
                              reply_markup=back_menu_admin_markup)

def FrameSkipSettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    try:
        frameskip = int(message.text)
        if 0 < frameskip <= 30:
            SetDB(f"UPDATE config SET frameSkipping = {frameskip}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='✅ Настройки обновлены!\nПерезагрузите устройство, чтобы изменения вступили в силу!',
                                  reply_markup=back_menu_admin_markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='❌ Ошибка!\nПожалуйста, введите число от 1 до 30.',
                                  reply_markup=back_menu_admin_markup)
    except ValueError:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌ Ошибка!\nПожалуйста, введите число от 1 до 30.',
                              reply_markup=back_menu_admin_markup)

def CountCapSpoofingSettings(message, call):
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    try:
        countcapspoof = int(message.text)
        if 1 < countcapspoof <= 15:
            SetDB(f"UPDATE config SET counterSpoofingCap = {countcapspoof}")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='✅ Настройки обновлены!\nПерезагрузите устройство, чтобы изменения вступили в силу!',
                                  reply_markup=back_menu_admin_markup)
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='❌ Ошибка!\nПожалуйста, введите число от 1 до 15.',
                                  reply_markup=back_menu_admin_markup)
    except ValueError:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='❌ Ошибка!\nПожалуйста, введите число от 1 до 15.',
                              reply_markup=back_menu_admin_markup)

def NotifyEntry(photo, user_id, type_entry, successfull_entry):
    if GetDB('SELECT notify FROM config')[0]:
        try:
            fio = GetDB(f'SELECT surname, name, middle_name, person_status FROM visitors WHERE user_id = {user_id}')
            surname = fio[0]
            name = fio[1]
            if user_id == '123456':
                middle_name = 'отсутствует'
            else:
                middle_name = fio[2]
            status = fio[3]
        except:
            surname='Неизвестно'
            name = 'Неизвестно'
            middle_name = 'Неизвестно'
            status = 'отсутствует'
        if successfull_entry:
            info = f'❗Уведомление о входе в кабинет!\n' \
                   f'*Фамилия:* {surname}\n*Имя:* {name}\n*Отчество:* {middle_name}\n*Должность:* {status}\n*Тип входа:* {type_entry}'
        else:
            info = f'⚠️Уведомление о попытке входе в кабинет!\n' \
                   f'*Фамилия:* {surname}\n*Имя:* {name}\n*Отчество:* {middle_name}\n*Должность:* {status}\n*Тип входа:* {type_entry}'
        photo = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(photo)
        byte_io = io.BytesIO()
        pil_image.save(byte_io, 'JPEG')
        byte_io.seek(0)
        bot.send_photo(chat_id=ADMIN_ID, photo=byte_io, caption=info,
                   parse_mode='Markdown', reply_markup=close_msg_markup)

def GetFolderSize(folder_path):
    total_size = sum(f.stat().st_size for f in Path(folder_path).rglob('*') if f.is_file())
    return total_size / (1024 * 1024)

def GetInfoDashboard(user_id):
    surname, name, middle_name, uid, person_status = GetDB(f"SELECT surname, name, middle_name, uid, person_status FROM visitors WHERE user_id = {user_id}")
    info = f'ℹ️Программно-аппаратный комплекс локальной биометрической идентификации\n\n' \
           f'🆔{user_id}\n' \
           f'🏢{person_status}\n' \
           f'🧑{surname} {name} {middle_name}\n' \
           f'🪪{uid}\n'
    cursor.execute(f'SELECT * FROM access_modifiers WHERE user_id = {user_id}')
    modifiers = cursor.fetchall()
    if modifiers == []:
        modifiers_anket = '🛡️Модификаторы доступа:\n❌Отсутствуют'
    else:
        modifiers_anket = f'🛡Модификаторы доступа:'
        modifiers_access = ''
        for day in modifiers:
            modifiers_access += f"\n🔹{day[2]}: {day[3]}-{day[4]}"
        modifiers_anket += modifiers_access
    info += modifiers_anket
    return info

def GetFaceDistance():
    frame = frame_queue.get()
    img = ResizeImage(frame, 70)
    face_locations = face_recognition.face_locations(img)
    for top, right, bottom, left in face_locations:
        face_area = (bottom - top) * (right - left)
        frame_area = img.shape[0] * img.shape[1]
        return round((face_area / frame_area), 4)

@bot.message_handler(commands=['start'])
def CommandStartHandler(message: types.Message):
    if CheckExistDB(message.from_user.id) == []:
        if message.from_user.id == ADMIN_ID:
            keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
            reg_button = types.KeyboardButton(text="📲Подтвердить номер телефона", request_contact=True)
            keyboard.add(reg_button)
            nomer = bot.send_message(message.chat.id,
                                     '⚠️Оставьте ваш контактный номер, чтобы пользоваться ботом.',
                                     reply_markup=keyboard)
            bot.register_next_step_handler(nomer, IdentificationTelegramUsers, True)
        else:
            keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
            reg_button = types.KeyboardButton(text="📲Подтвердить номер телефона", request_contact=True)
            keyboard.add(reg_button)
            nomer = bot.send_message(message.chat.id,
                                     '⚠️Оставьте ваш контактный номер, чтобы пользоваться ботом.',
                                     reply_markup=keyboard)
            bot.register_next_step_handler(nomer, IdentificationTelegramUsers, False)
    else:
        SetDB(f'UPDATE users SET active_window = 0 WHERE user_id = {message.from_user.id}')
        if message.from_user.id == ADMIN_ID:
            if GetDB(f"SELECT uid FROM visitors WHERE user_id = {ADMIN_ID}")==None:
                bot.send_message(message.chat.id,
                                       text=f"👋Здравствуйте,Вам нужно пройти первичную регистрацию в системе!",
                                       reply_markup=admin_reg)
                return
            bot.send_message(message.chat.id,
                             text=GetInfoDashboard(message.chat.id),
                             reply_markup=admin_menu)
        else:
            if GetDB(f"SELECT status_verified FROM users WHERE user_id = {message.from_user.id}")[0]:
                bot.send_message(message.chat.id,
                                 text=GetInfoDashboard(message.chat.id),
                                 reply_markup=main_menu)
            else:
                bot.send_message(message.chat.id,
                                 text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                                 parse_mode='Markdown')

def IdentificationTelegramUsers(message, admin):
    if message.contact.vcard == None:
        InsertUsersDB(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                      message.from_user.username, admin, message.contact.phone_number)
        bot.delete_message(message.chat.id, message.message_id)
        bot.delete_message(message.chat.id, message.message_id-1)
        if admin:
            bot.send_message(message.chat.id,
                             text=f"👋Здравствуйте,Вам нужно пройти первичную регистрацию в системе!",
                             reply_markup=admin_reg)
        else:
            bot.send_message(message.chat.id,
                             text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                             parse_mode='Markdown')
    else:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
        reg_button = types.KeyboardButton(text="📲Подтвердить номер телефона", request_contact=True)
        keyboard.add(reg_button)
        nomer = bot.send_message(message.chat.id,
                                 '⚠️Оставьте ваш контактный номер, чтобы пользоваться ботом.',
                                 reply_markup=keyboard)
        if message.chat.id == ADMIN_ID:
            bot.register_next_step_handler(nomer, IdentificationTelegramUsers, True)
        else:
            bot.register_next_step_handler(nomer, IdentificationTelegramUsers, False)

@bot.message_handler(content_types=['text'])
def TextMessageHandler(message):
    try:
        if not GetDB(f"SELECT status_verified FROM users WHERE user_id = {message.from_user.id}")[0]:
            try:
                code = int(message.text)
                if GetDB(f"SELECT COUNT(code) FROM list_access_codes WHERE code = {code} AND used_code = 0")[0] == 0:
                    bot.send_message(chat_id=message.chat.id, text='️❌Неверный код!', parse_mode='Markdown')
                    bot.send_message(message.chat.id,
                                     text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                                     parse_mode='Markdown')
                else:
                    interval = GetDB(f'SELECT start_time, end_time FROM list_access_codes WHERE code = {message.text}')
                    current_datetime = datetime.datetime.now().replace(microsecond=0)
                    date_format = "%Y-%m-%d %H:%M:%S"
                    if datetime.datetime.strptime(interval[1],
                                                  date_format) > current_datetime > datetime.datetime.strptime(
                            interval[0], date_format):
                        msg = bot.send_message(chat_id=message.chat.id,
                                               text='🕒Дверь откроется через 3', parse_mode='Markdown')
                        time.sleep(1)
                        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                                              text='🕕Дверь откроется через 2', parse_mode='Markdown')
                        time.sleep(1)
                        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                                              text='🕘Дверь откроется через 1', parse_mode='Markdown')
                        time.sleep(1)
                        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                                              text='🕛Дверь откроется через 0', parse_mode='Markdown')
                        time.sleep(0.5)
                        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                                              text='🔓🚪Дверь открыта на 5 секунд!', parse_mode='Markdown')
                        current_datetime = datetime.datetime.now().replace(microsecond=0)
                        if not frame_queue.empty():
                            frame = frame_queue.get()
                            Path(f'{dir_path}/photo_entry/{message.chat.id}/').mkdir(parents=True, exist_ok=True)
                            cv2.imwrite(f'{dir_path}/photo_entry/{message.chat.id}/{current_datetime}.png', frame)
                            NotifyEntry(frame, message.chat.id, 'Одноразовый код', True)
                        InsertVisitHistoryDB(message.chat.id, current_datetime, True, 'Одноразовый код', False,
                                             False, f'photo_entry/{message.chat.id}/{current_datetime}.png',
                                             message.text)
                        DoorOpen()
                        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                                              text='🔒🚪Дверь закрыта!', parse_mode='Markdown')
                        SetDB(
                            f'UPDATE list_access_codes SET used_code = 1 WHERE code = {message.text} AND used_code = 0')
                        time.sleep(1.5)
                        bot.send_message(message.chat.id,
                                         text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                                         parse_mode='Markdown')
                    else:
                        bot.send_message(chat_id=message.chat.id,
                                         text='️❌Код либо просрочен, либо еще не вступил в срок действия!',
                                         parse_mode='Markdown')
                        bot.send_message(message.chat.id,
                                         text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                                         parse_mode='Markdown')
            except:
                bot.send_message(chat_id=message.chat.id, text='️❌Неверный код!', parse_mode='Markdown')
                bot.send_message(message.chat.id,
                                 text=f"🔐*Для входа в кабинет* - _введите одноразовый код доступа, полученный от администратора!_\n\n🖥️*Для получения доступа в панель управления* - _передайте администратору данный код:_ `{message.chat.id}`",
                                 parse_mode='Markdown')
        else:
            bot.delete_message(message.chat.id, message.message_id)
    except TypeError:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
        reg_button = types.KeyboardButton(text="📲Подтвердить номер телефона", request_contact=True)
        keyboard.add(reg_button)
        nomer = bot.send_message(message.chat.id,
                                 '⚠️Оставьте ваш контактный номер, чтобы пользоваться ботом.',
                                 reply_markup=keyboard)
        bot.register_next_step_handler(nomer, IdentificationTelegramUsers, False)


@bot.callback_query_handler(func=lambda call: True)
def CallbackHandler(call):
    if call.data == 'add_person':
        msg = bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id, text = '🆔Введите userID регистрируемого пользователя', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, UserActivateStep0, call, False)
        return
    if call.data == 'reg_admin':
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'🆔Введите userID регистрируемого пользователя(ваш userID - `{call.message.chat.id}`)',
                                    parse_mode='Markdown')
        bot.register_next_step_handler(msg, UserActivateStep0, call, True)
        return
    if call.data == 'back_menu_admin':
        if GetDB(f"SELECT uid FROM visitors WHERE user_id = {ADMIN_ID}") == None:
            bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id,
                             text=f"👋Здравствуйте,Вам нужно пройти первичную регистрацию в системе!",
                             reply_markup=admin_reg)
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            return
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        SetDB(f'UPDATE users SET active_window = 0 WHERE user_id = {call.message.chat.id}')
        bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id,
                         text=GetInfoDashboard(call.message.chat.id),
                         reply_markup=admin_menu)
        return
    if call.data == 'access_code_generate':
        current_datetime = datetime.datetime.now().replace(microsecond=0)
        one_day = datetime.timedelta(days=1)
        today_datetime = current_datetime + one_day
        date_today = current_datetime.strftime("%d.%m.%Y %H:%M")
        date_tomorrow = today_datetime.strftime("%d.%m.%Y %H:%M")
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'✍️Введите временной промежуток срока действия одноразового кода в формате:\n`{date_today}-{date_tomorrow}`',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, GenerateCode, call)
        return
    if call.data.startswith('next_') or call.data.startswith('prev_'):
        page_number = int(call.data.split('_')[1])
        cursor.execute('SELECT user_id, surname, name, middle_name FROM visitors')
        users_list = cursor.fetchall()
        markup = GenerateMarkupUsersList(page_number, users_list)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"👥Выберите пользователя:\n📖Страница {page_number+1}", reply_markup=markup)
        return
    if call.data == 'visitor_settings':
        cursor.execute('SELECT user_id, surname, name, middle_name FROM visitors WHERE uid != 123456')
        users_list = cursor.fetchall()
        markup = GenerateMarkupUsersList(0, users_list)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"👥Выберите пользователя:\n📖Страница 1", reply_markup=markup)
        return
    if call.data == 'set_access_modifiers':
        user_id = GetDB(f"SELECT active_window FROM users WHERE user_id = {call.message.chat.id}")[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text='✍️Введите модификаторы доступа в формате:\n`'
                                         'Понедельник: 00:00-23:59\n'
                                         'Вторник: 00:00-23:59\n'
                                         'Среда: 00:00-23:59\n'
                                         'Четверг: 00:00-23:59\n'
                                         'Пятница: 00:00-23:59\n'
                                         'Суббота: 00:00-23:59\n'
                                         'Воскресенье: 00:00-23:59`\n\n'
                                         '❗При отсутствии одного из дней недели - доступ в этот день будет запрещён!', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, SetModifiers, call, user_id)
        return
    if call.data == 'delete_person':
        user_id = GetDB(f"SELECT active_window FROM users WHERE user_id = {call.message.chat.id}")[0]
        SetDB(f'DELETE FROM visitors WHERE user_id = {user_id}')
        SetDB(f'DELETE FROM access_modifiers WHERE user_id = {user_id}')
        SetDB(f'DELETE FROM visit_history WHERE user_id = {user_id}')
        SetDB(f'UPDATE users SET status_verified = 0 WHERE user_id = {user_id}')
        file_path = os.path.join(f'{dir_path}/photo_entry/', str(user_id))
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            elif os.path.isfile(file_path):
                os.unlink(file_path)
        except:
            pass
        file_path2 = os.path.join(f'{dir_path}/files/', str(user_id))
        try:
            if os.path.isdir(file_path2):
                shutil.rmtree(file_path2)
            elif os.path.isfile(file_path2):
                os.unlink(file_path2)
        except:
            pass
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='💽Обновляю файл биометрии...',
                              reply_markup=back_menu_admin_markup)
        os.system('sudo python FaceRegister.py')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='✅Пользователь успешно удален!', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        return
    if call.data == 'open_door':
        global frame
        if IsEntryAllowed(call.message.chat.id):
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🕒Дверь откроется через 3', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
            time.sleep(1)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🕕Дверь откроется через 2', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
            time.sleep(1)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🕘Дверь откроется через 1', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
            time.sleep(1)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🕛Дверь откроется через 0', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
            time.sleep(0.5)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🔓🚪Дверь открыта на 5 секунд!', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
            current_datetime = datetime.datetime.now().replace(microsecond=0)
            if not frame_queue.empty():
                frame = frame_queue.get()
                Path(f'{dir_path}/photo_entry/{call.message.chat.id}/').mkdir(parents=True, exist_ok=True)
                cv2.imwrite(f'{dir_path}/photo_entry/{call.message.chat.id}/{current_datetime}.png', frame)
                NotifyEntry(frame, call.message.chat.id, 'Админ панель', True)
            InsertVisitHistoryDB(call.message.chat.id, current_datetime, True, 'Админ панель', False,
                                 False, f'photo_entry/{call.message.chat.id}/{current_datetime}.png', None)
            DoorOpen()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='🔒🚪Дверь закрыта!', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
        else:
            gpio_write(h, speaker, 1)
            time.sleep(0.1)
            gpio_write(h, speaker, 0)
            time.sleep(0.1)
            gpio_write(h, speaker, 1)
            time.sleep(0.1)
            gpio_write(h, speaker, 0)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='❌Доступ в данный момент запрещён!', parse_mode='Markdown',
                                  reply_markup=back_menu_admin_markup)
        return
    if call.data == 'visit_history':
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='⏳Формирую файл...', parse_mode='Markdown',
                              reply_markup=back_menu_admin_markup)
        GetHistoryFile()
        with open(f'{dir_path}/reportHistory.html', 'rb') as file:
            bot.send_document(chat_id=call.message.chat.id, document=file, caption = '✅Файл с историей посещений.', reply_markup=close_msg_markup)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(chat_id = call.message.chat.id,
                         text=GetInfoDashboard(call.message.chat.id),
                         reply_markup=admin_menu)
        return
    if call.data == 'close_msg':
        bot.delete_message(chat_id=call.message.chat.id,
                           message_id=call.message.message_id)
        return
    if call.data == 'statistics':
        info = GetStatistics()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=info, parse_mode='Markdown',
                              reply_markup=back_menu_admin_markup)
        return
    if call.data == 'service_settings':
        size = round(GetFolderSize(f'{dir_path}/photo_entry'), 1)
        total, used, free = shutil.disk_usage('/')
        free = round(free / (1024 * 1024), 1)
        total = round(total / (1024*1024), 1)
        info = f'🛠️Сервисное меню\n' \
               f'📀Занятое пространство фото-логированием: {size} МБ\n' \
               f'💿Память хранилища(свободно): {free}/{total} МБ'
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=info, parse_mode='Markdown', reply_markup=service_menu)
        return
    if call.data == 'on_off_notify':
        notify = GetDB('SELECT notify FROM config')[0]
        if notify:
            notify = 'включены'
        else:
            notify = 'отключены'
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f'🎵Текущее состояние: уведомления {notify}\nВведите: 1 - чтобы включить уведомления\n 0 - чтобы выключить уведомления', parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, NotifySettings, call)
        return
    if call.data == 'delete_history':
        SetDB('DELETE FROM visit_history')
        for filename in os.listdir(f'{dir_path}/photo_entry/'):
            file_path = os.path.join(f'{dir_path}/photo_entry/', filename)
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                elif os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f'✅История посещений удалена!',
                              parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        return
    if call.data == 'reboot_rpi':
        os.system('sudo reboot')
        return
    if call.data == 'camera_settings':
        camera = GetDB('SELECT camera FROM config')[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'🎥Текущий адрес камеры: `{camera}`\n'
                                         f'Введите новый адрес камеры, либо индекс подключенной USB-камеры',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, CameraSettings, call)
        return
    if call.data == 'distance_settings':
        distance = GetDB('SELECT distanceRecognition FROM config')[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'📏Текущий коэфициент детектирования лица: `{GetFaceDistance()}`\n'
                                         f'📏Текущий коэфициент детектирования лица в конфиге: `{distance}`\n'
                                         f'Введите новое значение коэфициента от 0 до 0.99',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, DistanceSettings, call)
        return
    if call.data == 'pagination_settings':
        pageCount = GetDB('SELECT pageSize FROM config')[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'📖Текущее количество записей списка на одной странице: `{pageCount}`\n'
                                         f'Введите новое значение',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, PageSizeSettings, call)
        return
    if call.data == 'frameskip_settings':
        framecount = GetDB('SELECT frameSkipping FROM config')[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'🎞️Текущие значение пропуска кадров: `{framecount}`\n'
                                         f'Введите новое значение',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, FrameSkipSettings, call)
        return
    if call.data == 'antispoofing_settings':
        framecount = GetDB('SELECT counterSpoofingCap FROM config')[0]
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'🛃Текущие значение кадров для проверки системой антиспуфинга: `{framecount}`\n'
                                         f'Введите новое значение',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, CountCapSpoofingSettings, call)
        return
    if call.data == 'speaker_settings':
        notify = GetDB('SELECT speaker FROM config')[0]
        if notify:
            notify = 'включено'
        else:
            notify = 'отключено'
        msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=f'🎵Текущее состояние: звуковое уведомление {notify}\nВведите: 1 - чтобы включить звуковое уведомление\n 0 - чтобы выключить звуковое уведомление',
                                    parse_mode='Markdown', reply_markup=back_menu_admin_markup)
        bot.register_next_step_handler(msg, SpeakerNotifySettings, call)
        return
    else:
        info = GetDB(f'SELECT * FROM visitors WHERE user_id = {call.data}')
        phone_number = GetDB(f'SELECT phone_number FROM users WHERE user_id = {call.data}')[0]
        info_anket = f'🆔{info[1]}\n🪪{info[2]} {info[3]} {info[4]}\n🏢{info[5]}\n💳{info[7]}\n📱{phone_number}\n\n'
        cursor.execute(f'SELECT * FROM access_modifiers WHERE user_id = {call.data}')
        modifiers = cursor.fetchall()
        if modifiers == []:
            modifiers_anket = '🛡️Модификаторы доступа:\n❌Отсутствуют'
        else:
            modifiers_anket = f'🛡Модификаторы доступа:'
            modifiers_access = '`'
            for day in modifiers:
                modifiers_access += f"\n{day[2]}: {day[3]}-{day[4]}"
            modifiers_access += '`'
            modifiers_anket += modifiers_access
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text = f'{info_anket+modifiers_anket}', parse_mode='Markdown', reply_markup=anket_person)
        SetDB(f'UPDATE users SET active_window = {call.data} WHERE user_id = {call.message.chat.id}')
        return

def MainLoop():
    if GetDB("SELECT COUNT(user_id) FROM users WHERE user_id = 123456")[0]==0:
        InsertUsersDB(123456, 'Неизвестная', 'Личность', '', False, '987654321')
        InserVisitorsDB(123456, 'Неизвестная', 'Личность', '', 'Бот', 'files/123456/unknown.jpg', 123456)
    else:
        pass
    print('Bot Started')
    while True:
        try:
            bot.infinity_polling()
        except:
            time.sleep(5)

def isPathOrFrame(variable):
    if isinstance(variable, str):
        return True
    elif isinstance(variable, np.ndarray):
        return False

def FaceRecognition(img):
    data = pickle.loads(open(f'{dir_path}/face_enc', "rb").read())
    if isPathOrFrame(img):
        img = cv2.imread(img)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb)
    for encoding in encodings:
        matches = face_recognition.compare_faces(data["encodings"],
                                                 encoding)
        name = "Unknown"
        if True in matches:
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}
            for i in matchedIdxs:
                name = data["names"][i]
                counts[name] = counts.get(name, 0) + 1
                name = max(counts, key=counts.get)
        return name

def SpoofingChecker(image, model_dir, device_id):
    model_test = AntiSpoofPredict(device_id)
    image_cropper = CropImage()
    image_bbox = model_test.get_bbox(image)
    prediction = np.zeros((1, 3))
    test_speed = 0
    for model_name in os.listdir(model_dir):
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": image,
            "bbox": image_bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False
        img = image_cropper.crop(**param)
        start = time.time()
        prediction += model_test.predict(img, os.path.join(model_dir, model_name))
        test_speed += time.time()-start

    label = np.argmax(prediction)
    value = prediction[0][label]/2
    if label == 1:
        print("Real. Score: {:.2f}.".format(value))
        return True
    else:
        print("Fake. Score: {:.2f}.".format(value))
        return False

def SpoofingAttackCheck():
    if not frame_queue.empty():
        frame = frame_queue.get()
        cap_real = 0
        cap_fake = 0
        counter_cap_live = 0
        while counter_cap_live<counter_cap:
            if SpoofingChecker(frame, f"{dir_path}/AntiSpoofing/resources/anti_spoof_models", 0):
                cap_real += 1
            else:
                cap_fake += 1
            counter_cap_live += 1
        return cap_real > cap_fake

def ResizeImage(image, scale_percent=70):
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    return resized

def FaceDetection():
    print('FaceDetection Started')
    count = 0
    time_last = 0
    global frame
    while True:
        try:
            if not frame_queue.empty():
                frame = frame_queue.get()
                if count % frame_skip == 0:
                    img = ResizeImage(frame, 70)
                    face_locations = face_recognition.face_locations(img)
                    for top, right, bottom, left in face_locations:
                        face_area = (bottom - top) * (right - left)
                        frame_area = img.shape[0] * img.shape[1]
                        if (face_area / frame_area) > distanceRecognition:
                            print("Лицо найдено")
                            if (time.time()-time_last) > 10:
                                if SpoofingAttackCheck():
                                    print("Лицо настоящее")
                                    result = FaceRecognition(frame)
                                    if result != 'Unknown' and result != None:
                                        print(f"Это {result}")
                                        if IsEntryAllowed(result):
                                            time_last = time.time()
                                            current_datetime = datetime.datetime.now().replace(microsecond=0)
                                            Path(f'{dir_path}/photo_entry/{result}/').mkdir(parents=True, exist_ok=True)
                                            cv2.imwrite(f'{dir_path}/photo_entry/{result}/{current_datetime}.png', frame)
                                            InsertVisitHistoryDB(result, current_datetime, True, 'Биометрия лица', False,
                                                                 True, f'photo_entry/{result}/{current_datetime}.png', None)
                                            NotifyEntry(frame, result, 'Биометрия лица', True)
                                            DoorOpen()
                                            time.sleep(5)
                                    else:
                                        gpio_write(h, speaker, 1)
                                        time.sleep(0.1)
                                        gpio_write(h, speaker, 0)
                                        time.sleep(0.1)
                                        gpio_write(h, speaker, 1)
                                        time.sleep(0.1)
                                        gpio_write(h, speaker, 0)
                                        current_datetime = datetime.datetime.now().replace(microsecond=0)
                                        Path(f'{dir_path}/photo_entry/123456/').mkdir(parents=True, exist_ok=True)
                                        cv2.imwrite(f'{dir_path}/photo_entry/123456/{current_datetime}.png', frame)
                                        InsertVisitHistoryDB(123456, current_datetime, False, 'Биометрия лица', False,
                                                             False, f'photo_entry/123456/{current_datetime}.png', None)
                                        NotifyEntry(frame, '123456', 'Биометрия лица', False)
                                        print('Не узнал лицо')
                                else:
                                    gpio_write(h, speaker, 1)
                                    time.sleep(0.1)
                                    gpio_write(h, speaker, 0)
                                    time.sleep(0.1)
                                    gpio_write(h, speaker, 1)
                                    time.sleep(0.1)
                                    gpio_write(h, speaker, 0)
                                    current_datetime = datetime.datetime.now().replace(microsecond=0)
                                    Path(f'{dir_path}/photo_entry/123456/').mkdir(parents=True, exist_ok=True)
                                    cv2.imwrite(f'{dir_path}/photo_entry/123456/{current_datetime}.png', frame)
                                    InsertVisitHistoryDB(123456, current_datetime, False, 'Биометрия лица', True,
                                                         False, f'photo_entry/123456/{current_datetime}.png', None)
                                    NotifyEntry(frame, '123456', 'Биометрия лица', False)
                                    print('Лицо не настоящее')
                        else:
                            print("Не вижу лицо")
                count += 1
        except:
            pass

def CaptureFrames():
    print('CaptureFrames Started')
    while True:
        ret, new_frame = cap.read()
        if ret:
            if frame_queue.full():
                frame_queue.get()
            frame_queue.put(new_frame)


if __name__ == '__main__':
    t0 = threading.Thread(target=CaptureFrames)
    t1 = threading.Thread(target=MainLoop)
    t2 = threading.Thread(target=FaceDetection)
    t3 = threading.Thread(target=RFIDListener)
    t0.start()
    t1.start()
    t2.start()
    t3.start()
