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
try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client
http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


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

  def __init__(self, redis_db):
    super(Earth, self).__init__()
    self.redis_db = redis_db

  def suggestion(self, keyword):

    mid_result = []
    try:
      mid_result = self.get_keywords(keyword)
    except Exception as e:
      raise e

    left_blank_result = []
    try:
      left_blank_result = self.get_keywords(" "+keyword)
    except Exception as e:
      raise e

    right_blank_result = []
    try:
      right_blank_result = self.get_keywords(keyword+"")
    except Exception as e:
      raise e

    print(mid_result)
    print(left_blank_result)
    print(right_blank_result)
    result = (mid_result + left_blank_result + right_blank_result)

    if len(result) == 0:
      return

    unino_set = set()
    for x in result:
      k = x.get("keywords").strip()
      if k in unino_set:
        continue
      else:
        unino_set.add(k)
      print(k)
      if keyword == k:
        continue
      keyword_size = len(k.split(" "))
      count_str = x.get("count").replace(",", "")
      count = int(count_str)
      if keyword_size > 3 and count < 200 and self.redis_db.sadd("aliexpress.com", k) == 1:
        redis_db.hmset("aliexpress:keyword:"+k, { "keyword": k, "count": count, "len": keyword_size, "parent": keyword })
        redis_db.lpush("aliexpress:products:taks", k)
        print("target: " + k)
      else:
        continue

  def get_keywords(self, keyword):
    params =  {
              "__number": 2,
              "varname": "intelSearchData",
              "keyword": keyword.replace(" ", "+"),
              "_": execjs.eval("((new Date()).getTime()/100).toFixed(0)"),
            }
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

      products.append(Subject({"link": link, "order_number": order_number, "price": price, "title": title, "img": img }))
    return products

  def get_search(self, keyword):
    params =  {
              "keywords": keyword.replace(" ", "+")
            }
    res = requests.get(self.__urls["search"], params=params, headers=self.headers, cookies=self.cookies, timeout=self.timeout)
    if res.status_code == 200:
      html = BeautifulSoup(res.text)
      return html.findAll("div", {"class": "pro-inner"})
    else:
      res.raise_for_status()

# def Mercury():

#   def run():
#     keyword = redis_db.rpop()
#     if keyword is None:
#       sleep(2000)
#     mars.products(keyword)

#   thread = threading.Thread(target=get_movie_detail, name="get_movie_detail")
#   thread.setDaemon(True)
#   thread.start()



if __name__ == "__main__":
  redis_db = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)
  # Earth(redis_db).suggestion("liquid matte lipstick")
  # dose of colors liquid matte lipstick lot
  mars = Mars(redis_db)
  mars.get_products(redis_db.hgetall("aliexpress:keyword:liquid matte lipstick star"))
  # .products("liquid matte lipstick")
