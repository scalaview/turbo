 pip3 install -r requirements.txt



for x in redis_db.keys("aliexpress:*"):
    redis_db.delete(x)