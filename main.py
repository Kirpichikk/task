import json

from flask import Flask, render_template, request, abort
import requests
import redis
import random
import time
import logging

from model import error_detection, receiving_data, get_data
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def connect_to_redis():
    logger.info("Connecting to Redis...")
    r = redis.Redis(
        host="redis",  # адрес сервера (через docker network)
        port=6379,         # порт
        db=0,              # номер базы (0-15)
        password=None      # пароль (если нужен)
    )
    for _ in range(3):
        try:
            r.ping()
            logger.info("Connected to Redis successfully!")
            return r
        except redis.ConnectionError:
            logger.warn("Unable to reach Redis, retrying in 5 seconds...")
            time.sleep(5)
    logger.error("Failed to connect to Redis after 3 attempts")
    raise redis.ConnectionError("Failed to connect to Redis after 3 attempts")

r = connect_to_redis()
response = requests.get('https://randomuser.me/api/?results=1000')
if response.status_code == 200:
    data = response.json()["results"]
    for i in range(1, len(data) + 1):
        r.set(f"{i}", json.dumps(data[i - 1]))


app = Flask(__name__)

@app.route('/', methods = ["GET", "POST"])
def main_handler():
    data = get_data(r)
    if request.method == "GET":
        return render_template('main.html', data = data )
    else:
        error = error_detection(request.form.get("number"))
        if error:
            return render_template('main.html', data=data, error=True)

        data, number_rows = receiving_data(int(request.form.get("number")), r)
        return render_template('main.html', data = data[:number_rows], )

@app.route('/<int:user_id>')
def user_handler(user_id):
    max_value = int(max(r.keys("*")))
    if user_id > max_value:
        abort(404)
    else:
        data = json.loads(r.get(f"{user_id}"))
        return render_template("full_info.html", data = data)

@app.route('/random')
def random_handler():
    max_value = int(max(r.keys("*")))
    user_id = random.randint(1, max_value+1)
    data = json.loads(r.get(f"{user_id}"))
    return render_template("full_info.html", data = data)

if __name__ == '__main__':
    app.run(debug=True)