import asyncio
import unittest

from cexio.exceptions import *
from cexio.messaging import *
from cexio.ws_client import *
from config.prod_env_config import config


class ClientRequestReplyResolvingTestCase(unittest.TestCase):

	def _init_client(self):
		_config = config.copy()
		_config['authorize'] = True
		self.client = CommonWebSocketClient(_config)
		self.client._reconnect = False
		self.unhandled_message_list = []

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

		self.resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
													  key_set_path='oid', key_get_path='oid')
		self.secondary_message_map = (
			({	'e': 'ticker',
				'data': None,
				'ok': 'ok', },		self.on_async_ticker_received),
		)
		self.message_map = (

			# Resolver of request/response with 'oid'
			({	'e': None,
				'data': None,
				'oid': None,
				'ok': None, }, 		self.resolver + validator),

			# Entry for the messages with oid, but not resolved by resolver
			({	'e': None,
				'data': None,
				'oid': None,
				'ok': None, }, 		CallChain(self.on_unexpected_response) + MessageRouter(self.secondary_message_map)),
		)
		router = MessageRouter(self.message_map) + self.on_unhandled_message

		self.client.set_router(router)
		self.client.set_resolver(self.resolver)

	async def on_unexpected_response(self, message):
		# Returns message - processed
		self.unexpected_responses += 1
		return message

	async def on_unhandled_message(self, message):
		# Returns None - passed
		self.unhandled_messages += 1
		self.unhandled_message_list.append(message)

	async def on_async_ticker_received(self, message):
		# Returns None -passed
		self.async_messages_received += 1

	async def _run(self):
		await self.client.run()

	async def _stop(self):
		await self.client.stop()

	async def _request_once(self):
		self.unexpected_responses = 0
		self.unhandled_messages = 0
		self.async_messages_received = 0

		with self.subTest(case='3 resolved'):
			balance = await self.client.request({'e': 'get-balance', })
			print(balance)
			self.assertTrue('balance' in balance.keys())
			ticker = await self.client.request({'e': 'ticker', 'data': ['BTC', 'EUR'], })
			self.assertTrue('pair' in ticker.keys())
			balance = await self.client.request({'e': 'get-balance', })
			self.assertTrue('balance' in balance.keys())
			self.assertEqual(self.unexpected_responses, 0)
			self.assertEqual(len(self.resolver), 0)

	async def _catch_response_error_message(self):
		with self.subTest(case='catch error in the response body'):
			with self.assertRaises(ErrorMessage):
				await self.client.request({'e': 'ticker', 'data': ['BTC'], })
			self.assertEqual(len(self.resolver), 0)

	async def _request_once_unexpected(self):
		self.unexpected_responses = 0
		self.unhandled_messages = 0
		self.async_messages_received = 0

		with self.subTest(case='1 unexpected by resolver'):
			# response not awaited by resolver
			await self.client.send({'e': 'get-balance', 'oid': 'undefined', })
			await asyncio.sleep(1)
			self.assertEqual(self.unexpected_responses, 1)
			self.assertEqual(len(self.resolver), 0)

	async def _request_once_unresolved(self):
		self.unexpected_responses = 0
		self.unhandled_messages = 0
		self.async_messages_received = 0

		with self.subTest(case='1 unresolved on resolver (request, no response)'):
			with self.assertRaises(asyncio.TimeoutError):
				await asyncio.wait_for(self.client.request({'e': 'subscribe', 'rooms': ['none', ], }), 3)
			self.assertEqual(self.unexpected_responses, 0)
			self.assertEqual(len(self.resolver), 1)
			self.resolver.clear()

	async def _resolve_loads(self, packets):
		self.unexpected_responses = 0
		self.unhandled_messages = 0
		self.async_messages_received = 0
		self.resolver.clear()

		with self.subTest(case='0 unresolved, N unhandled, N unexpected, N asynchronously received'):
			tasklist = []
			for i in range(0, packets):  # schedule all
				# all N responses should be resolved
				tasklist.append(asyncio.ensure_future(self.client.request({'e': 'ticker', 'data': ['BTC', 'USD'], })))
				# result in N unexpected responses & N unhandled (via router.sink)
				tasklist.append(asyncio.ensure_future(self.client.send({'e': 'ticker', 'data': ['BTC', 'USD'], 'oid': i, }, )))
				# result in N unhandled message passed to async callback via secondary router
				tasklist.append(asyncio.ensure_future(self.client.send({'e': 'ticker', 'data': ['BTC', 'USD'], })))
				# just N sending while reading
				tasklist.append(asyncio.ensure_future(self.client.send({'e': 'subscribe', 'rooms': ['none', ], })))
			asyncio.wait_for(tasklist, 5 + packets * 0.2)
			await asyncio.sleep(5 + packets * 0.2)  # wait to receive async messages

			# temp - need to find one extra unhandled message, happaned not often
			# may be due to some race condition in client code or server side
			print('----------------------------')
			for m in self.unhandled_message_list:
				print(m)

			self.assertEqual(self.unexpected_responses, packets)
			self.assertEqual(self.unhandled_messages, packets)
			self.assertEqual(self.async_messages_received, packets)
			self.assertEqual(len(self.resolver), 0)

	def test_resolving(self):
		loop = asyncio.get_event_loop()
		self._init_client()
		loop.run_until_complete(self._run())
		loop.run_until_complete(self._request_once())
		loop.run_until_complete(self._request_once_unresolved())
		loop.run_until_complete(self._catch_response_error_message())
		loop.run_until_complete(self._resolve_loads(124))  # 124 to not exceed req rate limit
		loop.run_until_complete(self._stop())

