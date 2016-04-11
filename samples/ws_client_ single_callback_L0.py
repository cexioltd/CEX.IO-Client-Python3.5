import asyncio
import asyncio.coroutines
import logging
import random
import sys

from cexio.exceptions import *
from cexio.messaging import *
from cexio.ws_client import *

from config.my_config import config

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))


class SampleWSClient(CommonWebSocketClient):
	# Class responsible to setup specific messaging primitives and event model
	# to the instance of CEXWebSocketClientProtocol, created and connected by asyncio
	# This sample uses async callbacks to cover push notification (on_tick)
	def __init__(self, _config):
		super().__init__(_config)

		def validator(m):
			try:
				ok = m['ok']
				if ok == 'ok':
					return m['data']
				elif ok == 'error':
					raise ErrorMessage(m['data']['error'])
				else:
					error = InvalidMessage(m)
			except KeyError:
				error = InvalidMessage(m)
			raise error

		resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
												 key_set_path='oid', key_get_path='oid')
		self.message_map = (
			({	'e': None,
				'data': None,
				'oid': None,
				'ok': None, }, resolver + validator),

			({	'e': None, }, self.on_notification),
		)
		router = MessageRouter(self.message_map, sink=self.on_unhandled)
		self.set_router(router)
		self.set_resolver(resolver)
		self.__n_future = None
		self.__n_cond = asyncio.Condition()

	async def on_notification(self, data):
		print(data)
		return data

	@staticmethod
	def format_message(op_name, data=None):
		message = {'e': op_name, }
		if data is not None:
			message['data'] = data
		return message

	@staticmethod
	async def on_error(message):
		print("Error: ", message)

	@staticmethod
	async def on_unexpected_response(message):
		logger.debug("Resolver not expected response: {}".format(message))
		return message  # pass back to the router to continue matching

	@staticmethod
	async def on_unhandled(message):
		logger.debug("Unhandled message: {}".format(message))
		print("Unhandled: {}:".format(message))


if __name__ == "__main__":

	client = SampleWSClient(config)

	async def test01():
		try:
			balance = await client.request(SampleWSClient.format_message('get-balance'))
			print(balance)
			ticker = await client.request(SampleWSClient.format_message('ticker', ['BTC', 'USD']))
			print(ticker)

			await client.send_subscribe({'e': 'subscribe', 'rooms': ['tickers', ],})

			await client.send_subscribe({	"e": "init-ohlcv-new",
											"i": "1m",
											"rooms": ["pair-BTC-USD"]})
			await client.request_subscribe(SampleWSClient.format_message(
				'order-book-subscribe',
				{
					'pair': [
						'BTC',
						'USD',
					],
					'subscribe': 'true',
					'depth': 12,
				}))

		except Exception as ex:
				logger.error(ex)

	# to test reconnecting
	async def _get_balance():
		while True:
			try:
				await asyncio.sleep(random.randrange(12, 32))
				balance = await client.request(SampleWSClient.format_message('get-balance'))
				print(balance)
			except Exception as ex:
				print("Exception at closing connection: {}".format(ex))

	# to test reconnecting
	async def _force_disconnect():
		while True:
			try:
				await asyncio.sleep(random.randrange(24, 64))
				print('test > Force disconnect')
				await client.ws.close()
			except Exception as ex:
				print("Exception at exit: {}".format(ex), sys.__stderr__)

	loop = asyncio.get_event_loop()
	loop.set_debug(True)
	loop.run_until_complete(client.run())
	tasks = [
		asyncio.ensure_future(test01()),
		asyncio.ensure_future(_get_balance()),
		asyncio.ensure_future(_force_disconnect()),
	]
	loop.run_until_complete(asyncio.wait(tasks))
	loop.run_forever()
	loop.close()

else:
	pass


