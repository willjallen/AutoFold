import toml 
import inspect
from tinydb import TinyDB, Query
from concurrent.futures import ThreadPoolExecutor

from strategies.strategy import Strategy
from manifold.manifold_api import ManifoldAPI
from manifold.manifold_database import ManifoldDatabaseReader
from manifold.manifold_subscriber import ManifoldSubscriber

def get_strategy_class_from_file(strategy_filename):
	module = __import__(f"strategies.{strategy_filename[:-3]}", fromlist=[strategy_filename[:-3]])
	
	# Iterate over each member of the module
	for name, obj in inspect.getmembers(module):
		# Check if the member is a class, is not the Strategy base class, and is a subclass of Strategy
		if inspect.isclass(obj) and obj != Strategy and issubclass(obj, Strategy):
			return obj  # Return the found strategy class

	# If no matching class is found, return None
	return None

class Bot:
	def __init__(self, manifold_api: ManifoldAPI, manifold_db_reader: ManifoldDatabaseReader, manifold_subscriber: ManifoldSubscriber):

		self.manifold_api = manifold_api
		self.manifold_db_reader = manifold_db_reader
		self.manifold_subscriber = manifold_subscriber

		# Load the configuration file
		with open("config.toml", "r") as config_file:
			self.config = toml.load(config_file)


		# Load strategies
		self.strategy_objects = {}

		# Create instances for each strategy defined in the config
		for strategy_name, strategy_info in self.config["strategies"].items():
			strategy_filename = strategy_info["filename"]
			strategy_class = get_strategy_class_from_file(strategy_filename)
			if strategy_class:
				self.strategy_objects[strategy_name] = strategy_class(bot=self, manifold_api=self.manifold_api, manifold_db_reader=self.manifold_db_reader, manifold_subscriber=self.manifold_subscriber)  # Instantiate as needed with any parameters

		# Set bot id
		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
  
		self.executor = ThreadPoolExecutor(thread_name_prefix="BOT", max_workers=20)
  
		
	def start(self):
		# Schedule strategies to run in the thread pool
		self.futures = {strategy_name: self.executor.submit(strategy_class.run) for strategy_name, strategy_class in self.strategy_objects.items()}

	def shutdown(self):
		for strategy_name, strategy_class in self.strategy_objects.items():
			strategy_class.shutdown()

		self.executor.shutdown(wait=False)

	
