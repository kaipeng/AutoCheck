import os
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import json


class PrecisionFormatter(logging.Formatter):
	converter = datetime.datetime.fromtimestamp

	def formatTime(self, record, datefmt=None):
		ct = self.converter(record.created)
		if datefmt:
			s = ct.strftime(datefmt)
		else:
			t = ct.strftime("%Y-%m-%d %H:%M:%S")
			s = "%s,%03d" % (t, record.msecs)
		return s


def configure_logging(log_dir='logs', log_file=None, log_level='INFO', console_level='WARNING'):
	log_format = '%(asctime)s|%(levelname)s|%(name)s|%(message)s\t|%(module)s:%(funcName)s:%(lineno)s'
	log_datefmt = '%Y%m%d %H:%M:%S.%f'
	logger = logging.getLogger('')
	logger.setLevel(log_level)
	ch = logging.StreamHandler()
	ch.setLevel(console_level)
	ch.setFormatter(PrecisionFormatter(fmt=log_format, datefmt=log_datefmt))
	logger.addHandler(ch)
	if log_file:
		log_dir = os.path.expanduser(log_dir)
		if not os.path.exists(log_dir):
			os.makedirs(log_dir)
		fh = TimedRotatingFileHandler(log_file, when='midnight')
		fh.setLevel(log_level)
		fh.setFormatter(PrecisionFormatter(fmt=log_format, datefmt=log_datefmt))
		fh.suffix = '%Y-%m-%d.log'
		logger.addHandler(fh)
		fh.doRollover()