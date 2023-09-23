from concurrent.futures import ThreadPoolExecutor
from loguru import logger
import signal
import threading
import time
from autofold.strategy import Strategy
from autofold.api import ManifoldAPI
from autofold.database import ManifoldDatabase
from autofold.database import ManifoldDatabaseWriter
from autofold.database import ManifoldDatabaseReader
from autofold.subscriber import ManifoldSubscriber



class StrategyBot:
	'''
	The StrategyBot is responsible for maintaining, adding, removing, starting and stopping strategies. 
 
	Attributes:
	-----------
	- ``manifold_api``: The ManifoldAPI instance
	- ``manifold_db``: The ManifoldDatabase instance
	- ``manifold_db_reader``: The ManifoldDatabaseReader instance
	- ``manifold_db_writer``: The ManifoldDatabaseWriter instance
	- ``manifold_subscriber``: The ManifoldSubscriber instance
	''' 
	def __init__(self):
	 
		# Bind Ctrl+C to the stop function
		signal.signal(signal.SIGINT, self.stop) 
	 
		self._strategies = []
  
		self.manifold_api = ManifoldAPI()

		self.manifold_db = ManifoldDatabase()
		self.manifold_db_reader = ManifoldDatabaseReader(self.manifold_db)
		self.manifold_db_writer = ManifoldDatabaseWriter(self.manifold_db)
		self.manifold_db.create_tables()
  
		self.manifold_subscriber = ManifoldSubscriber(self.manifold_api, self.manifold_db, self.manifold_db_writer)
 
		self.shutdown_event = threading.Event()  # Create an event object
  
 
	def register_strategy(self, strategy):
		'''
		Registers a trading strategy with the bot.

		:param type strategy: Required. The strategy class to register. Must be a subclass of the `Strategy` class.
		:raises TypeError: if the strategy is not a class type.
		:raises ValueError: if the strategy is not a subclass of `Strategy`.

		Example:

		.. code-block:: python

			bot = ManifoldBot()
			bot.register_strategy(MyCustomStrategy)
		''' 
		if not isinstance(strategy, Strategy):
			logger.error(f"{strategy} must be of a subclass of type Strategy")
			return

		self._strategies.append(strategy)
 	
	def start(self):
		'''
		Starts the bot's operation.

		Initializes the manifold API, databases, subscriber, and thread executor. Schedules the strategies to run in the thread pool.

		:raises RuntimeError: if no strategies have been registered.
		''' 
		self._executor = ThreadPoolExecutor(thread_name_prefix="BOT", max_workers=20) 
	
		if len(self._strategies) == 0:
			logger.error("No strategies have been registered for the bot. Exiting.")
			self.stop()
		
		# Schedule strategies to run in the thread pool
		self.futures = [self._executor.submit(strategy.start) for strategy in self._strategies]
  
		# Loop to check for the stop condition
		while not self.shutdown_event.is_set():
			time.sleep(1)  # Sleep for 1 second

	def stop(self, *args):
		'''
		Stops the bot's operation.

		Shuts down the API, stops all running strategies, and shuts down the thread pool and subscriber.
		''' 
 		# API must be shut down first
		self.manifold_api.shutdown()

		for strategy in self._strategies:
			strategy.stop()
		self._executor.shutdown(wait=False)
  
		# Subscriber
		self.manifold_subscriber.shutdown()

		# Database 
		self.manifold_db_writer.shutdown()  
  
		self.shutdown_event.set() 


	def get_id(self):
		# Set bot id
		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
