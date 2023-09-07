from tinydb import TinyDB, Query
from apscheduler.schedulers.background import BackgroundScheduler

from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabase
from manifold_database import ManifoldDatabaseWriter


class ManifoldSubscriber():
	def __init__(self, manifold_api: ManifoldAPI, manifold_db: ManifoldDatabase, manifold_db_writer: ManifoldDatabaseWriter):
		self.subscriber_db = TinyDB("dbs/subscriber.json")
		self.manifold_api = manifold_api
		self.manifold_db = manifold_db
		self.manifold_db_writer = manifold_db_writer
		self.scheduler = BackgroundScheduler({

			'apscheduler.executors.default': {
				'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
				'max_workers': '20'
			},
			'apscheduler.job_defaults.coalesce': 'false',
			'apscheduler.job_defaults.max_instances': '1',
			'apscheduler.timezone': 'UTC',
		})
  
		self.scheduler.start()
  
   
	# def get_manifold_user_information(self):
	# 	return self.manifold_db_reader.execute_query(query="SELECT * FROM users WHERE id = ?", params=(self.manifold_bot_id,))
  	
	
	def subscribe_to_user_info(self, userId, polling_time=60):
		'''
		Continuously retrieves the (LiteUser) profile of a user by their userid and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		'''
		self.scheduler.add_job(func=self.update_user_info, args=[userId], trigger='interval', seconds=polling_time) 

	def update_user_info(self, userId):
		user = self.manifold_api.get_user_by_id(userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, users=[user]).result()
	
	def subscribe_to_user_bets(self, userId, polling_time=60):
		'''
		Continuously retrieves the bets of a user by their userid and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		''' 
		self.scheduler.add_job(func=self.update_user_bets, args=(userId), trigger='interval', seconds=polling_time) 

	def update_user_bets(self, userId):
		bets = self.manifold_api.retrieve_all_data(api_call_func=self.manifold_api.get_bets, max_limit=1000, api_params={"userId": userId})
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_bets, bets=[bets]).result()
	
	def subscribe_to_market():
		pass