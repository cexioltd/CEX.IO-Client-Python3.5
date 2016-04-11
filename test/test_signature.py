import unittest
from unittest.mock import *
from datetime import datetime

from cexio.ws_client import CEXWebSocketAuth


test_config = {
	'auth': {
		'user': 'TestCex1027',
		'key': '1WZbtMTbMbo2NsW12vOz9IuPM',
		'secret': '1IuUeW4IEWatK87zBTENHj1T17s',
	},
	'uri': {
		'ws': 'wss://ws.cex.io/ws/',
		'rest': 'https://cex.io/api/',
	}
}

test_signatures = (
	{
		'date': 'Nov 20 2015 17:48:53 GMT+0200',
		'timestamp': 1448034533,
		'signature': '7d581adb01ad22f1ed38e1159a7f08ac5d83906ae1a42fe17e7d977786fe9694',
	},
	{
		'date': 'Nov 20 2015 17:58:55 GMT+0200',
		'timestamp': 1448035135,
		'signature': '9a84b70f51ea2b149e71ef2436752a1a7c514f521e886700bcadd88f1767b7db',
	},
)

class WSAuthTestCase(unittest.TestCase):

	def setUp(self):
		super().setUp()

	def tearDown(self):
		super().tearDown()

	def test_signatures(self):
		with patch('test_signature.CEXWebSocketAuth.get_curr_timestamp') as mock:
			auth = CEXWebSocketAuth(test_config)
			mock.side_effect = map(lambda x: x['timestamp'], test_signatures)
			for tsd in test_signatures:
				with self.subTest(timestamp=tsd['timestamp']):
					timestamp = datetime.strptime(tsd['date'], "%b %d %Y %H:%M:%S %Z%z").timestamp()
					auth_request = auth.get_request()
					self.assertEqual(timestamp, tsd['timestamp'])
					self.assertEqual(auth_request['auth']['timestamp'], tsd['timestamp'])
					self.assertEqual(auth_request['auth']['signature'], tsd['signature'])
