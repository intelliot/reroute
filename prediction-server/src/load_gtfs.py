import sys
import transitfeed
import tz
import time
import datetime
import tornado.ioloop
import tornado.web  # docs: http://www.tornadoweb.org/documentation/web.html
import tornado.gen
import json


"""
|  GetAgency(self, agency_id)
|      Return Agency with agency_id or throw a KeyError
|  
|  GetAgencyList(self)
|      Returns the list of Agency objects known to this Schedule.
|  
|  GetDateRange(self)
|      Returns a tuple of (earliest, latest) dates on which the service periods
|      in the schedule define service, in YYYYMMDD form.
|  
|  GetDateRangeWithOrigins(self)
|      Returns a tuple of (earliest, latest, earliest_origin, latest_origin)
|      dates on which the service periods in the schedule define service, in
|      YYYYMMDD form.
|      The origins specify where the earliest or latest dates come from. In
|      particular, whether the date is a regular ServicePeriod start_date or
|      end_date in calendar.txt, a service exception of type add in
|      calendar_dates.txt, or feed start/end date defined in feed_info.txt.
|  
|  GetDefaultAgency(self)
|      Return the default Agency. If no default Agency has been set select the
|      default depending on how many Agency objects are in the Schedule. If there
|      are 0 make a new Agency the default, if there is 1 it becomes the default,
|      if there is more than 1 then return None.
|  
|  GetDefaultServicePeriod(self)
|      Return the default ServicePeriod. If no default ServicePeriod has been
|      set select the default depending on how many ServicePeriod objects are in
|      the Schedule. If there are 0 make a new ServicePeriod the default, if there
|      is 1 it becomes the default, if there is more than 1 then return None.
|  
|  GetFare(self, fare_id)
|      Deprecated. Please use GetFareAttribute instead
|  
|  GetFareAttribute(self, fare_id)
|  
|  GetFareAttributeList(self)
|
|  GetFareZones(self)
|      Returns the list of all fare zones that have been identified by
|      the stops that have been added.
|  
|  GetNearestStops(self, lat, lon, n=1)
|      Return the n nearest stops to lat,lon
|  
|  GetRoute(self, route_id)
|  
|  GetRouteList(self)
|  
|  GetServicePeriod(self, service_id)
|      Returns the ServicePeriod object with the given ID.
|  
|  GetServicePeriodList(self)
|  
|  GetServicePeriodsActiveEachDate(self, date_start, date_end)
|      Return a list of tuples (date, [period1, period2, ...]).
|      
|      For each date in the range [date_start, date_end) make list of each
|      ServicePeriod object which is active.
|      
|      Args:
|        date_start: The first date in the list, a date object
|        date_end: The first date after the list, a date object
|      
|      Returns:
|        A list of tuples. Each tuple contains a date object and a list of zero or
|        more ServicePeriod objects.
|  
|  GetShape(self, shape_id)
|  
|  GetShapeList(self)
|  
|  GetStop(self, id)
|  
|  GetStopBoundingBox(self)
|  
|  GetStopList(self)
|  
|  GetStopsInBoundingBox(self, north, east, south, west, n)
|      Return a sample of up to n stops in a bounding box
|  
|  GetTableColumns(self, table)
|      Return list of columns in a table.
|  
|  GetTransferIter(self)
|      Return an iterator for all Transfer objects in this schedule.
|  
|  GetTransferList(self)
|      Return a list containing all Transfer objects in this schedule.
|  
|  GetTrip(self, trip_id)
|  
|  GetTripList(self)
"""
def getActiveServicePeriod(s, timestamp):
  datestr = datetime.datetime.fromtimestamp(timestamp, tz.Pacific).strftime("%Y%m%d")
  periods = s.GetServicePeriodList()
  return [x.service_id for x in periods if datestr in x.ActiveDates()][0]

def timestampToTimeOfDay(timestamp):
  t = datetime.datetime.fromtimestamp(timestamp, tz.Pacific).time()
  return (t.hour * 60 + t.minute)*60 + t.second
def timeOfDayToTimestamp(ref_timestamp, seconds):
  d = datetime.datetime.fromtimestamp(ref_timestamp, tz.Pacific).date()
  t = datetime.time(seconds/60/60, (seconds/60)%60, seconds%60, tzinfo=tz.Pacific)
  return int(time.mktime(datetime.datetime.combine(d, t).astimezone(tz.UTC()).timetuple()))

def getSchedule(s, route, start_ts, stop_ts, lat1, lon1, lat2, lon2):
  service_id = getActiveServicePeriod(s, start_ts)
  possible_routes = set([x.route_id for x in s.GetRouteList() if x.route_short_name.lower() == route.lower()])
  trips_with_route = [x for x in s.GetTripList() if x.service_id == service_id and x.route_id in possible_routes]
  trips = []
  min_time = timestampToTimeOfDay(start_ts)
  max_time = timestampToTimeOfDay(stop_ts)
  if not lat2 and not lon2:
    for trip in trips_with_route:
      timestops = trip.GetTimeStops()
      (arrival_secs, departure_secs, stop) = timestops[-1]
      if not (min_time <= departure_secs <= max_time):
        continue
      dist = transitfeed.util.ApproximateDistance(lat1, lon1, stop.stop_lat, stop.stop_lon)
      if dist > 50:
        continue
      trips.append(departure_secs)
  else:
    for trip in trips_with_route:
      timestops = trip.GetTimeStops()
      if timestops[0][1] > max_time:
        continue
      if timestops[-1][1] < min_time:
        continue
      for (i, (arrival_secs, departure_secs, stop)) in enumerate(timestops[:-1]):
        dist = transitfeed.util.ApproximateDistance(lat1, lon1, stop.stop_lat, stop.stop_lon)
        if dist > 10:
          continue
        _, _, nextStop = timestops[i + 1]
        dist2 = transitfeed.util.ApproximateDistance(lat2, lon2, nextStop.stop_lat, nextStop.stop_lon)
        if dist > 10:
          continue;
        
        trips.append((trip.trip_id, departure_secs))
        #print trip
        break
  # GetTimeStops or GetStopTimes?
  return [{"tripTag": trip_id, "scheduledTime": timeOfDayToTimestamp(start_ts, seconds)} for (trip_id, seconds) in trips]
  # e.g. getSchedule(s, '44', 1350761830, 1350762000, 37.7363199, -122.39862, 37.7370999, -122.3966299)
  # 44 inbound at forest hill:
  # getSchedule(s, '44', 1350835200, 1350840600, 37.7483299, 122.45884, 37.75095, -122.46105)
class MainHandler(tornado.web.RequestHandler):
  def initialize(self, s):
    self.s = s
  def get(self, route, start_ts, stop_ts, lat1, lon1, lat2, lon2):
    (lat1, lon1, lat2, lon2) = (float(lat1), float(lon1), float(lat2), float(lon2))
    (start_ts, stop_ts) = (int(start_ts), int(stop_ts))
    route = str(route)
    times = getSchedule(self.s, route, start_ts, stop_ts, lat1, lon1, lat2, lon2)
    self.finish(json.dumps(times))

s = transitfeed.Schedule()
s.Load("../muni_gtfs")
def main():
  agency = s.GetAgency("SFMTA")
  application = tornado.web.Application([
    (r"/([^/]+)/(\d+)/(\d+)/([0-9.-]+)/([0-9.-]+)/([0-9.-]+)/([0-9.-]+)", MainHandler, {"s": s}),
  ])
  port = 8887
  application.listen(port)
  print "Starting to serve"
  tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()
  