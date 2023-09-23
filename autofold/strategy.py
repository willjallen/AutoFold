from abc import ABC, abstractmethod
from tinydb import TinyDB


class Strategy(ABC):

	def __init__(self, db_name: str, strategy_bot):
		'''
		Initializer for the Strategy class.

		:param str db_name: Required. The name of the database file to use, without the extension.
		:param autofold strategy_bot: Required. An instance of the autofold class.

		.. note::

			All child classes of Strategy are provided a local tinydb for non-volatile storage if needed.
			Note that tinydb is NOT threadsafe; access to a db should only occur from within the strategy that created it.
			Feel free to use your own storage medium as you see fit.

		Attributes:
		-----------
		- ``strategy_bot``: The ManifoldBot instance.
		- ``manifold_api``: The ManifoldAPI instance extracted from strategy_bot.
		- ``manifold_db_reader``: The ManifoldDatabaseReader instance extracted from strategy_bot.
		- ``manifold_subscriber``: The ManifoldSubscriber instance extracted from strategy_bot.
		- ``db``: The TinyDB instance for this strategy.
		''' 
		self.strategy_bot = strategy_bot
		self.manifold_api = strategy_bot.manifold_api
		self.manifold_db_reader = strategy_bot.manifold_db_reader
		self.manifold_subscriber = strategy_bot.manifold_subscriber
		self.db = TinyDB('dbs/'+db_name+'.json')
	
	@abstractmethod
	def start(self, *args, **kwargs):
		'''
		Abstract method to start the strategy.

		.. note::
			This method must be implemented in subclasses.

		:param args: Additional positional arguments.
		:param kwargs: Additional keyword arguments.
		'''
		pass
	
	@abstractmethod
	def stop(self, *args, **kwargs):
		'''
		Abstract method to stop the strategy.

		.. note::
			This method must be implemented in subclasses.

		:param args: Additional positional arguments.
		:param kwargs: Additional keyword arguments.
		'''
		pass
