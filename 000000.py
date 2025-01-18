import requests
from bs4 import BeautifulSoup
from telebot import TeleBot
import os
from urllib.parse import urljoin

# Настройки
BASE_URL = "https://densooluk.media"
NEWS_URL = f"{BASE_URL}/poleznoye/news.html"
TELEGRAM_BOT_TOKEN = "8091170439:AAHKq94yW985dM-Xa0ERxj-t5UQD3sP9Wt8"
CHAT_ID = "@jkdsajkdsa"

# Инициализация бота
bot = TeleBot(TELEGRAM_BOT_TOKEN)

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
            full_text = "Текст не найден."  # В случае, если текст не найден

        # Логируем полный текст для проверки
        print(f"Полный текст новости: {full_text[:1000]}...")  # Логируем первые 1000 символов для проверки

        # Извлекаем описание
        description_tag = soup.find("meta", {"name": "description"})
        description = description_tag["content"].strip() if description_tag else ""

        # Извлекаем изображение
        image_tag = article_body.find("img") if article_body else None
        image_url = image_tag["src"] if image_tag else None

        if image_url and not image_url.startswith("http"):
            image_url = urljoin(BASE_URL, image_url)

        # Извлекаем видео (если есть)
        video_tag = soup.find("video")
        video_url = video_tag["src"] if video_tag else None

        if video_url and not video_url.startswith("http"):
            video_url = urljoin(BASE_URL, video_url)

        return full_text, description, image_url, video_url
    except Exception as e:
        print(f"Ошибка при получении полной новости: {e}")
        return "Текст не найден.", "Описание отсутствует.", None, None

# Функция для отправки новости в Telegram
def send_to_telegram(news):
    try:
        full_text, description, image_url, video_url = get_full_news(news['link'])

        # Формируем сообщение
        message = (
            f"\U0001F514 *{news['title']}*\n\n"
            f"{description}\n\n"
            f"{full_text}\n\n"
            f"\U0001F517 [Читать полностью]({news['link']})"
        )

        # Отправляем сообщение с приоритетом на видео
        if video_url:
            video_response = requests.get(video_url)
            video_path = "temp_video.mp4"
            with open(video_path, 'wb') as f:
                f.write(video_response.content)

            with open(video_path, 'rb') as vid:
                bot.send_video(chat_id=CHAT_ID, video=vid, caption=message, parse_mode="Markdown")
            os.remove(video_path)
        elif image_url:
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

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling()