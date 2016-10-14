import requests
import redis
import execjs
import logging
from bs4 import BeautifulSoup
import  threading
from time import sleep

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1

# # You must initialize logging, otherwise you'll not see debug output.
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class Subject():
    def __init__(self, d):
        self.__dict__ = d


class ClassName(object):
  """docstring for ClassName"""
  def __init__(self, arg):
    super(ClassName, self).__init__()
    self.arg = arg

class Sun:

  timeout = 100

  __urls = {
    "home": "https://m.aliexpress.com",
    "keyword": "https://connectkeyword.aliexpress.com/lenoIframeJson.htm",
    "search": "https://m.aliexpress.com/search.htm"
  }

  def __init__(self):
    self.init_opener()

  def init_opener(self, headers = {
    'Connection': 'Keep-Alive',
    'Accept': 'text/html, application/xhtml+xml, */*',
    'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_3_5 like Mac OS X) AppleWebKit/601.1 (KHTML, like Gecko) CriOS/50.0.2661.95 Mobile/13G36 Safari/601.1.46',
    }):
    self.headers = headers
    response = requests.get(self.__urls["home"], headers=headers, timeout=self.timeout)
    if response.status_code == 200:
      self.cookies = response.cookies
    else:
      response.raise_for_status()


class Earth(Sun):

  __urls = {
    "home": "https://m.aliexpress.com",
    "keyword": "https://connectkeyword.aliexpress.com/lenoIframeJson.htm",
    "search": "https://m.aliexpress.com/search.htm"
  }

  def __init__(self, redis_db, unino_set):
    super(Earth, self).__init__()
    self.redis_db = redis_db
    self.unino_set = unino_set

  def suggestion(self, keyword):

    mid_result = []
    try:
      mid_result = self.get_keywords(keyword)
    except Exception as e:
      print(e)

    left_blank_result = []
    try:
      left_blank_result = self.get_keywords(" "+keyword)
    except Exception as e:
      print(e)

    right_blank_result = []
    try:
      right_blank_result = self.get_keywords(keyword+" ")
    except Exception as e:
      print(e)

    result = (mid_result + left_blank_result + right_blank_result)

    if len(result) == 0:
      return

    for x in result:
      k = x.get("keywords").strip()
      if k in self.unino_set:
        continue
      else:
        self.unino_set.add(k)
      if keyword == k:
        continue
      keyword_size = len(k.split(" "))
      count_str = x.get("count").replace(",", "")
      count = int(count_str)
      if keyword_size > 3 and count < 200:
        if self.redis_db.sadd("aliexpress.com", k) == 1:
          redis_db.hmset("aliexpress:keyword:"+k, { "keyword": k, "count": count, "len": keyword_size, "parent": keyword })
          redis_db.lpush("aliexpress:products:taks", k)
          print("target: " + k)
        else:
          continue
      else:
        self.suggestion(k)

  def get_keywords(self, keyword):
    params =  {
              "__number": 2,
              "varname": "intelSearchData",
              "keyword": keyword.replace(" ", "+"),
              "_": execjs.eval("((new Date()).getTime()/100).toFixed(0)"),
            }
    print("get keyword: %s" % keyword )
    res = requests.get(self.__urls["keyword"], params=params, headers=self.headers, cookies=self.cookies, timeout=self.timeout)
    if res.status_code == 200:
      jsonp = res.text.replace("window.", "").strip()
      if jsonp.endswith(";"):
        jsonp = jsonp[0:len(jsonp)-1]
      json = execjs.eval(jsonp)
      return json.get("keyWordDTOs")
    else:
      res.raise_for_status()

class Mars(Sun):

  __urls = {
    "home": "https://m.aliexpress.com",
    "keyword": "https://connectkeyword.aliexpress.com/lenoIframeJson.htm",
    "search": "https://m.aliexpress.com/search.htm"
  }

  def __init__(self, redis_db):
    super(Mars, self).__init__()
    self.redis_db = redis_db

  def get_products(self, target):
    search_rate = (200 - int(target["count"]))
    products = self.products(target["keyword"])
    rate = self.rate(products, target["keyword"])
    keyword_rate = rate.order_rate + search_rate
    redis_db.hset("aliexpress:keyword:"+target["keyword"], "rate", keyword_rate)
    redis_db.zadd("aliexpress:sortresult", keyword_rate, target["keyword"])

  def rate(self, products, keyword):
    rate = 0
    total_order_number = 0
    rate_total = 0
    cc = 1.00
    total_price = 0.00
    for x in products:
      total_order_number += int(x.order_number)
      rate_total = cc * int(x.order_number)
      cc -= 0.05
      total_price += float(x.price)
      self.redis_db.sadd("aliexpress:products:"+keyword, x.__dict__)

    order_rate = (1- rate_total/total_order_number) * 200
    average_price = total_price / len(products)
    return Subject({"order_rate": order_rate, "average_price": average_price})

  def products(self, keyword):
    result_htmls = self.get_search(keyword)

    if len(result_htmls) == 0:
      return

    products = []
    for x in result_htmls[0:20]:
      order_number_node = x.find("span", {"class": "order-number"})
      order_number = 0
      if order_number_node is not None:
        order_number_text = order_number_node.text.strip().replace("Orders", "").replace("Order", "").strip()
        order_number = int(order_number_text) if order_number_text != '' else 0

      price = 0
      price_node = x.find("em", {"itemprop": "price"})
      if price_node is not None:
        price_text = price_node.text.replace("US", "").replace("$", '').strip()
        if "-" in price_text:
          price_text = price_text.split("-")[0].strip()
        price = float(price_text)

      if price == 0:
        price_node = x.find("del", {"class": "original-price"})
        if price_node is not None:
          price_text = price_node.text.replace("US", "").replace("$", '').replace("/ piece", "").strip()
          if "-" in price_text:
            price_text = price_text.split("-")[0].strip()
          price = float(price_text)

      title = ""
      title_node = x.find("h3")
      if title_node is not None:
        title = title_node.text.strip()

      img = ""
      img_node = x.find("img")
      if img_node is not None:
        img = img_node["src-img"]
        if "http:" not in img:
          img = "http:" + img.replace("_220x220.jpg", "")

      link = ""
      link_node = x.find("a", {"class": "ms-rc-ripple"})
      if link_node is not None:
        link = link_node["href"]
        if "https:" not in link:
          link = "https:" + link

      products.append(Subject({"link": link, "order_number": order_number, "price": price, "title": title, "img": img }))
    return products

  def get_search(self, keyword):
    params =  {
              "keywords": keyword.replace(" ", "+")
            }
    res = requests.get(self.__urls["search"], params=params, headers=self.headers, cookies=self.cookies, timeout=self.timeout)
    if res.status_code == 200:
      html = BeautifulSoup(res.text, "html.parser")
      return html.findAll("div", {"class": "pro-inner"})
    else:
      res.raise_for_status()

def mercury(earth, mars, redis_db):

  with open('./keywords.txt') as fp:
      for line in fp:
        redis_db.sadd("aliexpress:init", line)

  def load_suggestion(redis_db, earth):
    while True:
      keyword = redis_db.spop("aliexpress:init")
      if keyword is None:
        sleep(5)
        continue

      try:
        earth.suggestion(keyword)
      except Exception as e:
        print(e)

  def run_products(redis_db, mars):
    while True:
      keyword = redis_db.rpop("aliexpress:products:taks")
      if keyword is None:
        sleep(5)
        continue
      product_search = redis_db.hgetall("aliexpress:keyword:"+keyword)
      if product_search is not None:
        try:
          mars.get_products(product_search)
        except Exception as e:
          print(e)

  for x in range(1,3):
    sug = threading.Thread(target=load_suggestion, name="load_suggestion", args=[redis_db, earth])
    sug.setDaemon(True)
    sug.start()

  products = threading.Thread(target=run_products, name="run_products", args=[redis_db, mars])
  products.setDaemon(True)

  sleep(5)
  print("search start")
  products.start()



if __name__ == "__main__":
  redis_db = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)
  unino_set = set()
  earth = Earth(redis_db, unino_set)
  mars = Mars(redis_db)
  mercury(earth, mars, redis_db)
  while True:
    sleep(10000000)
