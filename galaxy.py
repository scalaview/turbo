import requests
import redis
import execjs
import logging

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
    "keyword": "https://connectkeyword.aliexpress.com/lenoIframeJson.htm?__number=2&varname=intelSearchData",
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
      # if len(json.get("keyWordDTOs")) <= 1:
        # pass
      print(json.get("keyWordDTOs"))
      for x in json.get("keyWordDTOs"):
        k = x.get("keywords").strip()
        keyword_size = len(k.split(" "))
        if keyword == k:
          continue
        if keyword_size > 3:
          if redis_db.exists("keyword:" + k) == 0:
            count_str = x.get("count").replace(",", "")
            count = int(count_str)
            # redis_db.hmset("keyword:"+k, { "keyword": k, "count": count, "len": keyword_size })
            # redis_db.lpush("taks", k)
          else:
            pass
        else:
          pass
        if redis_db.exists("keyword:" + x.get("keywords").strip()) == 0:
          print(x.get("keywords"))
          print(x.get("count"))


if __name__ == "__main__":
  redis_db = redis.StrictRedis(host="localhost", port=6379, db=0)
  Earth(redis_db).get_keywords("dose of colors liquid matte lipstick lot")
