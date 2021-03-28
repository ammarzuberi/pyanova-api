import requests
import random
import string


class AnovaCooker(object):
	"""Anova cooker object"""
	def __init__(self, device_id):
		"""Initialize all state variables and call update_state() to get current values from the API."""
		self.device_id = device_id
		self._jwt = None

		#---------------------------------------------
		# States that can be changed via the API
		#---------------------------------------------
		self.cook_time = None # Int (seconds)
		self.cook = None # Boolean
		self.target_temp = None # Float
		self.temp_display_unit = None # String ('C' for Celcius or 'F' for Farenheit)
		
		#---------------------------------------------
		# States that are read only via the API
		#---------------------------------------------
		# Job
		self.job_status = None # String
		self.job_time_remaining = None # Int

		# Duty cycle
		self.heater_duty_cycle = None # Float
		self.motor_duty_cycle = None # Float

		# WiFi
		self.wifi_connected = None # Boolean
		self.wifi_ssid = None # String
		
		# Safety
		self.device_safe = None # Boolean
		self.water_leak = None # Boolean
		self.water_level_critical = None # Boolean
		self.water_level_low = None # Boolean
		
		# Temperature
		self.heater_temp = None # Float
		self.triac_temp = None # Float
		self.water_temp = None # Float

		# Get initial state from Anova API
		self.update_state()


	def update_state(self):
		"""Get the device state and update local variables."""
		device_state = self.__get_raw_state()

		self.cook_time = int(device_state.get('job').get('cook-time-seconds'))
		self.cook = False if device_state.get('job').get('mode') == 'IDLE' else True
		self.target_temp = float(device_state.get('job').get('target-temperature'))
		self.temp_display_unit = str(device_state.get('job').get('temperature-unit'))

		self.job_status = str(device_state.get('job-status').get('state'))
		self.job_time_remaining = int(device_state.get('job-status').get('cook-time-remaining'))

		self.heater_duty_cycle = float(device_state.get('heater-control').get('duty-cycle'))
		self.motor_duty_cycle = float(device_state.get('motor-control').get('duty-cycle'))

		self.wifi_connected = True if device_state.get('network-info').get('connection-status') == 'connected-station' else False
		self.wifi_ssid = str(device_state.get('network-info').get('ssid'))

		self.device_safe = bool(device_state.get('pin-info').get('device-safe'))
		self.water_leak = bool(device_state.get('pin-info').get('water-leak'))
		self.water_level_critical = bool(device_state.get('pin-info').get('water-level-critical'))
		self.water_level_low = bool(device_state.get('pin-info').get('water-level-low'))

		self.heater_temp = float(device_state.get('temperature-info').get('heater-temperature'))
		self.triac_temp = float(device_state.get('temperature-info').get('triac-temperature'))
		self.water_temp = float(device_state.get('temperature-info').get('water-temperature'))


	def __get_raw_state(self):
		"""Get raw device state from the Anova API. This does not require authentication."""
		device_state_request = requests.get('https://anovaculinary.io/devices/{}/states/?limit=1&max-age=10s'.format(self.device_id))
		if device_state_request.status_code != 200:
			raise ConnectionError('Error connecting to Anova')

		device_state_body = device_state_request.json()
		if len(device_state_body) == 0:
			raise InvalidDeviceID('Invalid device ID')

		return device_state_body[0].get('body')
		

	def authenticate(self, email, password):
		"""Authenticate with Anova via Google Firebase."""
		ANOVA_FIREBASE_KEY = 'AIzaSyDQiOP2fTR9zvFcag2kSbcmG9zPh6gZhHw'

		# First authenticate with Firebase and get the ID token
		firebase_req_data = {
			'email': email,
			'password': password,
			'returnSecureToken': True
		}

		firebase_req = requests.post('https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={}'.format(ANOVA_FIREBASE_KEY), json = firebase_req_data)
		firebase_id_token = firebase_req.json().get('idToken')

		if not firebase_id_token:
			raise Exception('Could not log in with Google Firebase')

		# Now authenticate with Anova using the Firebase ID token to get the JWT
		anova_auth_req = requests.post('https://anovaculinary.io/authenticate', json = {}, headers = { 'firebase-token': firebase_id_token })
		jwt = anova_auth_req.json().get('jwt') # Looks like this JWT is valid for an entire year...

		if not jwt:
			raise AuthenticationError('Could not authenticate with Anova')

		# Set JWT local variable
		self._jwt = jwt

		return True


	def save(self):
		"""Push local state to the cooker via the API."""
		if not self._jwt:
			raise Exception('No JWT set - before calling save(), you must call authenticate(email, password)')

		# Convert boolean mode to COOK or IDLE for API
		cook_converted = 'COOK' if self.cook else 'IDLE'

		# Validate temperature unit
		if self.temp_display_unit not in ['F', 'C']:
			raise InvalidTemperature('Invalid temperature unit - only F or C are supported')

		# Validate cook time and target temperature
		if type(self.cook_time) != int:
			raise InvalidCooktime('Invalid cook time')
		if type(self.target_temp) != float:
			raise InvalidTargetTemperature('Invalid target temperature')

		# Now prepare and send the request
		anova_req_headers = {
			'authorization': 'Bearer ' + self._jwt
		}

		anova_req_data = {
			'cook-time-seconds': self.cook_time,
			'id': ''.join(random.choices(string.ascii_lowercase + string.digits, k = 22)), # 22 digit random job ID for a new job at every save
			'mode': cook_converted,
			'ota-url': '',
			'target-temperature': self.target_temp,
			'temperature-unit': self.temp_display_unit
		}

		anova_req = requests.put('https://anovaculinary.io/devices/{}/current-job'.format(self.device_id), json = anova_req_data, headers = anova_req_headers)
		if anova_req.status_code != 200:
			raise Exception('An unexpected error occurred')

		if anova_req.json() != anova_req_data:
			raise Exception('An unexpected error occurred')

		return True



class InvalidTemperature(Exception):
	pass
class InvalidCooktime(Exception):
	pass
class InvalidTargetTemperature(Exception):
	pass
class InvalidDeviceID(Exception):
	pass
class ConnectionError(Exception):
	pass
class AuthenticationError(Exception):
	pass
