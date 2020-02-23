import traceback
import tornado
import collections
import logging
import json

from checkin import auto_checkin


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
	#
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
			'reservations': self.reservations,
			'params': self.get_param_list(self.request.arguments)
		})


class CreateHandler(APIHandler):
	def initialize(self, reservations, threads):
		self.reservations = reservations
		self.threads = threads

	def get(self):
		self.set_header("Content-Type", "text/plain")
		self.write('Post it to me!')

	def post(self):
		self.set_header("Content-Type", "text/plain")
		first_name = self.get_body_argument("first_name")
		last_name = self.get_body_argument("last_name")
		reservation_number = self.get_body_argument("reservation_number")
		email_address = self.get_body_argument("email_address")
		self.write('Got it! {} {} {} {}'.format(first_name, last_name, reservation_number, email_address))


class DefaultHandler(APIHandler):
	def get(self):
		self.write_json({
			'self.request.headers': self.request.headers,
		})


class DebugHandler(APIHandler):
	def initialize(self, **kwargs):
		self.data = kwargs

	def get(self, endpoint):
		params = self.get_param_list(self.request.arguments)
		endpoint_mapping = {
			None: self.default,
			'inspect': self.inspect,
		}
		if endpoint in endpoint_mapping:
			try:
				endpoint_mapping[endpoint](params, callback=self.write_json)
			except Exception as e:
				logging.exception(e)
				self.write_json(traceback.format_exc())
		else:
			self.write_json({'error': 'Oops, address does not exist'})

	def default(self, params, callback):
		result = {
			'self.request.headers': self.request.headers,
			'self.current_user': self.current_user,
			'self.allowed_users': self.allowed_users,
			'self.allowed_groups': self.allowed_groups,
			'usage': 'inspect?property=(object_name)&attrs=[attribute_names]'
		}
		callback(result)

	def inspect(self, params, callback):
		attrs = params.get('attrs')
		property = params.get('property')

		if property:
			property_obj = self.data.get(property[0])
			if property_obj:
				if attrs:
					result = collections.OrderedDict()
					for attr in attrs:
						obj = getattr(property_obj, attr)
						if isinstance(obj, pd.DataFrame):
							obj = self.df_to_json_friendly_object(obj)
						elif isinstance(obj, collections.deque):
							obj = list(obj)
						elif isinstance(obj, dict):
							obj = self.unfriendly_dict_to_string_key_dict(obj)
						result[attr] = obj
					callback(result)
				else:
					callback(dir(property_obj))
			else:
				callback(dir(self.data))
		else:
			callback(dir(self.data))