import re
import redis
import requests
import json
def error_detection(number):
    pattern = r"\b\d+\b"
    match = re.search(pattern, number)
    if match is None:
        return True
    else:
        if int(number) == 0:
            return True
        else: return False

def receiving_data(number, r):
    max_value = int(max(r.keys("*")))
    response = requests.get(
        f'https://randomuser.me/api/?results={number}')
    data = response.json()["results"]
    for i in range(1, len(data) + 1):
        r.set(f"{i}", json.dumps(data[i - 1]))
    if number < max_value:
        old_keys = [i for i in range(number + 1, max_value + 1)]
        r.delete(*old_keys)
    if number < 15:
        number_rows = number
    else:
        number_rows = 15
    return data, number_rows

def get_data(r):
    max_value = int(max(r.keys("*")))
    if max_value > 15:
        return [json.loads(r.get(f"{key}")) for key in range(1, 16)]
    else:
        return [json.loads(r.get(f"{key}")) for key in range(1, max_value+1)]