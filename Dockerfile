FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# WSGI-сервер на порту 5000 со всеми сообщениями из лога
CMD [ "gunicorn", "-b 0.0.0.0:5000", "main:app" ]
