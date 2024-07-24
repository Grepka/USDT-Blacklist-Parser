FROM python:3.9-slim

LABEL authors="Grepka"

# Обновляем список пакетов и устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean

# Устанавливаем библиотеку requests
RUN pip install requests

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем содержимое текущей директории в контейнер
COPY . .

# Команда по умолчанию для запуска контейнера
CMD ["bash"]