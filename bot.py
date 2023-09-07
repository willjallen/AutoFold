import threading
import schedule
from tinydb import TinyDB, Query
from apscheduler.schedulers.background import BackgroundScheduler

from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabaseReader
from manifold_subscriber import ManifoldSubscriber

class Bot:
	def __init__(self, manifold_api: ManifoldAPI, manifold_db_reader: ManifoldDatabaseReader, manifold_subscriber: ManifoldSubscriber, strategies):
		self.manifold_api = manifold_api
		self.manifold_db_reader = manifold_db_reader
		self.manifold_subscriber = manifold_subscriber

		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
  
		# Default update me every minute
		self.manifold_subscriber.subscribe_to_user_info(userId=self.id, polling_time=60)

		self.scheduler = BackgroundScheduler({

			'apscheduler.executors.default': {
				'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
				'max_workers': '20'
			},
			'apscheduler.job_defaults.coalesce': 'false',
			'apscheduler.job_defaults.max_instances': '1',
			'apscheduler.timezone': 'UTC',
		})
  
		

  
	def start(self):
		self.scheduler.start()
  
	def stop(self):
		self.scheduler.shutdown()

	def run_strategies(self):
		pass
		
  
  