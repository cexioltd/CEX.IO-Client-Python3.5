#!/usr/bin/env python

from asyncio import *
import logging
import random
import sys

from cexio.ws_client import *
from cexio.messaging import *
from config.my_config import config


logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))


if __name__ == "__main__":

	class WebSocketClientPublicData(WebSocketClientSingleCallback):
		def __init__(self, _config):
			super().__init__(_config)

			def get_first(t):
				if len(t) == 0:
					return None
				else:
					return t[0]

			async def on_tick(message):
				print("Tick > pair: {}:{}, price: {}".format(message['data']['symbol1'],
															 message['data']['symbol2'],
															 message['data']['price']))
				return message

			async def on_ohlcv_init_new(message):
				entries = message['data']
				print("OHLCV_init_new > pair: {}, {} entries like: {}".format(message['pair'],
																			  len(entries), get_first(entries)))
				return message

			async def on_ohlcv_new(message):
				entries = message['data']
				print("OHLCV_new > pair: {}, {} entries like: {}".format(message['pair'],
																		 len(entries), get_first(entries)))
				return message

			async def on_ohlcv1m(message):
				print("OHLCV_1m > {}".format(message['data']))
				return message

			async def on_md(message):
				data = message['data']
				print("MD > pair: {},"
					  " 'buy_total': {}, 'sell_total': {},"
					  " 'buy': [{} pairs like: {}],"
					  " 'sell': [{} pairs like: {}]".
					  format(data['pair'],
							 data['buy_total'], data['sell_total'],
							 len(data['buy']), get_first(data['buy']),
							 len(data['sell']), get_first(data['sell'])))
				return message

			async def on_md_grouped(message):
				data = message['data']
				print("MD_groped > pair: {},"
					  " 'buy': [{} items like: {}],"
					  " 'sell': [{} items like: {}]".
					  format(data['pair'],
							 len(data['buy'].items()), get_first(list(data['buy'].items())),
							 len(data['sell'].items()), get_first(list(data['sell'].items()))))
				return message

			async def on_history(message):
				data = message['data']
				print("History > [{} items like: '{}']".format(len(data), get_first(data)))
				return message

			async def on_history_update(message):
				data = message['data']
				if len(data) == 0:
					pass  # skip empty history updates
				else:
					print("History Update> [{} items like: [{}]]".format(len(data), get_first(data)))
				return message

			async def on_ohlcv(message):
				print("OHLCV > {}".format(message))
				return message

			async def on_ohlcv24(message):
				print("OHLCV_24 > {}".format(message))
				return message

			async def sink(message):
				event = message['e']
				print("   Uncovered > {}".format(event))
				return event

			self.n_router = MessageRouter((

				# Send: {'e': 'subscribe', 'rooms': ['tickers', ], }
				# Server is notifying on transaction executed on any pair with price
				({'e': 'tick', }, on_tick),

				# Send: { "e": "init-ohlcv-new", "i": "1m", "rooms": ["pair-BTC-USD"]}
				# Server is sending Minute charts changes and some more info available on public page
				# https://cex.io/ohlcv/btc/usd
				# Periods acceptable:  1m 3m 5m 15m 30m 1h 2h 4h 6h 12h 1d 3d 1w
				({'e': 'ohlcv-init-new', }, on_ohlcv_init_new),
				({'e': 'ohlcv-new', }, on_ohlcv_new),
				({'e': 'ohlcv1m', }, on_ohlcv1m),

				# Send: {"e": "subscribe", "rooms": ["pair-BTC-USD"]}
				# Server is sendig Trading history and updates, Order Book (MD) and  Market Depth (MD-grouped)
				({'e': 'md', }, on_md),
				({'e': 'md_groupped', }, on_md_grouped),
				({'e': 'history', }, on_history),
				({'e': 'history-update', }, on_history_update),
				({'e': 'ohlcv', }, on_ohlcv),
				({'e': 'ohlcv24', }, on_ohlcv24),

			)) + sink

		async def on_notification(self, message):
			return await self.n_router(message)

	# to test reconnecting
	async def _force_disconnect():
		while True:
			try:
				await sleep(random.randrange(24, 64))
				print('test > Force disconnect')
				await client.ws.close()
			except Exception as ex:
				print("Exception at closing connection: {}".format(ex))

	client = WebSocketClientPublicData(config)

	async def public_sunscribtion_test():
		await client.send_subscribe({'e': 'subscribe', 'rooms': ['tickers', ],})
		await client.send_subscribe({"e": "init-ohlcv-new",
										"i": "1m",
										"rooms": ["pair-BTC-USD"]})
		await client.send_subscribe({"e": "subscribe",
										"rooms": ["pair-BTC-USD"]})

	try:
		loop = get_event_loop()
		loop.set_debug(True)
		loop.run_until_complete(client.run())
		ensure_future(_force_disconnect()),
		loop.run_until_complete(public_sunscribtion_test())
		loop.run_forever()
		loop.close()
	except Exception as ex:
		print("Exception at exit: {}".format(ex), sys.__stderr__)

else:
	pass


