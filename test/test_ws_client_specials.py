import asyncio
import unittest

import websockets

from cexio.ws_client import *
from cexio.protocols_config import protocols_config
from config.prod_env_config import config


class WSClientSpecialsNoAuthTestCase(unittest.TestCase):

	def setUp(self):
		self.loop = asyncio.get_event_loop()
		self._config = config.copy()
		self._config['authorize'] = False
		protocols_config['ws']['reconnect'] = False
		super().setUp()

	def tearDown(self):
		super().tearDown()

	async def _test_primitives(self):

		with self.subTest(case='connect'):
			client = CommonWebSocketClient(self._config)
			await client.connect()
			await asyncio.sleep(1)

		with self.subTest(case='send & recv - private - Please Login'):
			await client.send({'e': 'ticker', 'data': ['BTC', 'USD', ], 'oid': 'id_1', })
			response = await client.recv()
			self.assertIsNotNone(response)
			self.assertEqual(response['ok'], 'error', "'Ticker' should be available for authorized user only")
			self.assertEqual(response['data']['error'], 'Please Login')
			self.assertEqual(response['oid'], 'id_1')
			await asyncio.sleep(1)

		with self.subTest(case='send & recv - public subscribe'):
			await client.send({'e': 'subscribe', 'rooms': ['fokBundles', ], 'oid': 'no_id', })
			response = await client.recv()
			self.assertIsNotNone(response)
			self.assertEqual(response['e'], 'fokBundles')
			self.assertFalse('ok' in response.keys())
			self.assertFalse('oid' in response.keys())
			await asyncio.sleep(1)

		with self.subTest(case='close'):
			await client.stop()

	def test_ws_protocol_no_auth(self):
		self.loop.run_until_complete(self._test_primitives())


class WSClientSpecialsAuthTestCase(unittest.TestCase):

	def setUp(self):
		self.loop = asyncio.get_event_loop()
		self._config = config.copy()
		self._config['authorize'] = True
		super().setUp()

	def tearDown(self):
		super().tearDown()

	async def _test_primitives(self):

		ping_after = protocols_config['ws']['ping_after']

		with self.subTest(case='connect'):
			client = CommonWebSocketClient(self._config)
			await client.connect()
			await asyncio.sleep(1)

		with self.subTest(case='send & no reply'):
			await client.send({'e': 'subscribe', 'rooms': ['none', ], })
			# ensure no response
			with self.assertRaises(asyncio.TimeoutError):
				await asyncio.wait_for(client.recv(), 5)

		with self.subTest(case='send & recv - balance'):
			await client.send({'e': 'get-balance', 'oid': 'id_1', })
			response = await client.recv()
			self.assertIsNotNone(response)
			self.assertEqual(response['ok'], 'ok', response)
			self.assertEqual(response['oid'], 'id_1', response)

		with self.subTest(case='pong on server ping'):
			try:
				ping = await asyncio.wait_for(client._recv(), ping_after + 1)
				self.assertEqual(ping['e'], 'ping')
				self.assertIsNotNone(ping['time'])
				asyncio.sleep(ping_after - 3)
				await client.send({'e': 'pong'})
			except asyncio.TimeoutError:
				self.fail("No ping from server within {} secs".format(ping_after))

		with self.subTest(case='get-balance on server ping'):
			try:
				ping = await asyncio.wait_for(client._recv(), ping_after + 5)
				self.assertEqual(ping['e'], 'ping')
				self.assertIsNotNone(ping['time'])
				asyncio.sleep(ping_after - 3)
				await client.send({'e': 'get-balance', 'oid': 'id_2', })
				await client.recv()
			except asyncio.TimeoutError:
				self.fail("No ping from server within {} secs".format(ping_after))

		with self.subTest(case='disconnected - no pong'):
			ping = await asyncio.wait_for(client._recv(), ping_after + 5)
			self.assertEqual(ping['e'], 'ping')
			self.assertIsNotNone(ping['time'])
			try:
				disconnecting = await asyncio.wait_for(client._recv(), ping_after + 5)
				self.assertEqual(disconnecting['e'], 'disconnecting')
			except asyncio.TimeoutError:
				self.fail("No {'e': 'disconnecting'} received")
			except websockets.exceptions.ConnectionClosed as ex:
				self.fail("No {'e': 'disconnecting'} received, but: {}".format(ex))

		with self.subTest(case='close after disconnected'):
			await client.stop()

	def test_ws_protocol_auth(self):
		self.loop.run_until_complete(self._test_primitives())


