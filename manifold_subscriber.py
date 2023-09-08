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
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_bets, bets=bets).result()
	
	def subscribe_to_market(self, marketId):
		pass

	def subscribe_to_all_users(self, polling_time=3600):
		self.scheduler.add_job(func=self.update_all_users, trigger='interval', seconds=polling_time) 

	def update_all_users(self):
		users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, users=users).result()

	def subscribe_to_all_markets(self, polling_time=3600):
		self.scheduler.add_job(func=self.update_all_markets, trigger='interval', seconds=polling_time) 

	def update_all_markets(self):
		markets = self.manifold_api.retrieve_all_data(self.manifold_api.get_markets, max_limit=1000)
		binary_choice_markets = []
		multiple_choice_markets = []
		for market in markets:
			if market["outcomeType"] == "BINARY":
				binary_choice_markets.append(market)
			elif market["outcomeType"] == "MULTIPLE_CHOICE":
				multiple_choice_markets.append(market)
   
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_binary_choice_markets, markets=binary_choice_markets).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_multiple_choice_markets, markets=multiple_choice_markets).result()
  