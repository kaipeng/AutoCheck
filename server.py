import json
import logging

import tornado
import tornado.httpclient
import tornado.httpserver
import tornado.httputil
import tornado.ioloop
import tornado.log
import tornado.web

from datetime import datetime
from datetime import timedelta
from dateutil.parser import parse
from docopt import docopt
from math import trunc
from pytz import utc
from southwest import Reservation, openflights
from threading import Thread
import sys
import time

from collections import OrderedDict


CHECKIN_EARLY_SECONDS = 5


import tornado
import logging
import math
import json
import decimal
import pandas as pd

class APIHandler(tornado.web.RequestHandler):
	def set_default_headers(self):
		if 'Origin' in self.request.headers:
			origin = self.request.headers['Origin']
			self.set_header("Access-Control-Allow-Origin", origin)

		self.set_header('Access-Control-Allow-Credentials', 'true')

	@staticmethod
	def get_param_list(params):
		param_list_dict = {}
		for k, v in params.items():
			param_list_dict[k] = []
			for arg_val in v:
				arg_val = arg_val.decode("utf-8")
				param_list_dict[k] += arg_val.split(',')
		return param_list_dict

	# @staticmethod
	# def json_serial(obj):
	# 	if obj is math.nan:
	# 		return None
	# 	elif isinstance(obj, decimal.Decimal):
	# 		return float(obj)
	# 	return str(obj)

	# @staticmethod
	# def df_to_json_friendly_object(df):
	# 	if df is not None and len(df) > 0:
	# 		# logging.debug('Friendlifying df:\n%s', df)
	# 		df = df.reset_index()
	# 		return df.where((pd.notnull(df)), None).to_dict(orient='records')
	# 	return None

	@staticmethod
	def unfriendly_dict_to_string_key_dict(unfriendly_dict):
		return {str(key): value for key, value in unfriendly_dict.items()}

	def write_json(self, obj):
		self.set_header('Content-Type', 'application/json')
		result_json = json.dumps(obj, default=self.json_serial)
		self.write(result_json)
		self.finish()


class ReservationsHandler(APIHandler):
    def initialize(self, reservations):
		self.reservations = reservations

	def get(self):
		self.write_json({
			'reservations': reservations,
		})

    def post(self):
        pass


def schedule_checkin(flight_time, reservation):
    checkin_time = flight_time - timedelta(days=1)
    current_time = datetime.utcnow().replace(tzinfo=utc)
    # check to see if we need to sleep until 24 hours before flight
    if checkin_time > current_time:
        # calculate duration to sleep
        delta = (checkin_time - current_time).total_seconds() - CHECKIN_EARLY_SECONDS
        # pretty print our wait time
        m, s = divmod(delta, 60)
        h, m = divmod(m, 60)
        logging.info("Too early to check in.  Waiting {} hours, {} minutes, {} seconds".format(trunc(h), trunc(m), s))
        try:
            time.sleep(delta)
        except OverflowError:
            logging.info("System unable to sleep for that long, try checking in closer to your departure date")
            #sys.exit(1)
    data = reservation.checkin()
    for flight in data['flights']:
        for doc in flight['passengers']:
            logging.info("{} got {}{}!".format(doc['name'], doc['boardingGroup'], doc['boardingPosition']))


def auto_checkin(reservation_number, first_name, last_name, email_address=None, verbose=True):
    reservation = Reservation(reservation_number, first_name, last_name, verbose)
    body = reservation.lookup_existing_reservation()

    # Get our local current time
    now = datetime.utcnow().replace(tzinfo=utc)
    tomorrow = now + timedelta(days=1)

    leg_id_to_threads = dict()

    # find all eligible legs for checkin
    for leg in body['bounds']:
        # calculate departure for this leg
        airport = "{}, {}".format(leg['departureAirport']['name'], leg['departureAirport']['state'])
        takeoff = "{} {}".format(leg['departureDate'], leg['departureTime'])
        departure_airport = leg['departureAirport']['code']
        destination_airport = leg['destinationAirport']['code']
        airport_tz = openflights.timezone_for_airport(leg['departureAirport']['code'])
        date = airport_tz.localize(datetime.strptime(takeoff, '%Y-%m-%d %H:%M'))

        leg_id = '{}.{}.{}.{}.{}.{}'.format(reservation_number, first_name, last_name, departure_airport, destination_airport, takeoff)
        if date > now:
            # found a flight for checkin!
            logging.info("Flight information found, departing {} at {}".format(airport, date.strftime('%b %d %I:%M%p')))
            # Checkin with a thread
            t = Thread(target=schedule_checkin, args=(date, reservation))
            t.daemon = True
            t.start()
            leg_id_to_threads[leg_id] = t

    reservation = {
        'reservation': reservation,
        'leg_id_to_threads': leg_id_to_threads,
        'reservation_number': reservation_number,
        'first_name': first_name,
        'last_name': last_name,
        'email_address': email_address
    }
    return reservation

'''
CONFIRMATION_NUMBER, FIRST_NAME, LAST_NAME
    email_address
    reservation_object
    legs
    leg_id_to_thread
        leg_id = 'reservation_number.first_name.last_name.departure_airport.destination_airport.takeoff'

'''

def clean_up_threads(threads):
    for t in threads:
        t.join(5)
        if not t.isAlive():
            threads.remove(t)

RESERVATIONS_FILE = 'reservations.txt'

def save_file(reservations):
    with open(RESERVATIONS_FILE, 'w') as f:
        for reservation_id, reservation in reservations.items():
            line = ','.join(reservations['reservation_number'], reservations['first_name'], reservations['last_name'], reservations['email_address'])
            f.write(line)

def open_file():
    with open(RESERVATIONS_FILE, 'r') as f:
        lines = f.readlines()
        for line in lines:
            reservation_number, first_name, last_name, email_address = line.split(',')
            auto_checkin(reservation_number=reservation_number, first_name=first_name, last_name=last_name, email_address=email_address)

def periodic_task(threads, reservations):
    clean_up_threads(threads)
    save_file(reservations)

@tornado.gen.coroutine
def init_sequence(threads, reservations)
    periodic_task = tornado.ioloop.PeriodicCallback(
		io_loop=io_loop,
		callback=functools.partial(periodic_task, threads=threads, reservations=reservations),
		callback_time=10000)
	periodic_task.start()
    open_file()

def run():
	define('port', type=int, default=8000)

	define('file_log_level', type=str, default='DEBUG')
	define('console_log_level', type=str, default='INFO')
	define('log_file', type=str, default='logs/AutoCheck')

	options.logging = None
	parse_command_line()

	configure_logging(log_file=options.log_file, file_log_level=options.file_log_level, console_log_level=options.console_log_level)
	io_loop = tornado.ioloop.IOLoop()

    threads = []
    reservations = OrderedDict()

	init_sequence(threads=threads, reservations=reservations)

	handlers = [
		tornado.web.url(r'/static/?(.*)?', tornado.web.StaticFileHandler,
		                {'path': 'static', 'default_filename': 'index.html'}),

		tornado.web.url(r'/create/?(.*)?', tornado.web.StaticFileHandler,
		                {'path': 'static', 'default_filename': 'index.html'}),
        tornado.web.url(r'/reservations/?(.*)?', tornado.web.StaticFileHandler,
		                {'path': 'static', 'default_filename': 'index.html'}),
	]

	settings = {
		'debug': False,
	}
	applicaton = tornado.web.Application(handlers, **settings)
	applicaton.listen(options.port)

	try:
		io_loop.start()
	finally:
		logging.info('Shutting down.')

if __name__ == '__main__':
	run()
