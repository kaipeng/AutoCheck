import json
import logging

import tornado
import tornado.httpclient
import tornado.httpserver
import tornado.httputil
import tornado.ioloop
import tornado.log
import tornado.web
from tornado.options import define, options, parse_command_line

import functools
from collections import OrderedDict


from utils import configure_logging
from handlers import CreateHandler, ReservationsHandler
from checkin import auto_checkin

RESERVATIONS_FILE = 'reservations.txt'


def clean_up_threads(threads):
	for t in threads:
		t.join(5)
		if not t.isAlive():
			threads.remove(t)

def save_file(reservations):
	with open(RESERVATIONS_FILE, 'w+') as f:
		for reservation_id, reservation in reservations.items():
			line = ','.join(reservations['reservation_number'], reservations['first_name'], reservations['last_name'], reservations['email_address'])
			f.write(line)

def open_file(threads, reservations):
	with open(RESERVATIONS_FILE, 'w+') as f:
		pass
	with open(RESERVATIONS_FILE, 'r') as f:
		lines = f.readlines()
		for line in lines:
			logging.info('Adding reservation from file: {}'.format(line))
			reservation_number, first_name, last_name, email_address = line.split(',')
			#result = auto_checkin(reservation_number=reservation_number, first_name=first_name, last_name=last_name, email_address=email_address)

def periodic_task(threads, reservations):
	clean_up_threads(threads)
	save_file(reservations)

def init_sequence(threads, reservations):
	periodic_callback = tornado.ioloop.PeriodicCallback(callback=functools.partial(periodic_task, threads=threads, reservations=reservations), callback_time=10000)
	periodic_callback.start()
	open_file(threads, reservations)

def run():
	define('port', type=int, default=8000)

	define('log_level', type=str, default='INFO')
	define('log_file', type=str, default='logs/AutoCheck')

	options.logging = None
	parse_command_line()

	configure_logging(log_file=options.log_file, log_level=options.log_level)
	io_loop = tornado.ioloop.IOLoop()

	threads = []
	reservations = OrderedDict()

	init_sequence(threads=threads, reservations=reservations)

	handlers = [
		tornado.web.url(r'/?(.*)?', tornado.web.StaticFileHandler,
		                {'path': 'static', 'default_filename': 'index.html'}),
		tornado.web.url(r'/create/?(.*)?', CreateHandler,
		                {'reservations': reservations, 'threads': threads}),
		tornado.web.url(r'/reservations/?(.*)?', ReservationsHandler,
		                {'reservations': reservations}),
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
