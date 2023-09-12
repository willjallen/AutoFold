import toml 
import inspect
from tinydb import TinyDB, Query
from apscheduler.schedulers.background import BackgroundScheduler

from strategies.strategy import Strategy
from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabaseReader
from manifold_subscriber import ManifoldSubscriber

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
		strategy_objects = {}

		# Create instances for each strategy defined in the config
		for strategy_name, strategy_info in self.config["strategies"].items():
			strategy_filename = strategy_info["filename"]
			strategy_class = get_strategy_class_from_file(strategy_filename)
			if strategy_class:
				strategy_objects[strategy_name] = strategy_class(bot=self, manifold_api=self.manifold_api, manifold_db_reader=self.manifold_db_reader, manifold_subscriber=self.manifold_subscriber)  # Instantiate as needed with any parameters

		print(strategy_objects)

		# Set baseline bot info
		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
  
		# Set default subscribers
		# self.bot_user_info_update_interval = self.config["bot"]["bot_user_info_update_interval"]
		# if self.bot_user_info_update_interval != -1:
		# 	self.manifold_subscriber.subscribe_to_user_info(userId=self.id, polling_time=self.bot_user_info_update_interval)

		# self.all_users_update_interval = self.config["bot"]["all_users_update_interval"]
		# if self.all_users_update_interval != -1:
		# 	self.manifold_subscriber.subscribe_to_all_users(polling_time=self.all_users_update_interval)

		# self.all_markets_update_interval = self.config["bot"]["all_markets_update_interval"]
		# if self.all_markets_update_interval != -1:
		# 	self.manifold_subscriber.subscribe_to_all_markets(polling_time=self.all_markets_update_interval)

		self.scheduler = BackgroundScheduler({

			'apscheduler.executors.default': {
				'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
				'max_workers': '20'
			},
			'apscheduler.job_defaults.coalesce': 'false',
			'apscheduler.job_defaults.max_instances': '1',
			'apscheduler.timezone': 'UTC',
		})

		for strategy_name, strategy_class in strategy_objects.items():
			self.scheduler.add_job(func=strategy_class.run)
  
		
	def start(self):
		self.scheduler.start()
  
	def stop(self):
		self.scheduler.shutdown()

	def get_id():
		pass
 
	def get_bot_user_info():
		pass

	
