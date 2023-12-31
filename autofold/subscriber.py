import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Full
from loguru import logger
from collections import defaultdict
from typing import List, Callable, Dict, DefaultDict
from autofold.api import ManifoldAPI
from autofold.database import ManifoldDatabase
from autofold.database import ManifoldDatabaseWriter
from typing import Callable, List, Any, Union
from concurrent.futures import Future

from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    FINISHED = "finished"
    EXECUTING = "executing"

class JobType(Enum):
	INTERVAL = "interval"
	ONEOFF = "oneoff"
 
class JobAction(Enum):
    ADD = "add"
    REMOVE = "remove"

    
class Job:
	def __init__(self, action: str, function: Callable, params: Any,
				 job_type: str, callbacks: list[dict] = None, future: Union[None, Future] = None):
		self.action = action  # JobAction.ADD or JobAction.REMOVE
		self.status = JobStatus.PENDING # The current status of the job (pending, executing, finished) 
		self.function = function  # Function responsible for the task
		self.params = params  # Parameters needed for the function
		self.job_type = job_type  # JobType.ONEOFF or JobType.INTERVAL
		self.future = future  # Used for oneoff jobs
		self.callbacks = callbacks if callbacks else []  # List of callbacks
		self.last_execution_time = 0  # Timestamp of the last update
		self.next_execution_time = None  # When the job is set to be executed next
		self.update_interval = None if len(self.callbacks) == 0 else min(cb['polling_time'] for cb in self.callbacks)    # Derived from min polling_times of callbacks

	def add_callback(self, callback):
		"""
		Add a callback with its polling_time.
		"""
		callback = {
			'function': callback['function'],
			'polling_time': callback['polling_time'],
			'next_call_time': time.time() + callback['polling_time']
		}
		self.callbacks.append(callback)
		self.update_interval = min(cb['polling_time'] for cb in self.callbacks)

	def remove_callback(self, callback_function: Callable):
		"""
		Remove a callback by its function.
		"""
		self.callbacks = [cb for cb in self.callbacks if cb['function'] != callback_function]
		if self.callbacks:
			self.update_interval = min(cb['polling_time'] for cb in self.callbacks)
		else:
			self.update_interval = None

	def execute(self):
		"""
		Executes the job's function with its parameters.
		"""
		self.function(*self.params)
		self.last_execution_time = time.time()  # Record the last execution time
 
		if self.future:
			self.future.set_result(True)
			self.future = None
 
		if self.job_type == JobType.ONEOFF:
			self.status = JobStatus.FINISHED
  
		if self.job_type == JobType.INTERVAL:
			self.next_execution_time = self.last_execution_time + self.update_interval # Set next execution time
			self.status = JobStatus.PENDING


	def __repr__(self):
		return f"<Job(function={self.function.__name__}, params={self.params})>"

class ManifoldSubscriber():
	def __init__(self, manifold_api: ManifoldAPI, manifold_db: ManifoldDatabase, manifold_db_writer: ManifoldDatabaseWriter):
		logger.debug("Initializing ManifoldSubscriber")
		self._manifold_api = manifold_api
		self._manifold_db = manifold_db
		self._manifold_db_writer = manifold_db_writer
 
		self._jobs = []
  
		self._thread = threading.Thread(target=self._run, name="MF_SUBSCRIBER") 
		self._executor = ThreadPoolExecutor(thread_name_prefix="MF_SUBSCRIBER_EXECUTOR", max_workers=20)
		self._jobs_queue = Queue(maxsize=20)
 
		self.running = True
	
		self._thread.start()
		logger.debug("ManifoldSubscriber initialized")
  
  
	def is_alive(self):
		"""
		Checks if the scheduler is running.

		:return: True if scheduler is running, False otherwise.
		:rtype: bool
		"""
		return self._thread.is_alive()

	def shutdown(self):
		logger.debug("Shutting down manifold subscriber")
		self.running = False
		self._executor.shutdown(wait=True)
		self._thread.join()
		logger.debug("Manifold subscriber shut down")

	def _run(self):
		logger.debug("Starting ManifoldSubscriber scheduler")
		while self.running:
			# Process adding/removing jobs
			while not self._jobs_queue.empty():
				job = self._jobs_queue.get()
				if job.action == JobAction.ADD:
					logger.debug(f"Adding job {job}")
					self._add_job(job)
				elif job.action == JobAction.REMOVE:
					logger.debug(f"Removing job {job}")
					self._remove_job(job)

			# Execute jobs
			current_time = time.time()
			for job in self._jobs:
				# Check if it's time for the job to be executed
				if job.next_execution_time <= current_time and job.status == JobStatus.PENDING:
					job.status = JobStatus.EXECUTING
					logger.debug(f"Executing job {job}")
					future = self._executor.submit(job.execute)

				# Check callbacks
				for callback in job.callbacks:
					if callback["next_call_time"] <= current_time and job.status != JobStatus.EXECUTING:
						logger.debug(f"Firing callback {callback} from job {job}")
						# Execute the callback
						callback["function"]()
						# Update next call time
						callback["next_call_time"] = current_time + callback["polling_time"]
	  
			time.sleep(0.1)

	def _add_job(self, new_job):
	 
		# Coalesce into existing job
		# An interval job always takes precedence for the job type
		for job in self._jobs:
			if job.function == new_job.function and job.params == new_job.params:
				# One-off job
				if new_job.job_type == JobType.ONEOFF:
					# Change status if applicable
					if job.status == JobStatus.FINISHED:
						job.status = JobStatus.PENDING
					# Set the next execution time to now
					job.next_execution_time = time.time()
					# Set the future
					job.future = new_job.future
					# Done
					return
   
				# Interval job
				if new_job.job_type == JobType.INTERVAL:
					# Job becomes an interval type
					job.job_type = JobType.INTERVAL
					# Change status if applicable
					if job.status == JobStatus.FINISHED:
						job.status = JobStatus.PENDING
					# Is there a callback?
					if len(new_job.callbacks) != 0:
						# Yes, add the new callback
						new_callback = new_job.callbacks[0]
						job.add_callback(new_callback)
						# Done
						return
  
		# New job
		if new_job.job_type == JobType.ONEOFF:
			# Set next execution time to now
			new_job.next_execution_time = time.time()
  
		elif new_job.job_type == JobType.INTERVAL:
			# Set next execution time
			new_job.next_execution_time = time.time() + new_job.update_interval
			# Set callback next call time
			new_job.callbacks[0]["next_call_time"] = time.time() + new_job.callbacks[0]["polling_time"]

		self._jobs.append(new_job)

	def _remove_job(self, job_to_remove):
		# Remove the job by comparing function and parameters
		self._jobs = [job for job in self._jobs if not (job.function == job_to_remove.function and job.params == job_to_remove.params)]

	def subscribe_to_user(self, user_id, polling_time, callback):
		'''
		Continuously retrieves the profile of a specified user and updates the database.

		:param str user_id:
			Required. The ID of the user to subscribe to.
		:param int polling_time:
			Required. The number of seconds between each profile update. 
		:param function callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.
		
		:return:
			None
		'''
		logger.debug(f"Subscribing to profile of user {user_id} with polling time {polling_time} seconds")
  
		job = Job(action=JobAction.ADD, 
				function=self._update_user,
			   	params=(user_id,),
				job_type=JobType.INTERVAL,
				callbacks=[                           
				{
					"function": callback,
					"polling_time": polling_time,
				}
			])
  
		self._jobs_queue.put(job)

	def unsubscribe_to_user(self, user_id):
		'''
		Stops the continuous retrieval of the profile of a specified user and removes all associated callbacks.

		:param str user_id:
			Required. The ID of the user to unsubscribe from.

		:return:
			None
		'''
	 
		logger.debug(f"Unsubscribing to profile of user {user_id}")
	 
		job = Job(action=JobAction.REMOVE, 
				function=self._update_user,
			   	params=(user_id,))

		self._jobs_queue.put(job)

	def update_user(self, user_id):
		'''
		Retrieves the profile of a specified user by their user_id and updates the database with the fetched data.

		:param str user_id:
			Required. The ID of the user whose profile needs to be updated.

		:return:
			A Future object representing the eventual result of the API call and database update.

		:rtype: Future
		'''
		logger.debug(f"Updating profile of user {user_id}")
	 
		future = Future()	

		job = Job(action=JobAction.ADD, 
				function=self._update_user,
			   	params=(user_id,),
       			job_type=JobType.ONEOFF,
          		future=future)

		self._jobs_queue.put(job)
		return future
 
	def _update_user(self, user_id):
		logger.debug(f"Updating profile for user {user_id}")
		user = self._manifold_api.get_user_by_id(user_id=user_id).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_users, data=[user]).result()

	def subscribe_to_all_users(self, polling_time, callback):
		'''
		Continuously retrieves the (LiteUser) profile of all users and updates the manifold database with it.

		:param int polling_time:
			Required. The number of seconds between updates.
		:param function callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.

		:returns: 
			None
		'''
	
		logger.debug(f"Subscribing to profiles of all users with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")

		job = Job(action=JobAction.ADD,
		  function=self._update_all_users,
		  params=(),
		  job_type=JobType.INTERVAL,
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])

		self._jobs_queue.put(job) 

	def unsubscribe_to_all_users(self):
		'''
		Stops the continuous retrieval of the (LiteUser) profiles of all users and updates to the manifold database.
		
		:returns: 
			None
		''' 
		job = Job(action=JobAction.REMOVE,
		  function=self._update_all_users,
		  params=()) 

		self._jobs_queue.put(job)
  
	def update_all_users(self):
		'''
		Retrieves the (LiteUser) profile of all users and updates the manifold database with the fetched data. 

		.. note:: 
			This function can take roughly 5 seconds to complete given the current API speeds.

		:return:
			A Future object representing the eventual result of the API call and database update.
		:rtype:
			Future
		'''
		future = Future()	
  
		job = Job(action=JobAction.ADD,
		  function=self._update_all_users,
		  params=(),
		  job_type=JobType.ONEOFF,
		  future=future)
   
		self._jobs_queue.put(job)
		return future
  
	def _update_all_users(self):
		logger.debug(f"Updating profiles of all users")
  
		users = self._manifold_api.retrieve_all_data(self._manifold_api.get_users, max_limit=1000)
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_users, data=users).result()
	
	def subscribe_to_bets(self, user_id, username, contract_id, contract_slug, polling_time, callback):
		'''
		Continuously retrieves bets based on a single value or a combination of the following:

		- user_id
		- username
		- contract_id
		- contract_slug
  
		Set unused values to None.
		
		Updates the manifold database accordingly.

		:param str user_id:
			Optional. The ID of the user whose bets are to be retrieved.
		:param str username:
			Optional. The username of the user whose bets are to be retrieved.
		:param str contract_id:
			Optional. The ID of the contract (market) whose bets are to be retrieved.
		:param str contract_slug:
			Optional. The URL slug of the contract (market) whose bets are to be retrieved.
		:param int polling_time:
			Required. The number of seconds between each bet update.
		:param function callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.
		
		:return:
			None
		'''
		logger.debug(f"Subscribing to bets with user_id={user_id}, username={username}, contract_id={contract_id}, contract_slug={contract_slug}, and polling_time={polling_time} seconds with callback {callback.__name__ if callback else None}.")
  
		job = Job(action=JobAction.ADD, 
		  function=self._update_bets,
		  params=(user_id, username, contract_id, contract_slug),
		  job_type=JobType.INTERVAL,
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])

		self._jobs_queue.put(job)

	def unsubscribe_to_bets(self, user_id, username=None, contract_id=None, contract_slug=None):
		'''
		Stops the continuous retrieval of bets based on a single value or a combination of the following:

		- user_id
		- username
		- contract_id
		- contract_slug

		Set unused values to None.
		
		:param str user_id:
			Optional. The ID of the user to unsubscribe from.
		:param str username:
			Optional. The username of the user to unsubscribe from.
		:param str contract_id:
			Optional. The ID of the contract (market) to unsubscribe from.
		:param str contract_slug:
			Optional. The URL slug of the contract (market) to unsubscribe from.
		
		:return:
			None
		''' 
		job = Job(action=JobAction.REMOVE,
		  function=self._update_bets,
		  params=(user_id, username, contract_id, contract_slug))

		self._jobs_queue.put(job)

	def update_bets(self, user_id, username=None, contract_id=None, contract_slug=None):
		'''
		Retrieves bets based on a single value or a combination of the following:

		- user_id
		- username
		- contract_id
		- contract_slug
		
		Updates the manifold database with the retrieved data.

		:param str user_id:
			Optional. The ID of the user whose bets are to be retrieved.
		:param str username:
			Optional. The username of the user whose bets are to be retrieved.
		:param str contract_id:
			Optional. The ID of the contract (market) whose bets are to be retrieved.
		:param str contract_slug:
			Optional. The URL slug of the contract (market) whose bets are to be retrieved.
		
		:return:
			A Future object representing the eventual result of the API call and database update.
		:rtype: Future
		'''

		future = Future()	
  
		job = Job(action=JobAction.ADD,
		  function=self._update_bets,
		  params=(user_id, username, contract_id, contract_slug),
		  job_type=JobType.ONEOFF,
		  future=future)

   
		self._jobs_queue.put(job)
		return future
		
	def _update_bets(self, user_id, username=None, contract_id=None, contract_slug=None):
		logger.debug(f"Updating bets with user_id={user_id}, username={username}, contract_id={contract_id} and contract_slug={contract_slug}")
  
		bets = self._manifold_api.retrieve_all_data(api_call_func=self._manifold_api.get_bets, max_limit=1000, user_id=user_id, username=username, contract_id=contract_id,  contract_slug=contract_slug)
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_bets, data=bets).result()

	def subscribe_to_market_positions(self, market_id, user_id, polling_time=60, callback=None):
		'''
		.. note:: 
			Due to https://github.com/manifoldmarkets/manifold/issues/2031, this function will only subscribe to the top 4000 positions by order.
		
		Continuously retrieves the positions of a market by its market_id and updates the manifold database. Optionally tracks positions of a specific user.

		:param str market_id:
			Required. The ID of the market to track.
		:param str user_id:
			Optional. If specified, tracks the positions of this specific user in the market.
		:param int polling_time:
			Required. The number of seconds between updates.
		:param function callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.

		:return:
			None
		'''
  
		job = Job(action=JobAction.ADD,
		  function=self._update_market_positions,
		  params=(market_id, user_id),
		  job_type=JobType.INTERVAL,
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])
  
		self._jobs_queue.put(job)

	def unsubscribe_to_market_positions(self, market_id, user_id):
		'''
		Stops the subscription to the positions of a market by its market_id. Optionally stops tracking positions of a specific user.

		:param str market_id:
			Required. The ID of the market to stop tracking.
		:param str user_id:
			Optional. If specified, stops tracking the positions of this specific user in the market.

		:return:
			None
		''' 
		job = Job(action=JobAction.REMOVE,
		  function=self._update_market_positions,
		  params=(market_id, user_id))

		self._jobs_queue.put(job)
  
	def update_market_positions(self, market_id, user_id):
		'''
		.. note:: 
			Due to https://github.com/manifoldmarkets/manifold/issues/2031 this function will only retrieve the top 4000 positions by order.
		
		Retrieves the positions of a market by its market_id and updates the manifold database with the fetched data. Optionally retrieves positions for a specific user.

		:param str market_id:
			Required. The ID of the market whose positions are to be fetched.
		:param str user_id:
			Optional. If specified, fetches positions only for this user in the specified market.

		:returns: 
			A Future object representing the eventual result of the API call and database update.
		:rtype:
			Future
		'''
		future = Future()	
  
		job = Job(action=JobAction.ADD,
		  function=self._update_market_positions,
		  params=(market_id, user_id),
		  job_type=JobType.ONEOFF,
		  future=future)
		self._jobs_queue.put(job)
		return future

	def _update_market_positions(self, market_id, user_id):
  
		logger.debug(f"Updating market positions for market_id={market_id} and user_id={user_id}")
  
		contract_metrics = self._manifold_api.get_market_positions(market_id=market_id, order='profit', top=2000, user_id=user_id).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_contract_metrics, data=contract_metrics).result()


	def subscribe_to_market(self, market_id, polling_time, callback):
		'''
		Continuously retrieves the (FullMarket) market for a specified market_id and updates the manifold database with the fetched data.

		.. note:: 
			Only BC and MC markets right now.

		:param str market_id:
			Required. The ID of the market whose positions are to be fetched.
		:param int polling_time:
			Required. The number of seconds between updates. 
		:param callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.

		:returns: 
			None
		'''
		job = Job(action=JobAction.ADD,
		  function=self._update_market,
		  params=(market_id,),
		  job_type=JobType.INTERVAL,
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])
  
		self._jobs_queue.put(job)

	def unsubscribe_to_market(self, market_id):
		'''
		Stops the subscription to a market by its market_id.

		:param str market_id:
			Required. The ID of the market to stop tracking.

		:return:
			None
		''' 
		job = Job(action=JobAction.REMOVE,
		  function=self._update_market,
		  params=(market_id))

		self._jobs_queue.put(job)

	def update_market(self, market_id):
		'''
		Retrieves the (FullMarket) market for a specified market_id and updates the manifold database with the fetched data.

		.. note:: 
			Only BC and MC markets right now.

		:param str market_id:
			Required. The ID of the market to be fetched.

		:returns: 
			A Future object representing the eventual result of the API call and database update.

		:rtype:
			Future
		'''

		future = Future()	
  
		job = Job(action=JobAction.ADD,
		  function=self._update_market,
		  params=(market_id,),
		  job_type=JobType.ONEOFF,
		  future=future)
		self._jobs_queue.put(job)

		return future
	
 
	def _update_market(self, market_id):
		logger.debug(f"Updating market for market_id={market_id}")
  
		market = self._manifold_api.get_market_by_id(market_id=market_id).result()
		market["lite"] = False
		if market["outcomeType"] == "BINARY":
			self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_binary_choice_markets, data=[market]).result()
		elif market["outcomeType"] == "MULTIPLE_CHOICE":
			self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_multiple_choice_markets, data=[market]).result()
		else:
			logger.error(f"Error, only binary and multiple choice markets are currently supported. Market is of type {market['outcomeType']}")
     

	def subscribe_to_all_markets(self, polling_time, callback):
		'''
		Continuously retrieves all (LiteMarket) markets and updates the manifold database.

		.. note:: 
			Only BC and MC markets right now.

		:param int polling_time:
			Required. The number of seconds between updates. 
		:param callback:
			Required. A function to be called when the job finishes. The function should accept no arguments.

		:returns: 
			None
		'''
  
		logger.debug(f"Subscribing to all markets with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")
 
		job = Job(action=JobAction.ADD,
			function=self._update_all_markets,
			params=(),
			job_type=JobType.INTERVAL,
			callbacks=[
				{
					"function": callback,
					"polling_time": polling_time	
				}
			])

		self._jobs_queue.put(job) 

	def unsubscribe_to_all_markets(self):
		'''
		Stops the continuous retrieval of all (LiteMarket) markets and removes the corresponding job from the job queue.

		:returns: 
			None
		''' 
		job = Job(action=JobAction.REMOVE,
		  function=self._update_all_markets,
		  params=()) 

		self._jobs_queue.put(job)

	def update_all_markets(self):
		'''
		Retrieves information on all markets and updates the manifold database with the fetched data.
  
		.. note::
			This function can take roughly 45 seconds to complete given the current API speeds.

		:returns: 
			A Future object representing the eventual result of the API call and database update.
		:rtype:
			Future
		'''  
		future = Future()	
  
		job = Job(action=JobAction.ADD,
			function=self._update_all_markets,
			params=(),
			job_type=JobType.ONEOFF,
			future=future
			)
   
		self._jobs_queue.put(job)
		return future
		
	def _update_all_markets(self):
		logger.debug("Updating all markets")
  
		markets = self._manifold_api.retrieve_all_data(self._manifold_api.get_markets, max_limit=1000)
		binary_choice_markets = []
		multiple_choice_markets = []
		for market in markets:
			market["lite"] = True
			if market["outcomeType"] == "BINARY":
				binary_choice_markets.append(market)
			elif market["outcomeType"] == "MULTIPLE_CHOICE":
				multiple_choice_markets.append(market)
   
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_binary_choice_markets, data=binary_choice_markets).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_multiple_choice_markets, data=multiple_choice_markets).result()
 
 
  
	# def register_callback(self, job_id, callback):
	# 	'''
	# 	Register a callback function for a specific job ID
	# 	'''
	# 	logger.debug(f"Adding callback {callback.__name__} to job id {job_id}")
	# 	self.callbacks[job_id].append(callback)

	# def unregister_callback(self, job_id, callback):
	# 	'''
	# 	Unregister a specific callback function for a specific job ID
	# 	'''
	# 	if callback in self.callbacks[job_id]:
	# 		logger.debug(f"Removing callback {callback.__name__} from job id {job_id}")
	# 		self.callbacks[job_id].remove(callback)
	# 		# If no more callbacks for this job ID, delete the job ID entry
	# 		if not self.callbacks[job_id]:
	# 			del self.callbacks[job_id]P