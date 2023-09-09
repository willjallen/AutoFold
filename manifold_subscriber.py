from collections import defaultdict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from manifold_api import ManifoldAPI
from manifold_database import ManifoldDatabase
from manifold_database import ManifoldDatabaseWriter


class ManifoldSubscriber():
	def __init__(self, manifold_api: ManifoldAPI, manifold_db: ManifoldDatabase, manifold_db_writer: ManifoldDatabaseWriter):
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
  
		# Dictionary to store job callbacks, defaulting to an empty list for each job ID
		self.callbacks = defaultdict(list)
		
		# Add listener to the scheduler
		self.scheduler.add_listener(self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
  
		self.scheduler.start()
  

	def job_listener(self, event):
		'''
		Listens to job events to trigger registered callbacks
		'''
		job_id = event.job_id
		for callback in self.callbacks[job_id]:
			callback()

	def register_callback(self, job_id, callback):
		'''
		Register a callback function for a specific job ID
		'''
		self.callbacks[job_id].append(callback)

	def unregister_callback(self, job_id, callback):
		'''
		Unregister a specific callback function for a specific job ID
		'''
		if callback in self.callbacks[job_id]:
			self.callbacks[job_id].remove(callback)
			# If no more callbacks for this job ID, delete the job ID entry
			if not self.callbacks[job_id]:
				del self.callbacks[job_id]

	def subscribe_to_user_info(self, userId, polling_time=60, callback=None):
		'''
		Continuously retrieves the (LiteUser) profile of a user by their userid and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		job = self.scheduler.add_job(func=self.update_user_info, args=(userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job
	
	def update_user_info(self, userId):
		'''
		Retrieves the (LiteUser) profile of a user by their userId and updates the manifold database with the fetched data.

		:param userId: The ID of the user to be fetched.
  
		NOTE: This function is blocking.
		'''
		user = self.manifold_api.get_user_by_id(userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, users=[user]).result()

	
	def subscribe_to_user_bets(self, userId, polling_time=60, callback=None):
		''' 
  		Continuously retrieves the bets of a user by their userid and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		job = self.scheduler.add_job(func=self.update_user_bets, args=(userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_user_bets(self, userId):
		'''
		Retrieves the bets of a user by their userId and updates the manifold database with the fetched data.

		:param userId: The ID of the user whose bets are to be fetched.
  
		NOTE: This function is blocking.
		'''
		bets = self.manifold_api.retrieve_all_data(api_call_func=self.manifold_api.get_bets, max_limit=1000, api_params={"userId": userId})
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_bets, bets=bets).result()

	
	def subscribe_to_market_positions(self, marketId, userId=None, polling_time=60, callback=None):
		''' 
  		Continuously retrieves the positions of a market by its marketId and updates the manifold database with it. Optionally tracks a single user's positions.
	
		:param marketId: The id of the market
		:param userId: Optional. Tracks the positions of a specific user in a market.
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		job = self.scheduler.add_job(func=self.update_market_positions, args=(marketId, userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_market_positions(self, marketId, userId=None):
		'''
		Retrieves the positions of a market by its marketId, and optionally for a specific user, then updates the manifold database with the fetched data.

		:param marketId: The ID of the market whose positions are to be fetched.
		:param userId: Optional. If provided, fetches positions only for this user in the specified market.
  
		NOTE: This function is blocking.
		'''
		contract_metrics = self.manifold_api.get_market_positions(marketId=marketId, userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_contract_metrics, contract_metrics=contract_metrics).result()

	def subscribe_to_market_position_bets(self, contractId, userId=None, polling_time=60, callback=None):
		'''
  		Continuously retrieves the bets of contracts(positions) in a market by contractId and updates the manifold database with it. Optionally tracks a single user's positions in a market.
	
		:param marketId: The id of the market
		:param userId: Optional. Tracks the positions of a specific user in a market.
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		job = self.scheduler.add_job(func=self.update_market_position_bets, args=(contractId, userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job 

	def update_market_position_bets(self, contractId, userId):
		'''
		Retrieves the bets of contracts(positions) in a market by contractId and updates the manifold database with it. Optionally tracks a single user's positions in a market. 
		:param contractId: The id of the contract.
		:param userId: Optional. Tracks the positions of a specific user in a market contract.
		NOTE: This function is blocking.
		''' 
		bets = self.manifold_api.get_bets(contractId=contractId, userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_bets, bets=bets).result()

	def subscribe_to_all_users(self, polling_time=3600, callback=None):
		''' 
		Continuously retrieves the (LiteUser) profile of all users and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		job = self.scheduler.add_job(func=self.update_all_users, trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_all_users(self):
		'''
		Retrieves the (LiteUser) profile of all users and updates the manifold database with the fetched data.
		NOTE: This function is blocking.
		''' 
		users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, users=users).result()

	def subscribe_to_all_markets(self, polling_time=3600, callback=None):
		''' 
  		Continuously retrieves all (LiteMarket) markets and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
  
		NOTE: Currently only supports binary choice and multiple choice markets
		'''
		job = self.scheduler.add_job(func=self.update_all_markets, trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_all_markets(self):
		'''
		Retrieves all (LiteMarket) markets and updates the manifold database with the fetched data.
  
		NOTE: Currently only supports binary choice and multiple choice markets 
		NOTE: This function is blocking.
		''' 
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
  