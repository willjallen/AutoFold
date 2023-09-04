import threading
import schedule
from tinydb import TinyDB, Query
from apscheduler.schedulers.background import BackgroundScheduler

from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabase
from manifold_database import ManifoldDatabaseReader
from manifold_database import ManifoldDatabaseWriter

class Bot:
	def __init__(self, manifold_api: ManifoldAPI, manifold_db: ManifoldDatabase, manifold_db_reader: ManifoldDatabaseReader, manifold_db_writer: ManifoldDatabaseWriter, strategies):
		self.manifold_api = manifold_api
		self.manifold_db = manifold_db
		self.manifold_db_reader = manifold_db_reader
		self.manifold_db_writer = manifold_db_writer

		self.manifold_bot_id = "" 

		self.update_bot_manifold_information()
		print(self.get_bot_manifold_information())
		self.scheduler = BackgroundScheduler({

			'apscheduler.executors.default': {
				'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
				'max_workers': '20'
			},
			'apscheduler.job_defaults.coalesce': 'false',
			'apscheduler.job_defaults.max_instances': '1',
			'apscheduler.timezone': 'UTC',
		})
  
		'''
		########################################################
		####                      JOBS                      ####
		########################################################
		'''
		
		self.scheduler.add_job(self.update_bot_manifold_information, 'interval', minutes=1)
		# Add a job to call update bot information every minute
		# Implement this
		

  
	def start(self):
		self.scheduler.start()
  
	def update_bot_manifold_information(self):
		bot_user = self.manifold_api.get_me().result()
		if self.manifold_bot_id == "":
			self.manifold_bot_id = str(bot_user["id"])
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, users=[bot_user]).result()
   
	def get_bot_manifold_information(self):
		return self.manifold_db_reader.execute_query(query="SELECT * FROM users WHERE id = ?", params=(self.manifold_bot_id,))
  
	def run_strategy_one(self):
		pass
		
  
  