"""
The :mod:`cexio.messaging` module provides primitives to build event model in CEX.IO client software:
CallChain (to be substitute with 'chain()' generator function)
MessageRouter
RequestResponseFutureResolver
message_equal_or_less
message_equal_or_greater
message_equal
compare_messages
create_dict_setter
create_dict_getter
"""


import inspect
import logging
import datetime

from .exceptions import *


__all__ = [
	'CallChain',
	'MessageRouter',
	'RequestResponseFutureResolver',
	'message_equal_or_less',
	'message_equal_or_greater',
	'message_equal',
	'compare_messages',
	'create_dict_setter',
	'create_dict_getter',
]


logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


class CallChain(object):
	"""
	Wraps single callable to support message handling async chain call
	callable may be either coroutine or function
	"""
	# TODO: create chain() generator function which is creating chain call instead of chaining at runtime
	#
	def __init__(self, handler=None):
		"""
		method passed processes the message __next_callable
		subscribers are called with its' return value if it is not None
		"""
		assert not isinstance(handler, CallChain), "Nesting of CallChain object is not suggested"
		self._next = None
		self._handler = handler

	def get_next_callable(self):
		return self._next

	def bind(self, next_callable):
		# attaches new CallChainNode(__next_callable) to the end of the chain
		assert callable(next_callable)
		node = self
		while node._next is not None:
			node = node._next
		if isinstance(next_callable, CallChain):
			node._next = next_callable
		else:
			node._next = CallChain(next_callable)
		return self

	def unbind(self):
		self._next = None

	def __str__(self, *args, **kwargs):
		return "{} ({}, next: {})".format(self.__class__.__name__, self._handler, self._next)

	def __add__(self, *args, **kwargs):
		next_callable = args[0]
		return self.bind(next_callable)

	@staticmethod
	def is_user_defined_class(obj):
		cls = obj.__class__
		if hasattr(cls, '__class__'):
			return ('__dict__' in dir(cls) or hasattr(cls, '__slots__'))
		return False

	@staticmethod
	def is_awaitable(obj):
		# There is no single method which can answer in any case, should wait or not - so need to create one
		# for the suspected cases : func, coro, gen-coro, future,
		#                           class with sync __call__, class with async __call__,
		#                           sync method, async method
		if inspect.isawaitable(obj) or inspect.iscoroutinefunction(obj) or inspect.iscoroutine(obj):
			return True
		elif inspect.isgeneratorfunction(obj):
			return True
		elif CallChain.is_user_defined_class(obj):
			if hasattr(obj, '__call__'):
				return CallChain.is_awaitable(obj.__call__)
			return False
		else:
			return False

	async def __call__(self, message):
		# generic call, which eventually may be regenerated to descope if-logic from runtime to construct time
		if self._handler is not None:
			if CallChain.is_awaitable(self._handler):
				message = await self._handler(message)
			else:
				message = self._handler(message)
		if message is not None and self._next is not None:
			logger.debug("    CallChain> chain {} to {}".format(message, self._next))
			message = await self._next.__call__(message)
		return message


async def default_message_router_sink(message):
	logger.warn("    Router> Unhandled message came to default Router.sink: {}".format(message))
	return message


class MessageRouter(list):
	"""
	Matches incoming messages to pattern messages and routes to coroutines:
	- matching goes through the list of pairs [pattern, coro] until matched and coro returns not None;
	- if message matched but rejected by coro returning None, matching moves to the next pattern;
	- if message not matched, it is sent to the sink or default sink coroutine;
	- coroutines in the list can be either - single async callback, CallChain, other Router
	"""
	def __init__(self, t_messages_entries, *,
				 sink=default_message_router_sink,
				 strict_match=False,
				 **kwargs):
		super().__init__(t_messages_entries)
		self.__sink = sink
		if strict_match:
			self.__matcher = message_equal
		else:
			self.__matcher = message_equal_or_greater

	def __str__(self, *args, **kwargs):
		return "{} ({}) Sink: {}".format(self.__class__.__name__, super().__str__(), self.__sink)

	def __contains__(self, *args, **kwargs):
		return args[0] in map(lambda t: t[0], self)

	def bind(self, other):
		assert callable(other)
		self.__sink = other
		return self

	def __add__(self, *args, **kwargs):
		self.bind(args[0])
		return self

	async def __call__(self, message):
		for t_message, handler in self:
			if self.__matcher(message, t_message):
				logger.debug("    Router> route {} to {}".format(message, handler))
				result = await handler(message)
				if result is not None:  # processed by handler, ignored(passed back) otherwise
					return result
		logger.debug("    Router> pass {} to {}".format(message, self.__sink))
		return await self.__sink(message)  # send any unprocessed to sink


def message_equal_or_less(message, t_message):
	# True if 'message' equal or less __next_callable 't_message'
	# 'None' value in t_message forces to ignore the value in message
	return __message_equal_or_less(message, t_message, 0, False)


def message_equal_or_greater(message, t_message):
	# True if 'message' equal or greater __next_callable 't_message'
	# 'None' value in t_message forces to ignore the value in message
	return __message_equal_or_less(t_message, message, 0, True)


def message_equal(message, t_message):
	# True if 'message' equal to 't_message'
	# 'None' value in t_message forces to ignore the value in message
	return message_equal_or_less(message, t_message) & message_equal_or_greater(message, t_message)


def compare_messages(message, t_message):
	# True -1, 0, +1
	# 'None' value in t_message forces to ignore the value in message
	el = message_equal_or_less(message, t_message)
	eg = message_equal_or_greater(message, t_message)
	if el and eg:
		return 0
	elif el:
		return -1
	elif eg:
		return 1
	else:
		return None


def __message_equal_or_less(message, t_message, recno, reverse):
	ret = True

	if recno == 12:
		raise Exception("Recursion limit {} exceeded".format(recno))

	if isinstance(message, dict) and isinstance(t_message, dict):
		# Iterate recursively
		for k, vsm in message.items():
			if k in t_message.keys():
				ret &= __message_equal_or_less(vsm, t_message[k], recno + 1, reverse)
			else:
				ret = False
		return ret

	# Match leafs, interpreting
	# 'None' on the Right (for left-to-right match call with reverse=False) as ignoring Left value
	# 'None' on the Left  (for right-to-left match call with reverse=True) as ignoring Right value
	elif t_message is None and not reverse:
		return True
	elif message is None and reverse:
		return True
	elif isinstance(message, str) and isinstance(t_message, str) and message == t_message:  # equal
		return True
	else:
		return False


def create_dict_getter(path):
	if path is not None:
		path = path.split('/')

		def getter(d):
			try:
				for item in path:
					d = d[item]
				return d
			except KeyError as ex:
				raise InvalidMessage("Invalid dict getter, can't get from: {}".format(d), ex)
	else:
		def getter(d):
			return d
	return getter


def create_dict_setter(path):
	assert path is not None and path is not ''
	path = path.split('/')

	def setter(d, value):
		try:
			for item in path[:-1]:
				d = d[item]
			d[path[-1]] = value
			return d

		except KeyError as ex:
			raise InvalidMessage("Invalid dict setter, can't get from: {}".format(d), ex)

	return setter


class RequestResponseFutureResolver(dict, CallChain):
	"""

	"""
	# Extends CallChain, because needs to manage future here, after successor called

	def __init__(self, *,
				 name=None,
				 op_name_get_path=None,
				 key_set_path=None,
				 key_get_path=None,
				 **kwargs):
		super(CallChain, self).__init__()
		super(dict, self).__init__()

		# generate number, unique within ~24 hours
		# which is used as a key for request/rely pair messages
		self._seqId_base = str(int(datetime.datetime.now().timestamp() * 1000))
		self._seqId_curr_id = 0
		self._name = name
		self._key_setter = create_dict_setter(key_set_path)
		self._key_getter = create_dict_getter(key_get_path)
		# TODO should it be feature of resolver? think no
		self._op_name_getter = lambda x: ''
		if op_name_get_path is not None:
			self._op_name_getter = create_dict_getter(op_name_get_path)

	def get_next_seq_id(self):
		self._seqId_curr_id += 1
		return self.get_seq_id()

	def get_seq_id(self):
		return self._seqId_base + '_' + str(self._seqId_curr_id) + '_' + self._name

	def mark(self, request, future):
		try:
			op_name = self._op_name_getter(request)
		except KeyError as ex:
			raise InvalidMessage("Can't get 'op_name' from Request: {}".format(request), ex)

		request_id = self.get_next_seq_id() + op_name
		self[request_id] = request, future
		try:
			self._key_setter(request, request_id)
		except KeyError as ex:
			raise InvalidMessage("Can't set 'key' to Request: {}".format(request), ex)
		return request

	def clear(self):
		for r, f in self.values():
			f.cancel()
		super().clear()

	async def __call__(self, message):
		# may raise Exception from successors if resolved,
		# return result if resolved, None if not, including the case of error while getting id
		try:
			request_id = self._key_getter(message)
		except KeyError as ex:
			logger.warn("Can't get 'key' from Response: {}".format(message), ex)
			# no key for resolving - supposed to be processed further by caller (MessageRouter)
			return None

		if request_id in self.keys():
			# 'resolved' with result or error, raised  by chan calls
			logger.debug("    Resolver> resolve {}".format(message))
			request, future = self.pop(request_id)
			if self.get_next_callable() is not None:
				logger.debug("    Resolver> chain {} to {}".format(message, self.get_next_callable()))
				try:
					# In Case of known exceptions,
					# need to return not None, since response is resolved
					# no raising, be cause exception should be handled ats future side but not on callee side
					message = await self.get_next_callable().__call__(message)
				except ErrorMessage as ex:
					future.set_exception(ex)
					return ex
				except InvalidMessage as ex:
					future.set_exception(ex)
					return ex
			future.set_result(message)
			return message


if __name__ == "__main__":
	pass
else:
	pass









