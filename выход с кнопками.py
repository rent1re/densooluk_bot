from telebot import TeleBot, types
import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

# Настройки
BASE_URL = "https://densooluk.media"
TELEGRAM_BOT_TOKEN = "8091170439:AAHKq94yW985dM-Xa0ERxj-t5UQD3sP9Wt8"
CHAT_ID = "@jkdsajkdsa"

# Инициализация бота
bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Глобальная переменная для хранения ID последней отправленной новости
last_news_link = None

# Функция для парсинга списка новостей из "Актуального"
def parse_actual_news():
    try:
        response = requests.get(BASE_URL)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем колонны с новостями
        columns = soup.find_all("div", class_="sppb-col-xs-6 sppb-col-sm-4 sppb-col-md-4 sppb-col-lg-4 sppb-col-12")
        if not columns:
            print("Не удалось найти колонны с новостями.")
            return []

        news_list = []
        for column in columns:
            # Находим заголовок новости
            title_tag = column.find("h3")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link_tag = title_tag.find("a")
            link = urljoin(BASE_URL, link_tag["href"]) if link_tag else None

            if title and link:
                news_list.append({"title": title, "link": link})

        return news_list
    except Exception as e:
        print(f"Ошибка при парсинге новостей: {e}")
        return []

# Функция для получения полной информации о новости
def get_full_news(link):
    try:
        response = requests.get(link)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Извлекаем текст статьи
        article_body = soup.find("div", itemprop="articleBody")
        if article_body:
            full_text = article_body.get_text(separator="\n", strip=True)
        else:
            full_text = "Текст не найден."

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
# Функция для отправки новости с кнопками
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
            types.InlineKeyboardButton("👍 ", callback_data=like_data),
            types.InlineKeyboardButton("👎 ", callback_data=dislike_data)
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
    if call.data.startswith("like:"):
        bot.answer_callback_query(call.id, "Вы поставили лайк!")
        bot.send_message(call.message.chat.id, "Спасибо за лайк! 👍")
    elif call.data.startswith("dislike:"):
        bot.answer_callback_query(call.id, "Вы поставили дизлайк!")
        bot.send_message(call.message.chat.id, "Мы учтем ваш отзыв! 👎")

# Основной запуск
if __name__ == "__main__":
    print("Бот запущен...")
    # Отправка последней новости в чат для теста
    news_list = parse_actual_news()
    if news_list:
        send_to_telegram(news_list[0])
    bot.polling()
