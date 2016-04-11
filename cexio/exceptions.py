"""
The :mod:`cexio.exceptions` module defines all user-defined Exceptions used by :mod:`cexio` package:
ConfigError
ProtocolError
AuthError
InvalidMessage
ErrorMessage
InvalidResponseError
ConnectivityError
"""


__all__ = [
	'ConfigError',
	'ProtocolError',
	'AuthError',
	'InvalidMessage',
	'ErrorMessage',
	'InvalidResponseError',
	'ConnectivityError',
]


class ConfigError(Exception):
	"""
	Any configuration error should be covered in this exception
	"""
	pass


class ProtocolError(Exception):
	"""
	An unexpected message should be covered by this exception to signal that protocol changed for example
	"""
	pass


class AuthError(Exception):
	"""
	Exception for User Authentication errors
	"""
	pass


class InvalidMessage(Exception):
	"""
	Is used in cases if 'dict' message , presenting JSON, is not of expected format.
	For example, functions like message validator, oid_setter/getter, data getters
	should raise InvalidMessage if KeyError thrown while trying to get/set some data from/into message
	"""
	pass


class ErrorMessage(Exception):
	"""
	Is used to return error message if it is set in message itself
	CEXIO normally sets the app-level error in the message like following
	{'ok': 'error', 'data': {'error': 'error message', }, }
	"""
	pass


class InvalidResponseError(Exception):
	"""
	Indicates issue with REST resource requested by rest_client
	Is raised on eny not 'OK: 200' response
	"""
	pass


class ConnectivityError(Exception):
	"""
	Is raised on client caller side, if call to websocket client not executed due to connectivity issue
	"""
	pass

