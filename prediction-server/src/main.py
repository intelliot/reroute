#!/usr/bin/python
import tornado.ioloop
import tornado.web  # docs: http://www.tornadoweb.org/documentation/web.html
import transitfeed  # docs: http://code.google.com/p/googletransitdatafeed/wiki/TransitFeed
import sys
import json
#import MySQLdb
import tornado.httpclient
import tornado.gen
import os
import xml.etree.ElementTree as ET
import time

class AnnouncementHandler(tornado.web.RequestHandler):
  def initialize(self, db):
    self.db = db
  def get(self, *criteria):
    c = self.db.cursor()
    (route_id, stop_id, time, _) = criteria
    if route_id is None:
      query = "select * from announcements_by_stop;"
      params = ()
    elif route_id and stop_id and time is None:
      query = "select * from announcements_by_stop where route_id=%s and stop_id=%s;"
      params = criteria
    elif route_id and stop_id and time:
      (route_id, stop_id, time) = criteria
      query = "select * from announcements_by_stop where route_id=%s and stop_id=%s and start_time_min <= %s and %s <= stop_time_min;"
      params = (route_id, stop_id, time, time)
    else:
      raise Exception(criteria)
    c.execute(query, params)
    data = c.fetchall()
    cleaned = [{"route_id": x[0], "stop_id": x[1], "start_time": x[2], "stop_time": x[3], "announcement": x[4]} for x in data]
    self.set_header("Content-type", "application/json")
    self.set_header("Access-Control-Allow-Origin", "*")
    self.write(json.dumps(cleaned) + '\n')
    self.finish()
  def post(self, *criteria):
    # curl -X POST localhost:8888/announcement/1/2/3/4 -d "announcement=hi"
    (route_id, stop_id, start_time, stop_time) = criteria
    announcement = self.get_argument("announcement")
    params = (route_id, stop_id, start_time, stop_time, announcement)
    assert route_id
    assert stop_id
    assert start_time
    assert stop_time
    assert announcement
    query = "insert into announcements_by_stop set route_id=%s, stop_id=%s, start_time_min=%s, stop_time_min=%s, announcement=%s;"
    c = self.db.cursor()
    c.execute(query, params)
    self.db.commit()
    self.finish()
class AlertHandler(tornado.web.RequestHandler):
  def initialize(self, db):
    self.db = db
  def get(self, user):
    c = self.db.cursor()
    c.execute("select * from subscriptions where user=%s;", (user,))
    data = c.fetchall()
    self.write(json.dumps(data))
    self.finish()
  def put(self, user, route_id, stop_id, start_time_min, stop_time_min):
    c = self.db.cursor()
    c.execute("insert into subscriptions set user=%s, route_id=%s, stop_id=%s, start_time_min=%s, stop_time_min=%s;", (user, route_id, stop_id, start_time_min, stop_time_min))
    #self.stream.read_bytes(self.content_length, self.parse_json)
    self.db.commit()
    self.finish()
  def put_json(self, data):
    json.loads(data)



class MainHandler(tornado.web.RequestHandler):
  def get(self):
    self.finish("Hello, world.")


class RouteCache(object):
  def __init__(self):
    self.routecache = {}  # route_tag -> route info
  def getRouteConfig(self, route_tag, callback):
    cb = callback  # TODO: rename
    if route_tag in self.routecache:
      return cb((None, self.routecache[route_tag]))
    url = "http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=sf-muni&r=%s" % (route_tag)
    http_client = tornado.httpclient.AsyncHTTPClient()
    def handle_request(response):
      if response.error:
        cb((response.error, None))
      else:
        root = ET.fromstring(response.body)
        routeelem = root.find("route")
        if not routeelem:
          raise Exception("Unexpected response to %s: %s" % (url, response.body))
        children  = routeelem.getchildren()
        stops = {}
        directions = []  # {tag, name, title, stops}
        for child in children:
          attrib = child.attrib
          if child.tag == 'stop':
            stops[attrib.get('tag')] = attrib
            attrib["lat"] = float(attrib["lat"])
            attrib["lon"] = float(attrib["lon"])
          elif child.tag == "direction":
            directions.append(attrib)
            directionstops = []
            attrib["stops"] = directionstops
            for stop in child.findall("stop"):
              tag = stop.attrib.get("tag")
              stopinfo = stops.get(tag)
              directionstops.append(stopinfo)
          # ignore paths
        routeelem.attrib["directions"] = directions
        self.routecache[route_tag] = routeelem.attrib
        cb((None, routeelem.attrib))
    http_client.fetch(url, handle_request)

class RouteConfigHandler(tornado.web.RequestHandler):
  def initialize(self, routecache):
    self.routecache = routecache
  @tornado.web.asynchronous
  @tornado.gen.engine
  def get(self, route_tag):
    (err, routeinfo) = yield tornado.gen.Task(self.routecache.getRouteConfig, route_tag)
    if err:
      raise Exception(err)
    self.set_header("Content-type", "application/json")
    self.set_header("Access-Control-Allow-Origin", "*")
    self.finish(json.dumps(routeinfo))
    
class RouteListHandler(tornado.web.RequestHandler):
  def initialize(self):
    pass
  @tornado.web.asynchronous
  @tornado.gen.engine
  def get(self):
    self.set_header("Content-type", "application/json")
    self.set_header("Access-Control-Allow-Origin", "*")
    if False:
      url = "http://webservices.nextbus.com/service/publicXMLFeed?command=routeList&a=sf-muni"
      resp = yield tornado.gen.Task(http_client.fetch, url)
      if resp.error: raise resp.error
      root = ET.fromstring(x)
      routeelems = root.findall("route")
      self.finish(json.dumps([routeelem.attrib for routeelem in routeelems]))
    else:
      self.finish(json.dumps([
        {'tag': 'F', 'title': 'F-Market & Wharves'},
        {'tag': 'J', 'title': 'J-Church'},
        {'tag': 'KT', 'title': 'KT-Ingleside/Third Street'},
        {'tag': 'L', 'title': 'L-Taraval'},
        {'tag': 'M', 'title': 'M-Ocean View'},
        {'tag': 'N', 'title': 'N-Judah'},
        {'tag': 'NX', 'title': 'NX-N Express'},
        {'tag': '1', 'title': '1-California'},
        {'tag': '1AX', 'title': '1AX-California A Express'},
        {'tag': '1BX', 'title': '1BX-California B Express'},
        {'tag': '2', 'title': '2-Clement'},
        {'tag': '3', 'title': '3-Jackson'},
        {'tag': '5', 'title': '5-Fulton'},
        {'tag': '6', 'title': '6-Parnassus'},
        {'tag': '8X', 'title': '8X-Bayshore Exp'},
        {'tag': '8AX', 'title': '8AX-Bayshore A Exp'},
        {'tag': '8BX', 'title': '8BX-Bayshore B Exp'},
        {'tag': '9', 'title': '9-San Bruno'},
        {'tag': '9L', 'title': '9L-San Bruno Limited'},
        {'tag': '10', 'title': '10-Townsend'},
        {'tag': '12', 'title': '12-Folsom/Pacific'},
        {'tag': '14', 'title': '14-Mission'},
        {'tag': '14L', 'title': '14L-Mission Limited'},
        {'tag': '14X', 'title': '14X-Mission Express'},
        {'tag': '16X', 'title': '16X-Noriega Express'},
        {'tag': '17', 'title': '17-Park Merced'},
        {'tag': '18', 'title': '18-46th Avenue'},
        {'tag': '19', 'title': '19-Polk'},
        {'tag': '21', 'title': '21-Hayes'},
        {'tag': '22', 'title': '22-Fillmore'},
        {'tag': '23', 'title': '23-Monterey'},
        {'tag': '24', 'title': '24-Divisadero'},
        {'tag': '27', 'title': '27-Bryant'},
        {'tag': '28', 'title': '28-19th Avenue'},
        {'tag': '28L', 'title': '28L-19th Avenue Limited'},
        {'tag': '29', 'title': '29-Sunset'},
        {'tag': '30', 'title': '30-Stockton'},
        {'tag': '30X', 'title': '30X-Marina Express'},
        {'tag': '31', 'title': '31-Balboa'},
        {'tag': '31AX', 'title': '31AX-Balboa A Express'},
        {'tag': '31BX', 'title': '31BX-Balboa B Express'},
        {'tag': '33', 'title': '33-Stanyan'},
        {'tag': '35', 'title': '35-Eureka'},
        {'tag': '36', 'title': '36-Teresita'},
        {'tag': '37', 'title': '37-Corbett'},
        {'tag': '38', 'title': '38-Geary'},
        {'tag': '38AX', 'title': '38AX-Geary A Express'},
        {'tag': '38BX', 'title': '38BX-Geary B Express'},
        {'tag': '38L', 'title': '38L-Geary Limited'},
        {'tag': '39', 'title': '39-Coit'},
        {'tag': '41', 'title': '41-Union'},
        {'tag': '43', 'title': '43-Masonic'},
        {'tag': '44', 'title': "44-O'Shaughnessy"},
        {'tag': '45', 'title': '45-Union/Stockton'},
        {'tag': '47', 'title': '47-Van Ness'},
        {'tag': '48', 'title': '48-Quintara - 24th Street'},
        {'tag': '49', 'title': '49-Mission-Van Ness'},
        {'tag': '52', 'title': '52-Excelsior'},
        {'tag': '54', 'title': '54-Felton'},
        {'tag': '56', 'title': '56-Rutland'},
        {'tag': '66', 'title': '66-Quintara'},
        {'tag': '67', 'title': '67-Bernal Heights'},
        {'tag': '71', 'title': '71-Haight-Noriega'},
        {'tag': '71L', 'title': '71L-Haight-Noriega Limited'},
        {'tag': '76', 'title': '76-Marin Headlands'},
        {'tag': '80X', 'title': '80X-Gateway Express'},
        {'tag': '81X', 'title': '81X-Caltrain Express'},
        {'tag': '82X', 'title': '82X-Levi Plaza Express'},
        {'tag': '83X', 'title': '83X-Caltrain'},
        {'tag': '88', 'title': '88-B.A.R.T. Shuttle'},
        {'tag': '90', 'title': '90-San Bruno Owl'},
        {'tag': '91', 'title': '91-Owl'},
        {'tag': '108', 'title': '108-Treasure Island'},
        {'tag': 'K OWL', 'title': 'K-Owl'},
        {'tag': 'L OWL', 'title': 'L-Owl'},
        {'tag': 'M OWL', 'title': 'M-Owl'},
        {'tag': 'N OWL', 'title': 'N-Owl'},
        {'tag': 'T OWL', 'title': 'T-Owl'},
        {'tag': '59', 'title': 'Powell/Mason Cable Car'},
        {'tag': '60', 'title': 'Powell/Hyde Cable Car'},
        {'tag': '61', 'title': 'California Cable Car'}
        ]))
      
    
class NextMuniHandler(tornado.web.RequestHandler):
  def initialize(self, routecache):
    self.routecache = routecache
  @tornado.web.asynchronous
  @tornado.gen.engine
  def get(self, stop_id, route_tag):
    assert stop_id
    assert route_tag  # for now, require a route
    http_client = tornado.httpclient.AsyncHTTPClient()
    (err, routeinfo) = yield tornado.gen.Task(self.routecache.getRouteConfig, route_tag)
    if err: raise Exception(err)
    scheduledtimeurl = None
    for direction in routeinfo["directions"]:
      for (i, stop) in enumerate(direction["stops"]):
        if stop_id != stop["stopId"]:
          continue
        (lat1, lon1) = (stop["lat"], stop["lon"])
        if i < len(direction["stops"]):
          nextstop = direction["stops"][i + 1]
          (lat2, lon2) = (nextstop["lat"], nextstop["lon"])
        else:
          (lat2, lon2) = (0, 0)
        now = int(time.time())
        scheduledtimeurl = "http://localhost:8887/%s/%s/%s/%s/%s/%s/%s" % (route_tag, now - 60*10, now + 60*90, lat1, lon1, lat2, lon2)
        # TODO: muiltple? 
    if not scheduledtimeurl:
      raise Exception("couldn't find stop %d in %s" % (stop_id, routeinfo["directions"]))
    url = "http://webservices.nextbus.com/service/publicXMLFeed?command=predictions&a=sf-muni&stopId=%s&routeTag=%s" % (stop_id, route_tag)
    (scheduleresp, predictionsresp) = yield [tornado.gen.Task(http_client.fetch, scheduledtimeurl), tornado.gen.Task(http_client.fetch, url)]
    if scheduleresp.error: raise Exception(scheduleresp.error)
    if predictionsresp.error: raise Exception(predictionsresp.error)
    schedulelist = json.loads(scheduleresp.body)
    for x in schedulelist:
      x["scheduledTime"] = x["scheduledTime"] * 1000  #### Use ms instead of s
    

    root = ET.fromstring(predictionsresp.body)
    predictionselem = root.find("predictions")
    directions = []
    if not predictionselem:
      raise Exception("No directions for %s in %s" % (url, predictionsresp.body))
    for directionelem in [child for child in predictionselem.getchildren() if child.tag == "direction"]:
      predictionelems = [child for child in directionelem.getchildren() if child.tag == "prediction"]
      directionelem.attrib["predictions"] = predictions = []
      directions.append(directionelem.attrib)
      for predictionelem in predictionelems:
        pred = predictionelem.attrib
        predictions.append(pred)
        pred["epochTime"] = int(pred["epochTime"])
        # del pred["seconds"]
        # del pred["minutes"]
        for i, x in enumerate(schedulelist):
          if x.get("tripTag") != pred.get("tripTag"):
            continue
          pred["scheduledTime"] = x["scheduledTime"]
          schedulelist[i:i+1] = []
          break
    for x in schedulelist:
      i = 0
      while i < len(directions[0]["predictions"]):
        pred = directions[0]["predictions"][i]
        if "epochTime" in pred: t = pred["epochTime"]
        else: t = pred["scheduledTime"]
        if t > x["scheduledTime"]:
          break
        i += 1
      directions[0]["predictions"].insert(i, x)
    self.set_header("Content-type", "application/json")
    self.set_header("Access-Control-Allow-Origin", "*")
    self.finish(json.dumps(directions))

if False:
  db = MySQLdb.connect(db="muni", user="muni")
routecache = RouteCache()
application = tornado.web.Application([
  (r"/", MainHandler),
#  (r"/alert/user/([^/]+)(?:/(\d+)/(\d+)/(\d+)/(\d+))", AlertHandler, {"db":db}),
#  (r"/announcement(?:/(\d+)/(\d+)(?:/(\d+)(?:/(\d+))?)?)?", AnnouncementHandler, {"db":db}),
  (r"/routelist", RouteListHandler),
  (r"/routeconfig/([^/]+)", RouteConfigHandler, {"routecache": routecache}),
  (r"/prediction/([^/]+)/([^/]+)", NextMuniHandler, {"routecache": routecache}),
  (r"/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__), "static")}),
], debug=True)

if __name__ == "__main__":
  port = 8888
  if len(sys.argv) >= 2 and sys.argv[1] == '--prod':
    port = 80
  application.listen(port)
  tornado.ioloop.IOLoop.instance().start()