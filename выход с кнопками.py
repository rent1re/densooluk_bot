import requests
from bs4 import BeautifulSoup
from telebot import TeleBot, types
import os
from urllib.parse import urljoin
import time
import threading

# Настройки
BASE_URL = "https://densooluk.media"
TELEGRAM_BOT_TOKEN = "8091170439:AAHKq94yW985dM-Xa0ERxj-t5UQD3sP9Wt8"
CHAT_ID = "@jkdsajkdsa"

# Инициализация бота
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Глобальная переменная для хранения ID последней отправленной новости
last_news_link = None

# Максимальная длина сообщения Telegram
MAX_MESSAGE_LENGTH = 400

# Функция для парсинга списка новостей из "Актуального"
def parse_actual_news():
    try:
        response = requests.get(BASE_URL)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Находим блок "Актуальное"
        actual_section = soup.find("div", class_="sppb-col-xs-6 sppb-col-sm-4 sppb-col-md-4 sppb-col-lg-4 sppb-col-12")
        if not actual_section:
            print("Секция 'Актуальное' не найдена.")
            return []

        # Находим статьи в блоке "Актуальное"
        articles = actual_section.find_all("div", class_="sppb-addon-article")
        news_list = []
        for article in articles:
            title_tag = article.find("h3")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link_tag = title_tag.find("a")
            link = urljoin(BASE_URL, link_tag["href"]) if link_tag else None

            if title and link:
                news_list.append({"title": title, "link": link})

        return news_list
    except Exception as e:
        print(f"Ошибка при парсинге 'Актуального': {e}")
        return []

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

        # Извлекаем изображение
        image_tag = article_body.find("img") if article_body else None
        image_url = image_tag["src"] if image_tag else None
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(BASE_URL, image_url)

        return full_text, image_url
    except Exception as e:
        print(f"Ошибка при получении полной новости: {e}")
        return "Текст не найден.", None

# Функция для отправки новости с кнопками
def send_to_telegram(news):
    try:
        full_text, image_url = get_full_news(news['link'])

        # Формируем сообщение
        message = f"🔔 *{news['title']}*\n\n{full_text}"

        # Если сообщение слишком длинное, обрезаем его
        if len(message) > 4096:
            message = message[:4096 - 50] + "..."  # Обрезаем и добавляем троеточие

        # Создаем клавиатуру с кнопками
        keyboard = types.InlineKeyboardMarkup()

        # Кнопка "Читать полностью"
        keyboard.add(types.InlineKeyboardButton("Читать полностью", url=news['link']))

        # Убедимся, что данные для кнопок короткие и допустимые
        like_data = f"like:{news['link'][:50]}"  # Ограничиваем длину ссылки для callback_data
        dislike_data = f"dislike:{news['link'][:50]}"  # Ограничиваем длину ссылки для callback_data

        # Кнопки лайка и дизлайка
        keyboard.row(
            types.InlineKeyboardButton("👍 Лайк", callback_data=like_data),
            types.InlineKeyboardButton("👎 Дизлайк", callback_data=dislike_data)
        )

        # Отправляем сообщение с изображением, если доступно
        if image_url:
            image_response = requests.get(image_url)
            image_path = "temp_image.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_response.content)

            with open(image_path, 'rb') as img:
                bot.send_photo(chat_id=CHAT_ID, photo=img, caption=message, parse_mode="Markdown", reply_markup=keyboard)
            os.remove(image_path)
        else:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", reply_markup=keyboard)

        print("Новость успешно отправлена!")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

# Обработчик нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    try:
        # Получаем данные из callback_data
        callback_data = call.data

        # Логика для кнопки "Лайк"
        if callback_data.startswith("like:"):
            bot.answer_callback_query(call.id, "Вы поставили лайк!")  # Ответ на клик
            bot.send_message(call.message.chat.id, "Спасибо за лайк! 👍")  # Отправляем сообщение с фидбеком

        # Логика для кнопки "Дизлайк"
        elif callback_data.startswith("dislike:"):
            bot.answer_callback_query(call.id, "Вы поставили дизлайк!")  # Ответ на клик
            bot.send_message(call.message.chat.id, "Мы учтем ваш отзыв! 👎")  # Отправляем сообщение с фидбеком

    except Exception as e:
        print(f"Ошибка при обработке нажатия кнопки: {e}")

# Функция для проверки и отправки новых новостей
def check_for_new_news():
    global last_news_link
    while True:
        news_list = parse_actual_news()
        if news_list:
            latest_news = news_list[0]  # Последняя новость
            if latest_news['link'] != last_news_link:  # Если это новая новость
                last_news_link = latest_news['link']
                send_to_telegram(latest_news)  # Отправляем новость
            else:
                print("Новых новостей нет.")
        else:
            print("Не удалось получить список новостей.")
        time.sleep(300)  # Проверяем каждые 5 минут

# Обработчик команды /news
@bot.message_handler(commands=['news'])
def send_last_news(message):
    news_list = parse_actual_news()
    if news_list:
        send_to_telegram(news_list[0])  # Отправляем последнюю новость
    else:
        bot.reply_to(message, "Нет доступных новостей для публикации.")

# Обработчик команды /news2
@bot.message_handler(commands=['news2'])
def send_second_last_news(message):
    news_list = parse_actual_news()
    if len(news_list) > 1:
        send_to_telegram(news_list[1])  # Отправляем предпоследнюю новость
    else:
        bot.reply_to(message, "Недостаточно новостей для публикации предпоследней.")

# Основной запуск
if __name__ == "__main__":
    print("Бот запущен...")
    # Запускаем фоновую проверку новых новостей
    news_thread = threading.Thread(target=check_for_new_news, daemon=True)
    news_thread.start()

    # Запуск бота для обработки команд
    bot.polling()
