import logging
import sys

from asyncio import *

from cexio.rest_client import *
from config.my_config import config


logger = logging.getLogger(__name__)
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))


if __name__ == "__main__":

	try:
		client = CEXRestClient(config)
		loop = get_event_loop()
		loop.set_debug(True)

		loop.run_until_complete(client.get("currency_limits"))
		loop.run_until_complete(client.post("price_group_distribution_report/BTC/USD", {'side': 'buy'}))
		loop.run_until_complete(client.get("ohlcv/hd/20160228/BTC/USD"))

		loop.run_until_complete(client.post("balance/"))
		loop.run_until_complete(client.post("open_orders/BTC/USD/"))
		loop.run_until_complete(client.post("active_orders_status",
											{ 'orders_list': ['8550492', '8550495', '8550497', ], }))
		loop.close()
	except Exception as ex:
		print(ex, sys.__stderr__)

else:
	pass
