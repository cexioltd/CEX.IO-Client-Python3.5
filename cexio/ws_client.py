"""
The :mod:`cexio.ws_client` module handles
basic CEX.IO WebSocket futures, connectivity, authentication, reconnecting, exception handling,
and basic functionality to build event model
CommonWebSocketClient
WebSocketClientSingleCallback
"""
import asyncio
import websockets
import websockets.http
import datetime
import hashlib
import hmac
import logging
import json
from asyncio import *
import random
import sys

from .exceptions import *
from .messaging import *

from .protocols_config import protocols_config
from .version import version


__all__ = [
	'CommonWebSocketClient',
	'WebSocketClientSingleCallback',
]


logger = logging.getLogger(__name__)


# Assert that required algorithm implemented
assert 'sha256' in hashlib.algorithms_guaranteed


# A WebSocketClient state:
CLOSED, CONNECTING, OPEN, READY = range(4)


class CEXWebSocketAuth:
	"""
	"""
	#

	# JSON template dict
	_json = {
		'e': 'auth',
		'auth': {
			'key': None,
			'signature': None,
			'timestamp': None,
		},
		'oid': 'auth',
	}

	def __init__(self, config):
		try:
			self._key = config['auth']['key']
			self._secret = config['auth']['secret']

		except KeyError as ex:
			raise ConfigError('Missing key in _config file', ex)

	def get_curr_timestamp(self):
		return int(datetime.datetime.now().timestamp())

	def get_timed_signature(self):
		"""
		Returns UNIX timestamp in seconds, and 'timed' signature,
		which is the digest of byte string, compound of timestamp and public key
		"""
		timestamp = self.get_curr_timestamp()
		message = "{}{}".format(timestamp, self._key)
		return timestamp, hmac.new(self._secret.encode(), message.encode(), hashlib.sha256).hexdigest()

	def get_request(self):
		"""
		Returns JSON from self._json dict
		The request is valid within ~20 seconds
		"""
		timestamp, signature = self.get_timed_signature()
		self._json['auth']['key'] = self._key
		self._json['auth']['signature'] = signature
		self._json['auth']['timestamp'] = timestamp
		return self._json


class CommonWebSocketClient:
	"""
	"""

	# Append CEXIO client API version to 'user_agent' http header value
	websockets.http.USER_AGENT = ' '.join((websockets.http.USER_AGENT, "cexio/{}".format(version)))

	def __init__(self, config):
		try:
			_config = config.copy()
			if 'auth' in _config.keys():
				_config['auth'] = "{***}"
			logger.info("WS> User Agent: {}".format(websockets.http.USER_AGENT))
			logger.debug("WS> CEXWebSocketClientProtocol with _config: {}".format(_config))

			self.ws = None
			self.state = CLOSED

			self._send_subscriptions = list()
			self._request_subscriptions = list()

			self._uri = config['ws']['uri']
			self._need_auth = config['authorize']

			self._timeout = protocols_config['ws']['timeout']
			self._protocol_timeout = protocols_config['ws']['protocol_timeout']
			self._ensure_alive_timeout = protocols_config['ws']['ensure_alive_timeout']
			self._reconnect = protocols_config['ws']['reconnect']
			self._reconnect_interval = lambda: 0.1 + random.randrange(300) / 100
			self._resend_subscriptions = protocols_config['ws']['resend_subscriptions']
			self._resend_requests = protocols_config['ws']['resend_requests']

			if self._need_auth:
				self._auth = CEXWebSocketAuth(config)

			# Message map for special messages, received while running
			special_message_map = (
				({	'e': 'connected', },										self._on_connected),
				({	'ok': 'error', 'data': {'error': 'Please Login'}, },		self._on_not_authenticated),
				({	'e': 'ping', },												self._on_ping),
				({	'e': 'disconnecting', },									self._on_disconnecting),
			)
			self._router = self._base_router = MessageRouter(special_message_map)
			self._resolver = None

			self._connecting_lock = Lock()
			self._listener_task = None
			self._routing_on = None
			self._send_error = Future()

		except KeyError as ex:
			raise ConfigError('Missing key in _config file', ex)

	def set_router(self, router):
		self._router = self._base_router.bind(router)

	def set_resolver(self, resolver):
		self._resolver = resolver

	# User methods
	# ------------

	async def connect(self):
		try:
			if self.state != CLOSED:
				return

			self.ws = await wait_for(websockets.connect(self._uri), self._timeout)
			self.ws.timeout = self._protocol_timeout

			if not self._send_error.done():
				self._send_error.cancel()
			self._send_error = Future()

			message = await self.recv()
			if message_equal_or_greater(message, {'e': 'connected', }):
				logger.info('WS> Client Connected')
			else:
				raise ProtocolError("WS> Client Connection failed: {}".format(message))

			if self._need_auth:
				await self._authorize()

			self.state = OPEN

		except Exception as ex:
			logger.info("{} (\'{}\') while connecting".format(ex.__class__.__name__, ex))
			try:
				if self.ws is not None:
					await wait_for(self.ws.close_connection(), self._timeout)
			except Exception as ex1:
				logger.error("Exception at close_connection: {}".format(ex1))
			raise ex

	async def run(self):
		assert self._router is not None
		assert self._resolver is not None

		await self.connect()
		if self._routing_on is None:
			self._routing_on = ensure_future(self._routing())

		logger.debug('WS.Client> Routing started')

	async def stop(self):
		if self._routing_on is not None and not self._routing_on.done():
			self._routing_on.cancel()

		if self._listener_task is not None and not self._listener_task.done():
			self._listener_task.cancel()

		logger.debug('WS.Client> Routing stopped')
		self.state = CLOSED
		await wait_for(self.ws.close(), self._timeout)

	async def send(self, message):
		await self._connecting_lock.acquire()
		try:
			await self._send(message)
		except Exception as ex:
			raise
		finally:
			self._connecting_lock.release()

	async def recv(self):
		# call recv() without timeout, used only in _routing()
		return await wait_for(self._recv(), self._timeout)

	async def request(self, message):
		# Returns resolved and processed response data in future
		future = Future()
		try:
			request = self._resolver.mark(message, future)
			await self.send(request)
		except Exception as ex:
			future.set_exception(ex)
		return await wait_for(future, self._timeout)

	async def send_subscribe(self, message):
		# saving subscription requests to subscribe after reconnect
		self._send_subscriptions.append(message)
		await self.send(message)

	async def request_subscribe(self, message):
		# saving subscription requests to subscribe after reconnect
		self._request_subscriptions.append(message)
		return await self.request(message)

	# Internals
	# ---------

	async def _send(self, message):
		if isinstance(message, dict):
			message = json.dumps(message)

		logger.debug("WS.Client> {}".format(message))

		try:
			await wait_for(self.ws.send(message), self._timeout)
		except Exception as ex:
			self._send_error.set_exception(ex)  # signal to _routing() coro, which will reconnect() od stop()
			raise ConnectivityError(ex)  # signal error to client call

	async def _recv(self):
		# call ws.recv() without timeout, used only in _routing() and in tests
		# not supposed to be called while running,
		# it will simply grab the message from the queue - not exactly the one expected
		message = await self.ws.recv()
		try:
			message = json.loads(message)
		except Exception as ex:
			raise ProtocolError(ex)

		logger.debug("WS.Server> {}".format(message))
		return message

	async def _authorize(self):
		await self._send(self._auth.get_request())
		response = await self.recv()
		if message_equal_or_greater(response, {'e': 'auth', 'ok': 'ok', 'data': {'ok': 'ok'}, }):
			logger.info('WS> User Authorized')

		elif message_equal(response, {'e': 'auth', 'ok': 'error', 'data': {'error': None}, }):
			raise AuthError("WebSocketConnection Authentication failed: {}".format(response['data']['error']))
		else:
			raise ProtocolError("WebSocketConnection Authentication failed: {}".format(response))

	async def _routing(self):
		while True:
			self._listener_task = ensure_future(self._recv())

			done, pending = await wait(
				[self._routing_on, self._listener_task, self._send_error],
				return_when=asyncio.FIRST_COMPLETED,
				timeout=self._ensure_alive_timeout)

			if self._routing_on in done:
				self._routing_on = None
				return

			elif self._send_error in done:
				logger.info("WS> Client disconnected while sending: {}".format(self._send_error.exception()))

				if not await self._on_disconnected():
					break

			elif self._listener_task in done:
				try:
					message = self._listener_task.result()
					await self._router(message)

				except ProtocolError:
					raise
				except CancelledError as ex:
					pass
				except Exception as ex:
					logger.info("WS> Client disconnected while receiving: {}".format(ex))

					if not await self._on_disconnected():
						break

			elif self._listener_task in pending:
				logger.info("WS> Client timeout")

				self._listener_task.cancel()
				if not await self._on_disconnected():
					break

	async def _on_disconnected(self):
		try:
			self.state = CLOSED
			self._send_error.cancel()
			await wait_for(self.ws.close(), self._timeout)

		except Exception as ex:
			logger.debug(ex)

		if self._reconnect:
			logger.info("WS> Reconnecting...")
			while True:
				try:
					await sleep(self._reconnect_interval())
					await self._connecting_lock.acquire()
					await self.connect()
					break
				except Exception as ex:
					logger.info(ex)
				finally:
					self._connecting_lock.release()

			ensure_future(self._after_connected())
			ret = True  # continue routing

		else:
			logger.info("WS> Client stopped")
			ret = False  # stop routing

		return ret

	async def _after_connected(self):
		try:
			if self._resend_subscriptions:
				for message in self._send_subscriptions:
					await self.send(message)
				for message in self._request_subscriptions:
					await self.request(message)

		except Exception as ex:
			logger.info(ex)

	# Special Message Callbacks
	# -------------------------

	async def _on_connected(self, message):
		logger.info('WS> WebSocket connection established')
		if self._need_auth:
			await self.send(self._auth.get_request())
		else:
			self.state = OPEN
		return message

	async def _on_not_authenticated(self, message):
		self.authorized = True
		logger.warn("WS> User Not Authenticated: {}".format(message))
		#TODO close , reconnect if was authorized
		return message

	async def _on_ping(self, message):
		await self.send({'e': 'pong'})
		return message

	async def _on_disconnecting(self, message):
		logger.info('WS> Disconnecting by Server')
		await self._on_disconnected()
		return message


class WebSocketClientSingleCallback(CommonWebSocketClient):

	def __init__(self, _config):
		super().__init__(_config)

		def validator(message):
			try:
				result = message['ok']
				if result == 'ok':
					return message['data']
				elif result == 'error':
					raise ErrorMessage(message['data']['error'])
				else:
					error = InvalidMessage(message)
			except KeyError:
				error = InvalidMessage(message)
			raise error

		resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
												 key_set_path='oid', key_get_path='oid')
		self.message_map = (
			({	'e': None,
				'data': None,
				'oid': None,
				'ok': None, }, resolver + validator),

			({	}, self.on_notification),
		)
		router = MessageRouter(self.message_map, sink=self.on_unhandled)
		self.set_router(router)
		self.set_resolver(resolver)
		self.__notification_future = None

	async def on_notification(self, message):
		# Supposed be redefined for the class or for the given object by user
		logger.debug("WS> Notification: {}".format(message))
		return message

	@staticmethod
	def format_message(e_name, data):
		message = {'e': e_name, }
		if data is not None:
			message['data'] = data
		return message

	@staticmethod
	async def on_error(message):
		logger.error("WS> Resolver not expected response: {}".format(message))
		return message

	@staticmethod
	async def on_unexpected_response(message):
		logger.warn("WS> Resolver not expected response: {}".format(message))
		return message  # pass back to the router to continue matching

	@staticmethod
	async def on_unhandled(message):
		logger.warn("WS> Unhandled message: {}".format(message))


if __name__ == "__main__":
	pass
else:
	pass
