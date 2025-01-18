import requests
from bs4 import BeautifulSoup
from telebot import TeleBot
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

# Функция для парсинга списка новостей
def parse_news():
    try:
        response = requests.get(NEWS_URL)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Находим список новостей
        articles = soup.find_all("article", class_="item")
        news_list = []
        for article in articles:
            title = article.find("h2").text.strip()
            link = urljoin(BASE_URL, article.find("a")["href"])
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

        # Извлекаем изображение
        image_tag = article_body.find("img") if article_body else None
        image_url = image_tag["src"] if image_tag else None
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(BASE_URL, image_url)

        # Извлекаем YouTube ссылку
        youtube_link = None
        object_tag = soup.find("object", class_="embed-responsive-item")
        if object_tag and object_tag.get("data"):
            youtube_link = object_tag["data"]
            if youtube_link.startswith("//"):
                youtube_link = "https:" + youtube_link

        return full_text, description, image_url, youtube_link
    except Exception as e:
        print(f"Ошибка при получении полной новости: {e}")
        return "Текст не найден.", "Описание отсутствует.", None, None

# Функция для отправки новости в Telegram
def send_to_telegram(news):
    try:
        full_text, description, image_url, youtube_link = get_full_news(news['link'])

        # Формируем сообщение
        message = (
            f"\U0001F514 *{news['title']}*\n\n"
            f"{description}\n\n"
            f"{full_text}\n\n"
            f"\U0001F517 [Читать полностью]({news['link']})"
        )

        # Добавляем YouTube ссылку, если она есть
        if youtube_link:
            message += f"\n\n🎥 [Смотреть видео]({youtube_link})"

        # Отправляем сообщение с изображением, если доступно
        if image_url:
            image_response = requests.get(image_url)
            image_path = "temp_image.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_response.content)

            with open(image_path, 'rb') as img:
                bot.send_photo(chat_id=CHAT_ID, photo=img, caption=message, parse_mode="Markdown")
            os.remove(image_path)
        else:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

        print("Новость успешно отправлена!")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

# Функция для проверки и отправки новых новостей
def check_for_new_news():
    global last_news_link
    while True:
        news_list = parse_news()
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
    news_list = parse_news()
    if news_list:
        send_to_telegram(news_list[0])  # Отправляем последнюю новость
    else:
        bot.reply_to(message, "Нет доступных новостей для публикации.")

# Обработчик команды /news2
@bot.message_handler(commands=['news2'])
def send_second_last_news(message):
    news_list = parse_news()
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
