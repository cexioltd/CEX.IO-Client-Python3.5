import unittest
from unittest.mock import *
import asyncio

from cexio.exceptions import *
from cexio.messaging import *


class TestDictSetGet(unittest.TestCase):

	def test_dict_getset(self):
		getter = create_dict_getter('a/b/c')
		setter = create_dict_setter('a/b/c')

		d = {'a': {'b': {'c': None}}}
		self.assertIsNone(getter(d))
		setter(d, 'value')
		self.assertEqual(getter(d), 'value')


class IsSubMessageTest(unittest.TestCase):

	# True if 'message' equal or less __next_callable 't_message'
	# 'None' value in t_message forces to ignore the value in message
	match_messages = (
	{
		'when': message_equal_or_less, 'given_t_messages': (

		{'t_message': None, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'any': None, },																'then': True},
		)},
		{'t_message': {}, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'e': None, },																	'then': False},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': False},
		)},
		{'t_message': {'e': None, }, 'given_messages': (
			{'message': {'e': None, },																	'then': True},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': True},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': True},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': False},
		)},
		{'t_message': {'e': 'connected', }, 'given_messages': (
			{'message': {'e': None, },																	'then': False},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': False},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': False},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': False},
		)},
		{'t_message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'}, 'given_messages': (
			{'message': {'e': 'connected', },															'then': True},
		)},
		{'t_message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', },							'then': True},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'don\'t know ', },					'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': None, },							'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', 'extra': 'extra data'}, 'ok': 'ok', },		'then': False},
			{'message': {'e': 'auth', 'data': {}, 'ok': 'ok', },										'then': True},
			{'message': {'e': 'auth', 'data': {}, 'not ok': 'ok', },									'then': False},
		)},
		{'t_message': {'e': 'auth', 'data': {'error': None, }, 'ok': 'error', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'error', },					'then': True},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'don\'t know ', },			'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': None, },						'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', 'err': 'err', }, 'ok': 'error', },		'then': False},
			{'message': {'e': 'auth', 'data': {}, 'ok': 'error', },										'then': True},
		)},
	)},
	{
		'when': message_equal_or_greater, 'given_t_messages': (

		{'t_message': None, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'any': None, },																'then': True},
		)},
		{'t_message': {}, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'e': None, },																	'then': True},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': True},
		)},
		{'t_message': {'e': None, }, 'given_messages': (
			{'message': {'e': None, },																	'then': True},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': True},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': True},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': True},
		)},
		{'t_message': {'e': 'connected', }, 'given_messages': (
			{'message': {'e': None, },																	'then': False},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': False},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': False},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': True},
		)},
		{'t_message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'}, 'given_messages': (
			{'message': {'e': 'connected', },															'then': False},
		)},
		{'t_message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', },							'then': True},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'don\'t know ', },					'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': None, },							'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', 'extra': 'extra data'}, 'ok': 'ok', },		'then': True},
			{'message': {'e': 'auth', 'data': {}, 'ok': 'ok', },										'then': False},
			{'message': {'e': 'auth', 'data': {}, 'not ok': 'ok', },									'then': False},
		)},
		{'t_message': {'e': 'auth', 'data': {'error': None, }, 'ok': 'error', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'error', },					'then': True},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'don\'t know ', },			'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': None, },						'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', 'err': 'err', }, 'ok': 'error', },		'then': True},
			{'message': {'e': 'auth', 'data': {'err': 'err', }, 'ok': 'error', },						'then': False},
		)},
	)},
	{
		'when': message_equal, 'given_t_messages': (

		{'t_message': None, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'any': None, },																'then': True},
		)},
		{'t_message': {}, 'given_messages': (
			{'message': {},																				'then': True},
			{'message': {'e': None, },																	'then': False},
		)},
		{'t_message': {'e': None, }, 'given_messages': (
			{'message': {'e': None, },																	'then': True},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': True},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': True},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': False},
		)},
		{'t_message': {'e': 'connected', }, 'given_messages': (
			{'message': {'e': None, },																	'then': False},
			{'message': {'unknown': 'connected', },														'then': False},
			{'message': {'e': 'unknown', },																'then': False},
			{'message': {'e': 'connected', },															'then': True},
			{'message': {'e': {'connected': 'nested'}, },												'then': False},
			{'message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'},							'then': False},
		)},
		{'t_message': {'a': 'a', 'e': 'connected', 'extra': 'some extra'}, 'given_messages': (
			{'message': {'e': 'connected', },															'then': False},
		)},
		{'t_message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', },							'then': True},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'don\'t know ', },					'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': None, },							'then': False},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', 'extra': 'extra data'}, 'ok': 'ok', },		'then': False},
			{'message': {'e': 'auth', 'data': {}, 'ok': 'ok', },										'then': False},
			{'message': {'e': 'auth', 'data': {}, 'not ok': 'ok', },									'then': False},
		)},
		{'t_message': {'e': 'auth', 'data': {'error': None, }, 'ok': 'error', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {'error': None, }, 'ok': 'error', },						'then': True},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'error', },					'then': True},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': 'don\'t know ', },			'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', }, 'ok': None, },						'then': False},
			{'message': {'e': 'auth', 'data': {'error': 'error', 'err': 'err', }, 'ok': 'error', },		'then': False},
			{'message': {'e': 'auth', 'data': {'err': 'err', }, 'ok': 'error', },						'then': False},
		)},
	)},
	{
		'when': compare_messages, 'given_t_messages': (

		{'t_message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', }, 'given_messages': (
			{'message': {'e': 'auth', 'data': {}, 'ok': 'ok', },										'then': -1},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'ok', },							'then': 0},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', 'extra': 'extra'}, 'ok': 'ok', },			'then': 1},
			{'message': {'e': 'auth', 'data': {'ok': 'ok', }, 'ok': 'unexpected', },					'then': None},
		)},
	)},
	)

	def test_match_messages(self):
		for func_test_suite in self.match_messages:
			func = func_test_suite['when']
			for t_message_suite in func_test_suite['given_t_messages']:
				t_message = t_message_suite['t_message']
				for message_case in t_message_suite['given_messages']:
					message = message_case['message']
					is_subm = func(message, t_message)
					with self.subTest(func=func, message=message, t_message=t_message):
						self.assertEqual(is_subm, message_case['then'],
										 "{}({}, {})".format(func, message, t_message))

	def test_stop_recursion(self):
		graph = {'entry': {'entry': None}}
		graph['entry']['entry'] = graph
		with self.assertRaises(Exception):
			message_equal_or_less(graph, graph)


class CallChainTestCase(unittest.TestCase):

	def setUp(self):
		super().setUp()

	def tearDown(self):
		super().tearDown()

	def test_isawaitable(self):

		class SyncCall:
			def method(self):
				pass

			async def async_method(self):
				pass

			def __call__(self, *args):
				pass

		def func():
			pass

		class AsyncCall:
			async def __call__(self, *args):
				pass

		async def coro():
			pass

		@asyncio.coroutine
		def gen_coro():
			pass

		@staticmethod
		def static_method():
			pass

		self.assertFalse(CallChain.is_awaitable(1))
		self.assertFalse(CallChain.is_awaitable(func))
		self.assertTrue(CallChain.is_awaitable(coro))
		self.assertTrue(CallChain.is_awaitable(asyncio.Future()))
		self.assertFalse(CallChain.is_awaitable(static_method))
		self.assertFalse(CallChain.is_awaitable(SyncCall().method))
		self.assertTrue(CallChain.is_awaitable(SyncCall().async_method))
		self.assertFalse(CallChain.is_awaitable(SyncCall()))
		self.assertTrue(CallChain.is_awaitable(AsyncCall()))
		self.assertTrue(CallChain.is_awaitable(gen_coro))


class MessageIdResolverTestCase(unittest.TestCase):

	def setUp(self):
		super().setUp()

	def tearDown(self):
		super().tearDown()

	async def _test_message_id_resolver1(self):

		resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
													key_get_path='id', key_set_path='id')
		f1 = asyncio.Future()
		f2 = asyncio.Future()
		message = resolver.mark(			{'root': {'message': {'m': 'message_to_send 1', }, }, 'e': 'op_name', }, f1)
		id1 = message['id']
		message = resolver.mark(			{'root': {'message': {'m': 'message_to_send 2', }, }, 'e': 'op_name', }, f2)
		id2 = message['id']

		with self.subTest(key_set_path='id', key_get_path='id', next=None):
			# resolved
			result = await resolver(			{'message': {'m': 'message_received 1', }, 'id': id1})
			self.assertEqual(f1.result(),		{'message': {'m': 'message_received 1', }, 'id': id1})
			self.assertEqual(result,			{'message': {'m': 'message_received 1', }, 'id': id1})

			# can not be resolved twice
			result = await resolver(			{'message': {'m': 'message_received 1', }, 'id': id1})
			self.assertIsNone(result)

			# resolved
			result = await resolver(			{'message': {'m': 'message_received 2', }, 'id': id2})
			self.assertEqual(f2.result(),		{'message': {'m': 'message_received 2', }, 'id': id2})
			self.assertEqual(result,			{'message': {'m': 'message_received 2', }, 'id': id2})

	async def _test_message_id_resolver2(self):

		resolver = RequestResponseFutureResolver(name='', op_name_get_path='e',
													key_get_path='message/id', key_set_path='root/message/id')
		f1 = asyncio.Future()
		f2 = asyncio.Future()
		message = resolver.mark(			{'root': {'message': {'m': 'message_to_send 1', }, }, 'e': 'op_name', }, f1)
		id1 = message['root']['message']['id']
		message = resolver.mark(			{'root': {'message': {'m': 'message_to_send 2', }, }, 'e': 'op_name', }, f2)
		id2 = message['root']['message']['id']

		with self.subTest(key_set_path='root/message/id', key_get_path='message/id', next=None):
			# resolved
			result = await resolver(			{'message': {'m': 'message_received 1', 'id': id1, }, })
			self.assertEqual(f1.result(),		{'message': {'m': 'message_received 1', 'id': id1, }, })
			self.assertEqual(result,			{'message': {'m': 'message_received 1', 'id': id1, }, })

			# can not be resolved twice
			result = await resolver(			{'message': {'m': 'message_received 1', 'id': id1, }, })
			self.assertIsNone(result)

			# resolved
			result = await resolver(			{'message': {'m': 'message_received 2', 'id': id2, }, })
			self.assertEqual(f2.result(),		{'message': {'m': 'message_received 2', 'id': id2, }, })
			self.assertEqual(result,			{'message': {'m': 'message_received 2', 'id': id2, }, })

	async def _test_resolver_with_next_calls(self):

		def validator(m):
			try:
				ok = m['ok']
				if ok == 'ok':
					return m
				elif ok == 'error':
					raise ErrorMessage(m['data']['error'])
				else:
					error = InvalidMessage(m)
			except KeyError:
				error = InvalidMessage(m)
			raise error

		async def data_getter(m):
			# async just for testing fun
			try:
				return m['data']
			except KeyError:
				raise InvalidMessage(m)

		resolver = RequestResponseFutureResolver(name='name',
												 key_get_path='id', key_set_path='id') + validator + data_getter
		f1 = asyncio.Future()
		f2 = asyncio.Future()
		f3 = asyncio.Future()
		f4 = asyncio.Future()
		f5 = asyncio.Future()
		message = resolver.mark(				{'message': '1', }, f1)
		id1 = message['id']
		message = resolver.mark(				{'message': '2', }, f2)
		id2 = message['id']
		message = resolver.mark(				{'message': '3', }, f3)
		id3 = message['id']
		message = resolver.mark(				{'message': '4', }, f4)
		id4 = message['id']
		message = resolver.mark(				{'message': '4', }, f5)
		id5 = message['id']

		with self.subTest(validator='{ok: ok} sample validator', case='not resolved'):
			# not resolved & passed back
			result = await resolver(			{'id': 'undefined', 'ok': 'ok', })
			self.assertIsNone(result)

		with self.subTest(validator='{ok: ok} sample validator', case='resolved'):
			# resolved successfully
			result = await resolver(			{'id': id1, 'ok': 'ok', 'data': {'d': 'the data', }, })
			self.assertEqual(f1.result(),										{'d': 'the data', })
			self.assertEqual(result, 											{'d': 'the data', })

		with self.subTest(validator='{ok: ok} sample validator', case='Invalid \'ok\' value'):
			# resolved with InvalidMessage(invalid)
			result = await resolver(			{'id': id2, 'ok': 'undefined', })
			self.assertIsInstance(f2.exception(), InvalidMessage)
			self.assertIsNotNone(result)

		with self.subTest(validator='{ok: ok} sample validator', case='no m[data][error] found'):
			# resolved with InvalidMessage(invalid -  no {'data': {'error': ..., }, })
			result = await resolver(			{'id': id3, 'ok': 'error', 'data': {}, })
			self.assertIsInstance(f3.exception(), InvalidMessage)
			self.assertIsNotNone(result)

		with self.subTest(validator='{ok: ok} sample validator', case='data_getter thrown exception'):
			# resolved with InvalidMessage(invalid -  no {'data': {'error': ..., }, })
			result = await resolver(			{'id': id4, 'ok': 'error', 'no_data': {}, })
			self.assertIsInstance(f4.exception(), InvalidMessage)
			self.assertIsNotNone(result)

		with self.subTest(validator='{ok: ok} sample validator', case='error found in message body'):
			# resolved ErrorMessage - error is set to message in right way
			result = await resolver(			{'id': id5, 'ok': 'error', 'data': {'error': 'error message', }, })
			self.assertIsInstance(f5.exception(), ErrorMessage)
			self.assertIsNotNone(result)

	async def run_all(self):
		await self._test_message_id_resolver1()
		await self._test_message_id_resolver2()
		await self._test_resolver_with_next_calls()

	def test_async(self):
		loop = asyncio.new_event_loop()
		loop.run_until_complete(self.run_all())
		loop.close()


class MessageRouterAndChainCallTest(unittest.TestCase):

	def setUp(self):
		super().setUp()

	def tearDown(self):
		super().tearDown()

	# Test sync callbacks for mocking
	def __on_connected(message):
		print('>    ', "Connection established: {}".format(message))
		return message

	def __on_connected2(message):
		print('>    ', "Connection established 2: {}".format(message))
		return None

	def __on_authorized(message):
		print('>         ', "User authorized: {}".format(message))

	def __on_auth_error(message):
		print('>    ', "Authorization error: {}".format(message))

	def __on_ping(message):
		print('>    ', "On Ping: {}".format(message))
		return message

	def __sink(message):
		print('>    ', "Passed: {}".format(message))

	def __on_ping2(message):
		print('>         ', "chain 1 on_ping via chain router called")

	def __on_ping3(message):
		print('>         ', "chain 1 on_ping via chain router called")

	# Test async callbacks
	async def on_connected(message):
		return MessageRouterAndChainCallTest.__on_connected(message)

	async def on_connected2(message):
		return MessageRouterAndChainCallTest.__on_connected2(message)

	async def on_authorized(message):
		return MessageRouterAndChainCallTest.__on_authorized(message)

	async def on_auth_error(message):
		return MessageRouterAndChainCallTest.__on_auth_error(message)

	async def on_ping(message):
		return MessageRouterAndChainCallTest.__on_ping(message)

	async def sink(message):
		return MessageRouterAndChainCallTest.__sink(message)

	async def on_ping2(message):
		return MessageRouterAndChainCallTest.__on_ping2(message)

	async def on_ping3(message):
		return MessageRouterAndChainCallTest.__on_ping3(message)

	# CallChain
	chain = CallChain(on_connected) + on_connected2

	# Secondary router setup as call
	chain_router = MessageRouter((
		({'e': 'ping', 'time': None, },
		 CallChain() + on_ping2 + on_ping3),
	), sink=sink)

	# Root Router
	rmap = (
		({'skip': None}, CallChain()),
		({'e': 'connected', }, chain),
		({'e': 'auth', 'data': {'ok': 'ok'}, 'ok': 'ok'}, on_authorized),
		({'e': 'auth', 'ok': 'error'}, on_auth_error),
		({'e': 'ping', 'time': None},
		 CallChain(on_ping) + chain_router),
	)
	root_router = MessageRouter(rmap, sink=sink)
	root_router_strict = MessageRouter(rmap, sink=sink, strict_match=True)

	async def run_all(self):
		await self.root_router({'skip': 'skip'})
		await self.root_router({'e': 'connected', 'extra': 'extra'})  # should match to if strict_match = False
		await self.root_router({'e': 'auth', 'ok': 'error'})
		await self.root_router({'unk': 'connected'})
		await self.root_router({'': 'unk'})
		await self.root_router({'e': 'ping', 'time': '001'})

	async def run_strict_match(self):
		# Test strict matching
		await self.root_router_strict({'e': 'connected', 'extra': 'extra'})  # should not match due to extra data
		await self.root_router_strict({'e': 'connected', })  # should match


	def test_async_scenario(self):
		loop = asyncio.new_event_loop()

		# just print
		# loop.run_until_complete(self.run_all())

		MessageRouterAndChainCallTest.__on_connected 	= MagicMock(return_value={'e': 'connected', 'extra': 'extra'})
		MessageRouterAndChainCallTest.__on_connected2 	= MagicMock(return_value=None)
		MessageRouterAndChainCallTest.__on_authorized 	= MagicMock(return_value=None)
		MessageRouterAndChainCallTest.__on_auth_error 	= MagicMock()
		MessageRouterAndChainCallTest.__on_ping 		= MagicMock(return_value=None)
		MessageRouterAndChainCallTest.__sink 			= MagicMock()
		MessageRouterAndChainCallTest.__on_ping2 		= MagicMock()
		MessageRouterAndChainCallTest.__on_ping3 		= MagicMock()

		loop.run_until_complete(self.run_all())
		MessageRouterAndChainCallTest.__on_connected	.assert_called_once_with({'e': 'connected', 'extra': 'extra'})
		MessageRouterAndChainCallTest.__on_connected2	.assert_called_once_with({'e': 'connected', 'extra': 'extra'})
		MessageRouterAndChainCallTest.__on_authorized 	.assert_not_called()
		MessageRouterAndChainCallTest.__on_auth_error 	.assert_called_once_with({'e': 'auth', 'ok': 'error'})
		MessageRouterAndChainCallTest.__on_ping			.assert_called_once_with({'time': '001', 'e': 'ping'})
		MessageRouterAndChainCallTest.__sink 			.assert_has_calls([call({'unk':'connected'}), call({'':'unk'})])
		MessageRouterAndChainCallTest.__on_ping2 		.assert_not_called()
		MessageRouterAndChainCallTest.__on_ping3 		.assert_not_called()

		MessageRouterAndChainCallTest.__on_connected 	= MagicMock(return_value={'e': 'new message'})
		MessageRouterAndChainCallTest.__on_connected2 	= MagicMock(return_value=None)
		MessageRouterAndChainCallTest.__on_authorized 	= MagicMock(return_value=None)
		MessageRouterAndChainCallTest.__on_auth_error 	= MagicMock()
		MessageRouterAndChainCallTest.__on_ping 		= MagicMock(return_value={'time': '001', 'e': 'ping'})
		MessageRouterAndChainCallTest.__sink 			= MagicMock()
		MessageRouterAndChainCallTest.__on_ping2 		= MagicMock(return_value={'time': '001', 'e': 'ping'})
		MessageRouterAndChainCallTest.__on_ping3 		= MagicMock()

		loop.run_until_complete(self.run_all())
		MessageRouterAndChainCallTest.__on_connected	.assert_called_once_with({'e': 'connected', 'extra': 'extra'})
		MessageRouterAndChainCallTest.__on_connected2	.assert_called_once_with({'e': 'new message'})
		MessageRouterAndChainCallTest.__on_authorized 	.assert_not_called()
		MessageRouterAndChainCallTest.__on_auth_error 	.assert_called_once_with({'e': 'auth', 'ok': 'error'})
		MessageRouterAndChainCallTest.__on_ping			.assert_called_once_with({'time': '001', 'e': 'ping'})
		MessageRouterAndChainCallTest.__sink 			.assert_has_calls([call({'unk':'connected'}), call({'':'unk'})])
		MessageRouterAndChainCallTest.__on_ping2 		.assert_called_once_with({'time': '001', 'e': 'ping'})
		MessageRouterAndChainCallTest.__on_ping3 		.assert_called_once_with({'time': '001', 'e': 'ping'})

		# Testing if strict matching works
		MessageRouterAndChainCallTest.__on_connected 	= MagicMock()

		loop.run_until_complete(self.run_strict_match())
		MessageRouterAndChainCallTest.__on_connected	.assert_called_once_with({'e': 'connected'})

		loop.close()
