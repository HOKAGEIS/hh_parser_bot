FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir aiogram aiosqlite python-dotenv requests
COPY . .
CMD ["python", "bot.py"]