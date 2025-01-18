import requests
from bs4 import BeautifulSoup
from telebot import TeleBot, types
import os
from urllib.parse import urljoin
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import hashlib

def generate_hash(data):
    return hashlib.md5(data.encode()).hexdigest()[:16]  # Ограничим длину до 16 символов

# Настройки
BASE_URL = "https://densooluk.media"
TELEGRAM_BOT_TOKEN = "8091170439:AAHKq94yW985dM-Xa0ERxj-t5UQD3sP9Wt8"
CHAT_ID = "@ego12345678"

# Инициализация бота
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Глобальные переменные для хранения лайков и дизлайков
likes = set()
dislikes = set()
last_action_time = {}
# Функция для парсинга списка новостей из "Актуального"
def parse_actual_news():
    try:
        response = requests.get(BASE_URL)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Находим блок "Актуальное"
        actual_section = soup.find("section", {"id": "section-id-0b9a719f-99c7-4297-8b1c-1b04ab4a3036"})
        if not actual_section:
            print("Секция 'Актуальное' не найдена.")
            return {}

        # Находим статьи в блоке "Актуальное"
        articles = actual_section.find_all("div", class_="sppb-addon-article")

        news_dict = {}

        for i, article in enumerate(articles[:3]):
            title_tag = article.find("h3")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link_tag = title_tag.find("a")
            link = urljoin(BASE_URL, link_tag["href"]) if link_tag else None

            if title and link:
                news_dict[f"news_{i + 1}"] = {"title": title, "link": link}

        return news_dict
    except Exception as e:
        print(f"Ошибка при парсинге 'Актуального': {e}")
        return {}

# Функция для получения полной информации о новости
def get_full_news(link):
    try:
        response = requests.get(link)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Извлекаем текст статьи из тега <div itemprop="articleBody">
        article_body = soup.find("div", itemprop="articleBody")
        if article_body:
            full_text = article_body.get_text(separator="\n", strip=True)
        else:
            full_text = "Текст не найден."

        # Извлекаем описание
        description_tag = soup.find("meta", {"name": "description"})
        description = description_tag["content"].strip() if description_tag else ""

        # Исключаем описание из полного текста, если оно там присутствует
        if description and description in full_text:
            full_text = full_text.replace(description, "").strip()

        # Ограничиваем длину текста до 3000 символов
        if len(full_text) > 3000:
            full_text = full_text[:3000] + "..."

        # Извлекаем изображение с секции 'active' (из блока с классом 'sppb-item active')
        active_items = soup.find("div", class_=["carousel-item active", "pull-none entry-image full-image"])

        image_url = None
        if active_items:
            # Поиск как изображения <img>, так и ссылок на файлы .jpg
            image_tag = active_items.find("img")
            if image_tag:
                image_url = urljoin(BASE_URL, image_tag["src"])
            else:
                # Ищем прямые ссылки на изображения .jpg
                jpg_tag = active_items.find("a", href=lambda href: href and href.endswith('.jpg'))
                if jpg_tag:
                    image_url = urljoin(BASE_URL, jpg_tag["href"])

        object_tag = soup.find("object", class_="embed-responsive-item")
        youtube_link = object_tag["data"] if object_tag and object_tag.get("data") else None
        if youtube_link and youtube_link.startswith("//"):
            youtube_link = "https:" + youtube_link

        print(f"Изображение найдено: {image_url}")
        return full_text, image_url, youtube_link
    except Exception as e:
        print(f"Ошибка при получении полной новости: {e}")
        return "Текст не найден.", None


def create_keyboard(news_link, youtube_link):
    keyboard = InlineKeyboardMarkup()

    # Кнопка "Читать полностью" с правильным URL
    keyboard.add(InlineKeyboardButton("Читать полностью", url=news_link))

    # Кнопка "Смотреть видео", если ссылка на YouTube существует
    if youtube_link:
        keyboard.add(InlineKeyboardButton("Смотреть видео", url=youtube_link))

    # Генерация коротких callback_data
    like_data = f"like:{generate_hash(news_link)}"
    dislike_data = f"dislike:{generate_hash(news_link)}"

    # Кнопки для лайков и дизлайков
    keyboard.row(
        InlineKeyboardButton(f"👍 {len(likes)}", callback_data=like_data),
        InlineKeyboardButton(f"👎 {len(dislikes)}", callback_data=dislike_data)
    )

    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global likes, dislikes, last_action_time

    user_id = call.from_user.id
    current_time = time.time()  # Текущее время в секундах

    try:
        # Проверка, прошло ли 10 секунд с последнего действия пользователя
        if user_id in last_action_time:
            elapsed_time = current_time - last_action_time[user_id]
            if elapsed_time < 10:
                # Если прошло меньше 10 секунд, игнорируем запрос
                bot.answer_callback_query(call.id, "Подождите 10 секунд перед повторным нажатием.", show_alert=True)
                return

        # Обновляем временную метку последнего действия пользователя
        last_action_time[user_id] = current_time

        # Проверка типа callback_data
        if call.data.startswith('like:'):
            if user_id not in likes:
                likes.add(user_id)
                dislikes.discard(user_id)
            else:
                likes.remove(user_id)
        elif call.data.startswith('dislike:'):
            if user_id not in dislikes:
                dislikes.add(user_id)
                likes.discard(user_id)
            else:
                dislikes.remove(user_id)

        # Уведомление пользователя о принятии действия
        bot.answer_callback_query(call.id, "Ваш выбор учтён!")

        # Извлечение текущей клавиатуры из сообщения
        current_markup = call.message.reply_markup

        # Поиск нужных кнопок (которые являются кнопками-ссылками)
        news_link = None
        youtube_link = None
        for button_row in current_markup.keyboard:
            for button in button_row:
                if button.url:
                    if "youtube" in button.url:
                        youtube_link = button.url
                    else:
                        news_link = button.url

        # Генерация новой клавиатуры с обновленными счетчиками
        new_keyboard = create_keyboard(news_link=news_link, youtube_link=youtube_link)

        # Проверка изменения текста и клавиатуры
        updated_message = False

        # Проверка изменения клавиатуры
        if current_markup.keyboard != new_keyboard.keyboard:
            updated_message = True

        # Проверка изменения текста
        current_text = call.message.text
        updated_text = f"🔔 *{call.message.text}*"

        if current_text != updated_text:
            updated_message = True

        # Обновляем сообщение только если произошли изменения
        if updated_message:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=new_keyboard
            )

        print("Сообщение обновлено!")

    except Exception as e:
        print(f"Ошибка в обработке callback_query: {e}")





# Функция для отправки текста для папы
def send_text_for_comm():
        text_for_comm = "Комментарии."
        # Отправляем сообщение в тот же чат (или другой, если нужно)
        bot.send_message(chat_id=CHAT_ID, text=text_for_comm, parse_mode="Markdown")


# Функция для отправки новостей
def send_to_telegram(news):
    try:
        full_text, image_url, youtube_link = get_full_news(news['link'])
        message = f"🔔 *{news['title']}*\n\n{full_text}"
        if len(message) > 4096:
            message = message[:4096 - 50] + "..."

        keyboard = create_keyboard(news['link'], youtube_link)
        if youtube_link:
            message += f"\n [⠀]({youtube_link})"
        if image_url:
            image_response = requests.get(image_url)
            with open("temp_image.jpg", 'wb') as f:
                f.write(image_response.content)

            with open("temp_image.jpg", 'rb') as img:
                bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=img,
                    caption=message[:1024],
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            os.remove("temp_image.jpg")
        else:
            bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        print("Новость успешно отправлена!")

        # После отправки новости отправляем текст для папы
        send_text_for_comm()

    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")


# Функция для проверки новых новостей
def check_for_new_news():
    last_news_link = None
    while True:
        news_list = parse_actual_news()
        if news_list:
            latest_news = news_list['news_2']
            if latest_news['link'] != last_news_link:
                last_news_link = latest_news['link']
                send_to_telegram(latest_news)
        time.sleep(300)

if __name__ == "__main__":
    print("Бот запущен...")
    news_thread = threading.Thread(target=check_for_new_news, daemon=True)
    news_thread.start()
    bot.polling()