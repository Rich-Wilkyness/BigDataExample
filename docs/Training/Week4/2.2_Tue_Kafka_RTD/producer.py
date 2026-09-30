from kafka import KafkaProducer
import requests
import json
from datetime import datetime
import math
import time

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

while True: 
    ts = math.ceil(datetime.now().timestamp())

    res = requests.get('https://api.chucknorris.io/jokes/random').json()

    message = {
        "joke": res['value'],
        "time": ts
    }


    producer.send('test-topic', message)
    time.sleep(1)