from loguru import logger
from collections import defaultdict
from typing import List, Callable, Dict, DefaultDict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from autofold.api import ManifoldAPI
from autofold.database import ManifoldDatabase
from autofold.database import ManifoldDatabaseWriter



'''
TODO:

This whole thing has a litany of edge cases and problems when there are multiple strategies involved.
As it stands now it *works*, just not as robust as I would like.

Thoughts:
All callbacks associated with job should be fired. 
Right now it's possible for a subscriber to miss a callback if

Replace APScheduler with custom scheduler
- Job objects should be stored with function signature for proper sharing
- Job run interval should be min(polling_times) (coalesce jobs)
- Polling times per subscriber should be respected
'''

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
			'apscheduler.job_defaults.coalesce': 'true',
			'apscheduler.job_defaults.max_instances': '1',
		})
  
		# Dictionary to store job callbacks, defaulting to an empty list for each job ID
		self.callbacks: DefaultDict[str, List[Callable]] = defaultdict(list)
		
		# Add listener to the scheduler
		self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
  
		self.scheduler.start()
  
	def shutdown(self):
		logger.debug("Shutting down manifold subscriber")
		self.scheduler.remove_listener(self._job_listener)
		self.scheduler.shutdown(wait=True)
		logger.debug("Manifold subscriber shut down")

	def _job_listener(self, event):
		'''
		Listens to job events to trigger registered callbacks
		'''
		job_id = event.job_id
		for callback in self.callbacks[job_id]:
			callback()

	def _get_job_key(self, func, args, polling_time):
		"""
		Generate a unique key for a job based on function, arguments, and polling time.
		"""
		return f"{func.__name__}_{str(args)}_{polling_time}"

	def _add_or_update_job(self, func, args, polling_time, callback):
		"""
		Check if a job with the given parameters already exists. If so, register the new callback.
		If not, create a new job.
		"""
		job_key = self._get_job_key(func, args, polling_time)
		if job_key in self.callbacks:
			self.register_callback(job_key, callback)
		else:
			job = self.scheduler.add_job(func=func, args=args, trigger='interval', seconds=polling_time)
			self.callbacks[job_key] = []
			self.register_callback(job_key, callback)

	def register_callback(self, job_id, callback):
		'''
		Register a callback function for a specific job ID
		'''
		logger.debug(f"Adding callback {callback.__name__} to job id {job_id}")
		self.callbacks[job_id].append(callback)

	def unregister_callback(self, job_id, callback):
		'''
		Unregister a specific callback function for a specific job ID
		'''
		if callback in self.callbacks[job_id]:
			logger.debug(f"Removing callback {callback.__name__} from job id {job_id}")
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
		logger.debug(f"Subscribing to profile of user {userId} with polling time {polling_time} seconds")
		job = self.scheduler.add_job(func=self.update_user_info, args=(userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job
	
	def update_user_info(self, userId):
		'''
		Retrieves the (LiteUser) profile of a user by their userId and updates the manifold database with the fetched data.

		:param userId: The Id of the user to be fetched.
  
		NOTE: This function is blocking.
		'''
		logger.debug(f"Updating profile for user {userId}")
		user = self.manifold_api.get_user_by_id(userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, data=[user]).result()

	
	def subscribe_to_bets(self, userId=None, username=None, contractId=None, contractSlug=None, polling_time=60, callback=None):
		'''Continuously retrieves the bets via a single value or combination of:

		- userId
		- username
	 	- contractId
	 	- contractSlug 
	  
		and updates the manifold database with it.

		:param userId: The Id of the user.
		:param username: The username of the user.
		:param contractId: The Id of the contract (market).
		:param contractSlug: The URL slug of the contract (market). 
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
		logger.debug(f"Subscribing to bets with userId={userId}, username={username}, contractId={contractId}, contractSlug={contractSlug}, and polling_time={polling_time} seconds with callback {callback.__name__ if callback else None}.")
		job = self.scheduler.add_job(func=self.update_user_bets, args=(userId, username, contractId, contractSlug), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_bets(self, userId=None, username=None, contractId=None, contractSlug=None):
		'''
		Retrieves the bets of a user by their userId and updates the manifold database with the fetched data.

		:param userId: Optional. If set, the response will include only bets created by this user.
		:param username: Optional. If set, the response will include only bets created by this user.
		:param contractId: Optional. If set, the response will only include bets on this contract.
		:param contractSlug: Optional. If set, the response will only include bets on this contract.
  
		NOTE: This function is blocking.
		'''
		logger.debug(f"Updating bets with userId={userId}, username={username}, contractId={contractId} and contractSlug={contractSlug}")
  
		# Use locals to get the current local variables as a dictionary
		api_params = locals().copy()
		# Remove the 'self' key
		api_params.pop('self') 

		bets = self.manifold_api.retrieve_all_data(api_call_func=self.manifold_api.get_bets, max_limit=1000, **api_params)
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_bets, data=bets).result()

	
	def subscribe_to_market_positions(self, marketId, userId=None, polling_time=60, callback=None):
		''' 
		NOTE: Due to https://github.com/manifoldmarkets/manifold/issues/2031 this function will only subscribe to the top 4000 positions ranked by profit.

  		Continuously retrieves the positions of a market by its marketId and updates the manifold database with it. Optionally tracks a single user's positions.
	
		:param marketId: The id of the market
		:param userId: Optional. Tracks the positions of a specific user in a market.
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
  
		logger.debug(f"Subscribing to market positions for marketId={marketId} and userId={userId} with a polling time of {polling_time} seconds and callback {callback.__name__ if callback else None}")
  
		job = self.scheduler.add_job(func=self.update_market_positions, args=(marketId, userId), trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_market_positions(self, marketId, userId=None):
		'''
		NOTE: Due to https://github.com/manifoldmarkets/manifold/issues/2031 this function will only retrieve to the top 4000 positions ranked by profit.

		Retrieves the positions of a market by its marketId, and optionally for a specific user, then updates the manifold database with the fetched data.

		:param marketId: The ID of the market whose positions are to be fetched.
		:param userId: Optional. If provided, fetches positions only for this user in the specified market.
  
		NOTE: This function is blocking.
		'''
  
		logger.debug(f"Updating market positios for marketId={marketId} and userId={userId}")
  
		contract_metrics = self.manifold_api.get_market_positions(marketId=marketId, order='profit', top=2000, userId=userId).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_contract_metrics, data=contract_metrics).result()

	def subscribe_to_all_users(self, polling_time=3600, callback=None):
		''' 
		Continuously retrieves the (LiteUser) profile of all users and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
	
		logger.debug(f"Subscribing to profiles of all users with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")
  
		job = self.scheduler.add_job(func=self.update_all_users, trigger='interval', seconds=polling_time)
		if callback:
			self.register_callback(job.id, callback)
		return job

	def update_all_users(self):
		'''
		Retrieves the (LiteUser) profile of all users and updates the manifold database with the fetched data.
		NOTE: This function is blocking.
		''' 
	
		logger.debug(f"Updating profiles of all users")
  
		users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, data=users).result()

	def subscribe_to_all_markets(self, polling_time=3600, callback=None):
		''' 
  		Continuously retrieves all (LiteMarket) markets and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
  
		NOTE: Currently only supports binary choice and multiple choice markets
		'''
  
		logger.debug(f"Subscribing to all markets with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")
  
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
	
		logger.debug("Updating all markets")
  
		markets = self.manifold_api.retrieve_all_data(self.manifold_api.get_markets, max_limit=1000)
		binary_choice_markets = []
		multiple_choice_markets = []
		for market in markets:
			if market["outcomeType"] == "BINARY":
				binary_choice_markets.append(market)
			elif market["outcomeType"] == "MULTIPLE_CHOICE":
				multiple_choice_markets.append(market)
   
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_binary_choice_markets, data=binary_choice_markets).result()
		self.manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_multiple_choice_markets, data=multiple_choice_markets).result()
  