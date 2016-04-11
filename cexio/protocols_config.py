"""
The :mod:`cexio.protocols_config` module defines configuration parameters for protocol connectivity
used by :mod:`cexio.ws_client` and :mod:`cexio.rest_client`
"""


protocols_config = {
	'ws': {
		'ping_after': 15,
		'protocol_timeout': 3,
		'timeout': 5,  # real 3-8, more than 18 for testing
		'ensure_alive_timeout': 15 + 3,
		'reconnect': True,
		'resend_subscriptions': True,
		'resend_requests': True,
	},
	'rest': {},
}