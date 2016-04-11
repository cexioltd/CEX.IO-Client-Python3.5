from setuptools import *

from cexio.version import version


setup(
	name='cexio',
	version=version,
	description='CEX.IO Client (WebSocket and REST API basic client functionality on Python3.5)',
	url='https://github.com/cexioltd/CEX.IO-Client-Python3.5',
	license='MIT License',
	author='Yegor Parusymov',
	author_email='yegor.parusymov@gmail.com',
	install_requires=[
		'websockets>=3.0',
		'aiohttp>=0.21.5',
	],
	packages=['cexio'],
	include_package_data=True,
	platforms='any',
	test_suite='cexio.test',
	classifiers=[
		'Programming Language :: Python',
		'Development Status :: 1.0 - Beta',
		'Natural Language :: English',
		'Intended Audience :: traders, developers',
		'License :: MIT License',
		'Operating System :: OS Independent',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'Topic :: Software Development :: Libraries :: Client API',
		'Topic :: Trading :: BitCoin',
	],
)
