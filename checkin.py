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
import logging

CHECKIN_EARLY_SECONDS = 5

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

	reservation_dict = {
		'reservation': reservation,
		'leg_id_to_threads': leg_id_to_threads,
		'reservation_number': reservation_number,
		'first_name': first_name,
		'last_name': last_name,
		'email_address': email_address
	}
	return reservation_dict
