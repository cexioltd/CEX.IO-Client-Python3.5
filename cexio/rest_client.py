import hmac
import hashlib
import time
import urllib
import json
import datetime
import logging
import sys

from asyncio import *
import aiohttp

from cexio.exceptions import *


logger = logging.getLogger(__name__)


__all__ = [
	'CEXRestClient',
]


# Assert that required algorithm implemented
assert 'sha256' in hashlib.algorithms_guaranteed


class CEXRestAuth:
	"""
	"""
	#

	# JSON template dict
	_json = {
		'key': None,
		'signature': None,
		'nonce': None,
	}

	def __init__(self, config):
		try:
			self._user_id = config['auth']['user_id']
			self._key = config['auth']['key']
			self._secret = config['auth']['secret']

		except KeyError as ex:
			raise ConfigError('Missing key in _config file', ex)

	def get_curr_timestamp(self):
		return int(datetime.datetime.now().timestamp() * 1000)

	def get_timed_signature(self):
		"""
		Returns java timestamp in miliseconds, and 'timed' signature,
		which is the digest of byte string, compound of timestamp, user ID ans public key
		"""
		timestamp = self.get_curr_timestamp()
		message = "{}{}{}".format(timestamp, self._user_id, self._key)
		return timestamp, hmac.new(self._secret.encode(), message.encode(), hashlib.sha256).hexdigest()

	def get_params(self):
		"""
		Returns JSON from self._json dict
		The request is valid within ~20 seconds
		"""
		timestamp, signature = self.get_timed_signature()
		self._json['key'] = self._key
		self._json['signature'] = signature
		self._json['nonce'] = timestamp
		return self._json


class CEXRestClient:

	def __init__(self, config):
		global headers
		headers = {'content-type': 'application/json'}

		try:
			self._uri = config['rest']['uri']
			self._need_auth = config['authorize']
			if self._need_auth:
				self._auth = CEXRestAuth(config)

		except KeyError as ex:
			raise ConfigError('Missing key in _config file', ex)

	async def get(self, resource):
		url = self._uri + resource
		logger.debug("REST.Get> {}".format(url))

		with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				self._validate(url, response)
				response = await response.json()
				logger.debug("REST.Resp> Response: {}".format(response))
				return response

	async def post(self, resource, params={}):
		url = self._uri + resource
		logger.debug("REST.Post> {}".format(url))

		with aiohttp.ClientSession() as session:
			if self._need_auth:
				params.update(self._auth.get_params())

			async with session.post(url, data=params) as response:
				self._validate(url, response)
				response = await response.json()
				logger.debug("REST.Resp> {}".format(response))
				return response

	@staticmethod
	def _validate(url, response):
		if response.status != 200:
			error = "Error response code {}: {} at: {}".format(response.status, response.reason, url)
			logger.debug(error)
			raise InvalidResponseError(error)

		content_type = response.headers['CONTENT-TYPE']
		if content_type != 'text/json':
			error = "Invalid response content-type \'{}\' of: {}".format(content_type, url)
			logger.debug(error)
			raise InvalidResponseError(error)


if __name__ == "__main__":
	pass
else:
	pass
