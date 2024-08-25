import os
import json
import random
import string
from telebot import TeleBot, types
from telegraph import Telegraph

token = "TOKEN"
bot = TeleBot(token)
channel_id = '-1002174723157'  

# Путь к директории для хранения данных
DATA_DIR = 'bot_data'
TEAM_MEMBERS_FILE = os.path.join(DATA_DIR, 'team_members.json')
PENDING_MEMBERS_FILE = os.path.join(DATA_DIR, 'pending_members.json')
ADMIN_IDS_FILE = os.path.join(DATA_DIR, 'admin_ids.json')
QUESTS_FILE = os.path.join(DATA_DIR, 'quests.json')

# Инициализация словарей
admin_ids = []
active_chats = {}
waiting_queue = []
user_data = {}
team_members = {}
pending_members = {}
quests = {}

# Инициализация Telegraph API
telegraph = Telegraph()
telegraph.create_account(short_name='bot')

def ensure_data_dir():
    """Создает директорию для хранения данных, если ее нет."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_data():
    """Загружает данные из файлов в соответствующие словари."""
    global admin_ids, team_members, pending_members, quests

    ensure_data_dir()

    # Загрузка admin_ids
    if os.path.exists(ADMIN_IDS_FILE):
        with open(ADMIN_IDS_FILE, 'r') as f:
            admin_ids = json.load(f)
    else:
        admin_ids = [5841941223, 1085668248]
        save_admin_ids()

    # Загрузка team_members
    if os.path.exists(TEAM_MEMBERS_FILE):
        with open(TEAM_MEMBERS_FILE, 'r') as f:
            team_members = json.load(f)

    # Загрузка pending_members
    if os.path.exists(PENDING_MEMBERS_FILE):
        with open(PENDING_MEMBERS_FILE, 'r') as f:
            pending_members = json.load(f)
    
    # Загрузка quests
    if os.path.exists(QUESTS_FILE):
        with open(QUESTS_FILE, 'r') as f:
            quests = json.load(f)

def save_team_members():
    """Сохраняет данные team_members в файл."""
    with open(TEAM_MEMBERS_FILE, 'w') as f:
        json.dump(team_members, f, indent=4)

def save_pending_members():
    """Сохраняет данные pending_members в файл."""
    with open(PENDING_MEMBERS_FILE, 'w') as f:
        json.dump(pending_members, f, indent=4)

def save_admin_ids():
    """Сохраняет данные admin_ids в файл."""
    with open(ADMIN_IDS_FILE, 'w') as f:
        json.dump(admin_ids, f, indent=4)

def save_quests():
    """Сохраняет данные quests в файл."""
    with open(QUESTS_FILE, 'w') as f:
        json.dump(quests, f, indent=4)

def is_admin(user_id):
    return user_id in admin_ids

def is_team_member(user_id):
    return str(user_id) in team_members

def generate_unique_quest_id():
    """Генерирует уникальный 10-символьный идентификатор задания."""
    while True:
        quest_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if quest_id not in quests:
            return quest_id

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    if not is_team_member(user_id) and str(user_id) not in pending_members:
        bot.send_message(
            user_id,
            'Привет! Отныне это твой бот-помощник! До начала, давай устроимся на интересующую тебя программу!\n\nНа данный момент, у нас набор на такие программы: \n\n- Дизайн\n- Сайты\n- Программирование\n- Видеомонтаж \n\nВ анкете снизу укажи, в какой программе ты специализируешься, конечно, можешь выбрать несколько вариантов!'
        )
        send_survey(message)
    else:
        bot.send_message(user_id, 'Ты уже подал заявку или был одобрен. Теперь ты можешь пользоваться другими командами.')

def send_survey(message):
    user_id = message.chat.id

    questions = [
        "Анкета: \nКак тебя зовут?",
        "Твой возраст?",
        "Ваши выбранные программы",
        "Опыт работы (в годах)?",
        "О себе. Расскажи в каких компаниях ты работал ранее, что ты ждешь от работы, можешь поделиться в каких компьютерных программах работаешь"
    ]

    user_data[user_id] = {
        'username': message.from_user.username or f'user_{user_id}',
        'answers': [],
        'question_index': 0,
        'chat_id': user_id
    }

    bot.send_message(user_id, questions[0])

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'question_index' in user_data[message.chat.id] and user_data[message.chat.id]['question_index'] < 5)
def handle_survey_response(message):
    user_id = message.chat.id
    question_index = user_data[user_id]['question_index']
    questions = [
        "Анкета: \nКак тебя зовут?",
        "Твой возраст?",
        "Ваши выбранные программы",
        "Опыт работы (в годах)?",
        "О себе. Расскажи в каких компаниях ты работал ранее, что ты ждешь от работы, можешь поделиться в каких компьютерных программах работаешь"
    ]

    user_data[user_id]['answers'].append(message.text)
    user_data[user_id]['question_index'] += 1

    if user_data[user_id]['question_index'] < len(questions):
        bot.send_message(user_id, questions[user_data[user_id]['question_index']])
    else:
        bot.send_message(
            user_id,
            "Спасибо за ответы! Ждите одобрения! Если все в порядке - с Вами свяжется администратор. Хорошего дня!"
        )
        save_survey_to_telegraph(user_id)
        send_survey_results_to_admins(user_id)
        del user_data[user_id]  # Удаляем временные данные

def save_survey_to_telegraph(user_id):
    data = user_data[user_id]
    username = data['username']
    answers = data['answers']

    # Формируем содержимое страницы
    content = f"<b>Анкета пользователя @{username} (ID: {user_id}):</b><br>"
    content += f"<b>1. Имя:</b> {answers[0]}<br>"
    content += f"<b>2. Возраст:</b> {answers[1]}<br>"
    content += f"<b>3. Программы:</b> {answers[2]}<br>"
    content += f"<b>4. Опыт работы:</b> {answers[3]} лет<br>"
    content += f"<b>5. О себе:</b> {answers[4]}<br>"

    # Публикуем страницу на Telegra.ph
    response = telegraph.create_page(
        title=f"Анкета пользователя @{username}",
        html_content=content
    )

    # Сохраняем ссылку на страницу в данных участника
    page_url = f"https://telegra.ph/{response['path']}"
    pending_members[str(user_id)] = {
        'username': username,
        'page_url': page_url,
        'chat_id': user_id
    }
    save_pending_members()  # Сохраняем изменения

def send_survey_results_to_admins(user_id):
    data = pending_members[str(user_id)]
    username = data['username']
    page_url = data['page_url']

    results_message = f"Новая анкета от @{username} (ID: {user_id}):\n"
    results_message += f"Ссылка на анкету: {page_url}\n"
    results_message += f"Для добавления в команду используйте команду:\n /add {user_id}\n"
    results_message += f"Для отклонения заявки используйте команду:\n /reject {user_id}\n"

    for admin_id in admin_ids:
        bot.send_message(admin_id, results_message)


@bot.message_handler(commands=['post'])
def post_to_channel(message):
    user_id = message.chat.id
    if is_admin(user_id):
        message_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ''
        if message_text:
            bot.send_message(channel_id, message_text)
        else:
            bot.send_message(message.chat.id, 'Текст для публикации не найден. Используйте команду правильно.')
    else:
        bot.send_message(message.chat.id, 'Вы не админ!')



@bot.message_handler(commands=['newquest'])
def create_new_quest(message):
    user_id = message.chat.id
    if is_admin(user_id):
        bot.send_message(user_id, "Напишите тематику задания:")
        user_data[user_id] = {'step': 'theme'}
    else:
        bot.send_message(user_id, "Вы не авторизованы для использования этой команды.")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'step' in user_data[message.chat.id])
def handle_quest_creation(message):
    user_id = message.chat.id
    step = user_data[user_id]['step']

    if step == 'theme':
        user_data[user_id]['theme'] = message.text
        bot.send_message(user_id, "Напишите требование:")
        user_data[user_id]['step'] = 'requirement'
    elif step == 'requirement':
        user_data[user_id]['requirement'] = message.text
        bot.send_message(user_id, "Напишите заказчика:")
        user_data[user_id]['step'] = 'customer'
    elif step == 'customer':
        user_data[user_id]['customer'] = message.text
        bot.send_message(user_id, "Напишите страну:")
        user_data[user_id]['step'] = 'country'
    elif step == 'country':
        user_data[user_id]['country'] = message.text
        bot.send_message(user_id, "Напишите Дедлайн:")
        user_data[user_id]['step'] = 'deadline'
    elif step == 'deadline':
        user_data[user_id]['deadline'] = message.text
        bot.send_message(user_id, "Отправьте ссылку с доп. файлами:")
        user_data[user_id]['step'] = 'file_link'
    elif step == 'file_link':
        user_data[user_id]['file_link'] = message.text
        bot.send_message(user_id, "Укажите оплату:")
        user_data[user_id]['step'] = 'payment'
    elif step == 'payment':
        user_data[user_id]['payment'] = message.text
        quest_id = generate_unique_quest_id()
        user_data[user_id]['quest_id'] = quest_id

        post_text = (
            f"✅ <u><b>Пришел новый заказ! Успевайте забрать его, пока не забрал кто-то другой!</b></u> \n<b>#{quest_id}</b>\n\n"
            f"❗️ <b>Тематика: {user_data[user_id]['theme']}</b>\n\n"
            f"<b>Требования:</b>\n* {user_data[user_id]['requirement']}\n\n"
            f"<blockquote><b>Заказчик:</b> {user_data[user_id]['customer']}\n"
            f"<b>Страна:</b> {user_data[user_id]['country']}\n"
            f"<b>Дедлайн:</b> {user_data[user_id]['deadline']}\n"
            f"<b>Доп. файлы:</b> {user_data[user_id]['file_link']}</blockquote>\n\n"
            f"💸 <b>Оплата: {user_data[user_id]['payment']}₽</b>\n\n"
            f"<i>- ДЛЯ ВЫПОЛНЕНИЯ ЗАКАЗА НАЖАТЬ КНОПКУ НИЖЕ</i>\n"
            f"➖➖➖➖➖➖➖➖➖➖➖\n"
            f"<i>По всем техническим проблемам - сообщайте боту через команду <b>/start_chat</b></i>"
        )

        # Кнопка для отклика
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("Откликнуться", callback_data=f"apply_{quest_id}")
        markup.add(button)

        # Путь к изображению
        image_path = "1.png"

        # Отправляем текст с изображением в одном сообщении
        with open(image_path, 'rb') as image_file:
            sent_message = bot.send_photo(channel_id, photo=image_file, caption=post_text, parse_mode="HTML", reply_markup=markup)

        # Сохраняем задание в словарь, включая идентификатор сообщения
        quests[quest_id] = {
            'theme': user_data[user_id]['theme'],
            'requirement': user_data[user_id]['requirement'],
            'customer': user_data[user_id]['customer'],
            'country': user_data[user_id]['country'],
            'deadline': user_data[user_id]['deadline'],
            'file_link': user_data[user_id]['file_link'],
            'payment': user_data[user_id]['payment'],
            'message_id': sent_message.message_id
        }

        save_quests()

        # Удаляем временные данные
        del user_data[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith("apply_"))
def handle_apply(call):
    user_id = call.from_user.id
    quest_id = call.data.split("_")[1]

    if is_team_member(user_id):
        user_quest_key = f"{user_id}_{quest_id}"

        if user_quest_key not in quests:
            # Отправляем уведомление о новом отклике
            username = team_members[str(user_id)]['username']
            user_survey_url = team_members[str(user_id)]['page_url']

            response_message = (
                f"📩 <b>Новый отклик на задание #{quest_id}:</b>\n"
                f"🔹 @{username} (ID: {user_id})\n"
                f"🔗 <a href='{user_survey_url}'>Анкета</a>\n"
            )

            # Отправляем уведомление всем администраторам
            for admin_id in admin_ids:
                bot.send_message(admin_id, response_message, parse_mode="HTML")

            # Помечаем, что пользователь откликнулся на задание
            quests[user_quest_key] = True
            save_quests()

            # Уведомляем пользователя
            bot.send_message(user_id, "Вы откликнулись на задание.")
        else:
            bot.send_message(user_id, "Вы уже откликнулись на это задание.")
    else:
        bot.send_message(user_id, "Вы не авторизованы для использования этого бота. Пожалуйста, дождитесь одобрения вашей заявки.")


@bot.message_handler(commands=['remove_button'])
def remove_button(message):
    user_id = message.chat.id
    if is_admin(user_id):
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(user_id, "Пожалуйста, укажите номер задания для удаления кнопки. Пример: /remove_button QUEST_ID")
                return

            quest_id = parts[1]

            if quest_id in quests:
                quest = quests[quest_id]
                if 'message_id' in quest:
                    # Удаляем кнопку у сообщения с заданием
                    bot.edit_message_reply_markup(channel_id, quest['message_id'], reply_markup=None)
                    bot.send_message(user_id, f"Кнопка для задания #{quest_id} успешно удалена.")
                else:
                    bot.send_message(user_id, f"Задание с номером #{quest_id} не имеет идентификатора сообщения для удаления кнопки.")
            else:
                bot.send_message(user_id, f"Задание с номером #{quest_id} не найдено.")
        except Exception as e:
            bot.send_message(user_id, f"Произошла ошибка при удалении кнопки: {e}")
    else:
        bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")



@bot.message_handler(commands=['add'])
def add_to_team(message):
    if is_admin(message.chat.id):
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "Пожалуйста, укажите ID пользователя для добавления. Пример: /add 123456789")
                return

            user_id = parts[1]
            if user_id in team_members:
                bot.send_message(message.chat.id, f"Пользователь {user_id} уже в команде.")
            elif user_id in pending_members:
                # Переносим пользователя из pending_members в team_members
                team_members[user_id] = pending_members.pop(user_id)
                save_team_members()
                save_pending_members()
                bot.send_message(message.chat.id, f"Пользователь {user_id} добавлен в команду.")
                
                # Уведомляем пользователя о принятии
                bot.send_message(int(user_id), "Поздравляем! Ваша заявка одобрена, и вы добавлены в команду. Теперь вы можете пользоваться всеми доступными командами бота.")
            else:
                bot.send_message(message.chat.id, "Этот пользователь ещё не заполнил анкету или его заявка уже обработана.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Произошла ошибка при добавлении пользователя: {e}")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['reject'])
def reject_application(message):
    if is_admin(message.chat.id):
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "Пожалуйста, укажите ID пользователя для отклонения. Пример: /reject 123456789")
                return

            user_id = parts[1]
            if user_id in pending_members:
                pending_members.pop(user_id)
                save_pending_members()
                bot.send_message(message.chat.id, f"Заявка пользователя {user_id} отклонена.")
                
                # Уведомляем пользователя об отклонении
                bot.send_message(int(user_id), "К сожалению, ваша заявка была отклонена администратором.")
            else:
                bot.send_message(message.chat.id, "Заявка этого пользователя уже обработана или не существует.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Произошла ошибка при отклонении заявки: {e}")
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['list_command'])
def list_command(message):
    if is_admin(message.chat.id):
        result_message = "📋 <b>Список админов и участников:</b>\n\n"

        # Список админов
        result_message += "<b>Админы:</b>\n"
        for admin_id in admin_ids:
            try:
                admin_user = bot.get_chat(admin_id)
                admin_username = admin_user.username or f"user_{admin_id}"
                result_message += f"▫️ @{admin_username} (ID: {admin_id})\n"
            except Exception as e:
                result_message += f"▫️ ID: {admin_id} (Не удалось получить юзернейм)\n"

        # Список участников
        if team_members:
            result_message += "\n<b>Участники команды:</b>\n"
            for member_id, data in team_members.items():
                username = data['username']
                page_url = data['page_url']
                result_message += f"▫️ @{username} (ID: {member_id}) - <a href='{page_url}'>Анкета</a>\n"
        else:
            result_message += "\n❗️ В команде пока нет участников."

        # Список ожидающих одобрения
        if pending_members:
            result_message += "\n<b>Ожидают одобрения:</b>\n"
            for member_id, data in pending_members.items():
                username = data['username']
                page_url = data['page_url']
                result_message += f"▫️ @{username} (ID: {member_id}) - <a href='{page_url}'>Анкета</a>\n"
        else:
            result_message += "\n✅ Нет заявок, ожидающих одобрения."

        bot.send_message(message.chat.id, result_message, parse_mode="HTML", disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "У вас нет прав на выполнение этой команды.")

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.chat.id
    if is_team_member(user_id):
        help_text = """
<b>Доступные команды:</b>

/start_chat - Начать диалог с администраторами
/end_chat - Завершить диалог с администраторами
/help - Показать это сообщение помощи
"""
        bot.send_message(user_id, help_text, parse_mode="HTML")
    else:
        bot.send_message(user_id, "Вы не авторизованы для использования этого бота. Пожалуйста, заполните анкету и дождитесь одобрения.")



@bot.message_handler(commands=['fire'])
def fire_member(message):
    user_id = message.chat.id
    if is_admin(user_id):
        try:
            parts = message.text.strip().split()
            if len(parts) < 2:
                bot.send_message(user_id, "Пожалуйста, укажите ID пользователя для увольнения. Пример: /fire 123456789")
                return

            target_id = parts[1]
            
            if target_id not in team_members:
                bot.send_message(user_id, "Этот пользователь не является членом команды.")
                return
            
            # Удаляем пользователя из команды
            team_members.pop(target_id)
            save_team_members()
            
            # Уведомляем пользователя о увольнении
            bot.send_message(int(target_id), "К сожалению, вы были уволены из команды. Ваш доступ к командам и каналам больше не доступен.")

            # Кикаем пользователя из канала
            bot.kick_chat_member(channel_id, int(target_id))
            
            bot.send_message(user_id, f"Пользователь {target_id} был успешно уволен и кикнут из канала.")

        except Exception as e:
            bot.send_message(user_id, f"Произошла ошибка при увольнении пользователя: {e}")
    else:
        bot.send_message(user_id, "У вас нет прав для выполнения этой команды.")



@bot.message_handler(commands=['start_chat'])
def handle_start_chat(message):
    user_id = message.chat.id

    if is_team_member(user_id):
        if user_id in active_chats or user_id in waiting_queue:
            bot.send_message(user_id, 'Вы уже находитесь в очереди или в активном чате.')
            return

        if not active_chats:
            start_chat(user_id)
        else:
            waiting_queue.append(user_id)
            bot.send_message(user_id, 'Все операторы заняты. Вы добавлены в очередь. Пожалуйста, ожидайте.')

    else:
        bot.send_message(user_id, "Вы не авторизованы для начала диалога. Пожалуйста, дождитесь одобрения вашей заявки.")

def start_chat(user_id):
    active_chats[user_id] = admin_ids
    bot.send_message(user_id, 'Диалог начат. Вы можете отправлять сообщения.')

    for admin_id in admin_ids:
        bot.send_message(admin_id, f'📞 Начат диалог с пользователем @{team_members[str(user_id)]["username"]} (ID: {user_id}).')
        bot.send_message(admin_id, f'Используйте команду /end_chat чтобы завершить диалог.')

@bot.message_handler(commands=['end_chat'])
def handle_end_chat(message):
    user_id = message.chat.id

    if user_id in active_chats:
        end_chat(user_id)
    elif user_id in admin_ids:
        # Завершение чата администратором
        if active_chats:
            user_id_to_end = next(iter(active_chats.keys()))  # Берем ID первого активного чата
            end_chat(user_id_to_end)
        else:
            bot.send_message(user_id, 'В данный момент нет активных чатов.')
    
    elif is_team_member(user_id):
        bot.send_message(user_id, 'Вы не в активном чате.')
    else:
        bot.send_message(user_id, 'Вы не авторизованы для использования этого бота. Пожалуйста, заполните анкету и дождитесь одобрения.')




def end_chat(user_id):
    del active_chats[user_id]
    bot.send_message(user_id, 'Диалог завершен. Спасибо за общение!')

    for admin_id in admin_ids:
        bot.send_message(admin_id, f'Диалог с пользователем @{team_members[str(user_id)]["username"]} (ID: {user_id}) завершен.')

    # Проверяем, есть ли кто-то в очереди
    if waiting_queue:
        next_user_id = waiting_queue.pop(0)
        start_chat(next_user_id)

@bot.message_handler(content_types=['text', 'photo', 'audio', 'document', 'sticker', 'video', 'video_note', 'voice', 'location', 'contact', 'venue', 'animation'])
def handle_media(message):
    user_id = message.chat.id

    if user_id in active_chats:
        # Отправляем сообщение всем администраторам
        for admin_id in admin_ids:
            if message.content_type == 'text':
                bot.send_message(admin_id, f'Сообщение от @{team_members[str(user_id)]["username"]}: {message.text}')
            else:
                bot.forward_message(admin_id, user_id, message.message_id)

    elif user_id in admin_ids:
        # Если администратор, отправляем сообщение активному чату
        if active_chats:
            active_user_id = next(iter(active_chats.keys()))
            bot.copy_message(active_user_id, user_id, message.message_id)
        else:
            bot.send_message(user_id, 'В данный момент нет активных чатов.')
    elif is_team_member(user_id):
        bot.send_message(user_id, 'Вы не в активном чате.')
    else:
        bot.send_message(user_id, 'Вы не авторизованы для использования этого бота. Пожалуйста, заполните анкету и дождитесь одобрения.')

if __name__ == '__main__':
    load_data()
    print("Бот запущен и готов к работе.")
    bot.polling(none_stop=True)
