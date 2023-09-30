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


'''
TODO:

This whole thing has a litany of edge cases and problems when there are multiple strategies involved.
As it stands now it *works*, just not as robust as I would like.

Thoughts:
All callbacks associated with job should be fired. 
Right now it's possible for a subscriber to miss a callback if two automations are subscribed to the same endpoint

Replace APScheduler with custom scheduler
- Job objects should be stored with function signature for proper sharing
- Job run interval should be min(polling_times) (coalesce jobs)
- Polling times per subscriber should be respected
	- Add additional parameter callback_soonest_update
		- If automation A subscribes to endpoint at interval 30 seconds and automation B subscribes at 60 seconds, should automation B wait for the full 60 seconds or update as soon as A is finished

  

job = {
	"function": "subscribe_to_user_info",   // The function that is responsible for the task
	"params": { /*params*/ },                // Parameters needed for the function
	"lastUpdate": 34234552,                  // A timestamp of the last update
	"callbacks": [                           // An array of callback functions
		{
			"function": "foo",
			"polling_time": 60
			"next_call_time": 3232432
			// any other properties you may want to include for the callback
		}
	],
	"update_interval": min(polling_times)
	"status": "pending",                     // The current status of the job (e.g., pending, in-progress, complete, failed)
	"attempts": 0,                           // The number of attempts made to execute the job
	"maxAttempts": 5,                        // The maximum number of retries before marking the job as failed
	"priority": 1,                           // Priority level (lower number means higher priority)
	"timeout": 3000,                         // Timeout in milliseconds
	"createdOn": 162344554,                  // A timestamp of when the job was created
	"nextExecution": null,                   // When the job is set to be executed next
	"errorLog": [],                          // Any errors or exceptions caught during execution
	"result": null,                          // The result returned by the function, if any
}

Callbacks are always gaurenteed to have updated information upon their firing

Loop through jobs
Check if they need to update (min polling times of callbacks)
Loop through callbacks
Fire callback

'''


class Job:
	def __init__(self, action: str, function: Callable, params: Any,
				 job_type: str, callbacks: list[dict], future: Union[None, Future] = None):
		self.action = action  # "add" or "remove"
		self.status = "pending" # The current status of the job (pending, executing) 
		self.function = function  # Function responsible for the task
		self.params = params  # Parameters needed for the function
		self.job_type = job_type  # "oneoff" or "interval"
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
		self.next_execution_time = time.time() + self.update_interval # Set next execution time

		if self.job_type == "oneoff":
			self.future.set_result("done")	
   
		self.status = "pending"

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
		self._executor = ThreadPoolExecutor(thread_name_prefix="MF_SUBSCRIBER_EXECUTOR", max_workers=5)
		self._jobs_queue = Queue(maxsize=1000)
 
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
				if job.action == "add":
					logger.debug(f"Adding job {job}")
					self._add_job(job)
				elif job.action == "remove":
					logger.debug(f"Removing job {job}")
					self._remove_job(job)

			# Execute jobs
			current_time = time.time()
			for job in self._jobs:
				# Check if it's time for the job to be executed
				if job.next_execution_time <= current_time and job.status != "executing":
					job.status = "executing"
					logger.debug(f"Executing job {job}")
					if job.job_type == "oneoff":
						future = self._executor.submit(job.execute)
						# Remove one-off jobs after execution
						self._jobs.remove(job)
					elif job.job_type == "interval":
						future = self._executor.submit(job.execute)
						# Update next execution time
						job.next_execution_time = current_time + job.update_interval

				# Check callbacks
				for callback in job.callbacks:
					if callback["next_call_time"] <= current_time and job.status != "executing":
						logger.debug(f"Firing callback {callback} from job {job}")
						# Execute the callback
						callback["function"]()
						# Update next call time
						callback["next_call_time"] = current_time + callback["polling_time"]
      
			time.sleep(0.1)

	def _add_job(self, new_job):
	 
		# Coalesce into existing job
		for job in self._jobs:
			if job.function == new_job.function and job.params == new_job.params:
				# One-off job
				if new_job.job_type == "oneoff":
					# Set the next execution time to now
					job.next_execution_time = time.time()
					# Set the future
					job.future = new_job.future
					# Done
					return
   
				# Interval job
				if new_job.job_type == "interval":
					# Is there a callback?
					if len(new_job.callbacks) != 0:
						# Yes, add the new callback
						new_callback = new_job.callbacks[0]
						job.add_callback(new_callback)
						# Done
						return
  
		# New job
		if new_job.job_type == "oneoff":
			# Set next execution time to now
			new_job.next_execution_time = time.time()
  
		elif new_job.job_type == "interval":
			# Set next execution time
			new_job.next_execution_time = time.time() + new_job.update_interval
			# Set callback next call time
			new_job.callbacks[0]["next_call_time"] = time.time() + new_job.callbacks[0]["polling_time"]

		self._jobs.append(new_job)

	def _remove_job(self, job_to_remove):
		# Remove the job by comparing function and parameters
		self._jobs = [job for job in self._jobs if not (job.function == job_to_remove.function and job.params == job_to_remove.params)]


 
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
	# 			del self.callbacks[job_id]

	def subscribe_to_user_info(self, userId, polling_time=60, callback=None):
		'''
		Continuously retrieves the (LiteUser) profile of a user by their userid and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		'''
		logger.debug(f"Subscribing to profile of user {userId} with polling time {polling_time} seconds")
  
		job = Job(action="add", 
				function=self._update_user_info,
			   	params=(userId),
				callbacks=[                           
				{
					"function": callback,
					"polling_time": polling_time,
				}
			])
  
		self._jobs_queue.put(job)

	def unsubscribe_to_user_info(self, userId):
		'''
		Unsubscribes to the profile of a user and removes all associated callbacks.	
		'''
	 
		logger.debug(f"Unsubscribing to profile of user {userId}")
	 
		job = Job(action="remove", 
				function=self._update_user_info,
			   	params=(userId))

		self._jobs_queue.put(job)

	def update_user_info(self, userId):
		'''
		Retrieves the (LiteUser) profile of a user by their userId and updates the manifold database with the fetched data.

		:param userId: The Id of the user to be fetched.
  
		'''
		logger.debug(f"Updating profile of user {userId}")
	 
		future = Future()	
  
		job = {
			"action": "add",
			"function": self._update_user_info,   
			"params": (userId),                
			"job_type": "oneoff",
			"future": future,
		} 	 
   
		self._jobs_queue.put(job)
		return future
 
	def _update_user_info(self, userId, future):
		logger.debug(f"Updating profile for user {userId}")
		user = self._manifold_api.get_user_by_id(userId=userId).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_users, data=[user]).result()
  
		if future:
			future.set_result("done")
	
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
  
		job = Job(action="add", 
		  function=self._update_bets,
		  params=(userId, username, contractId, contractSlug),
		  job_type="interval",
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])

		self._jobs_queue.put(job)

	def unsubscribe_to_bets(self, userId=None, username=None, contractId=None, contractSlug=None, polling_time=60, callback=None):
		job = Job(action="remove",
		  function=self._update_bets,
		  params=(userId, username, contractId, contractSlug))

		self._jobs_queue.put(job)

	def update_bets(self, userId=None, username=None, contractId=None, contractSlug=None):
		'''
		Retrieves the bets of a user by their userId and updates the manifold database with the fetched data.

		:param userId: Optional. If set, the response will include only bets created by this user.
		:param username: Optional. If set, the response will include only bets created by this user.
		:param contractId: Optional. If set, the response will only include bets on this contract.
		:param contractSlug: Optional. If set, the response will only include bets on this contract.
  
		NOTE: This function is blocking.
		'''

		future = Future()	
  
		job = Job(action="add",
		  function=self._update_bets,
		  params=(userId, username, contractId, contractSlug),
		  job_type="oneoff",
		  future=future)

   
		self._jobs_queue.put(job)
		return future
		
	def _update_bets(self, userId=None, username=None, contractId=None, contractSlug=None):
		logger.debug(f"Updating bets with userId={userId}, username={username}, contractId={contractId} and contractSlug={contractSlug}")
  
		bets = self._manifold_api.retrieve_all_data(api_call_func=self.manifold_api.get_bets, max_limit=1000, params={"userId": userId, "username": username, "contractId": contractId, "contractSlug": contractSlug})
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_bets, data=bets).result()

	def subscribe_to_market_positions(self, marketId, userId=None, polling_time=60, callback=None):
		''' 
		NOTE: Due to https://github.com/manifoldmarkets/manifold/issues/2031 this function will only subscribe to the top 4000 positions by order.

  		Continuously retrieves the positions of a market by its marketId and updates the manifold database with it. Optionally tracks a single user's positions.
	
		:param marketId: The id of the market
		:param userId: Optional. Tracks the positions of a specific user in a market.
		:param polling_time: The number of seconds between updates. Default is 60 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
  
		job = Job(action="add",
		  function=self._update_market_positions,
		  params=(marketId, userId),
		  job_type="interval",
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])
  
		self._jobs_queue.put(job)

	def unsubscribe_to_market_positions(self, marketId, userId=None):
		job = Job(action="remove",
		  function=self._update_market_positions,
		  params=(marketId, userId))

		self._jobs_queue.put(job)
  
	def update_market_positions(self, marketId, userId=None):
		'''
		NOTE: Due to https://github.com/manifoldmarkets/manifold/issues/2031 this function will only retrieve to the top 4000 positions by order.

		Retrieves the positions of a market by its marketId, and optionally for a specific user, then updates the manifold database with the fetched data.

		:param marketId: The ID of the market whose positions are to be fetched.
		:param userId: Optional. If provided, fetches positions only for this user in the specified market.
  
		NOTE: This function is blocking.
		'''
		future = Future()	
  
		job = Job(action="add",
		  function=self._update_market_positions,
		  params=(marketId, userId),
		  job_type="oneoff",
		  future=future)
		self._jobs_queue.put(job)
		return future

	def _update_market_positions(self, marketId, userId=None):
  
		logger.debug(f"Updating market positios for marketId={marketId} and userId={userId}")
  
		contract_metrics = self._manifold_api.get_market_positions(marketId=marketId, order='profit', top=2000, userId=userId).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_contract_metrics, data=contract_metrics).result()

	def subscribe_to_all_users(self, polling_time=3600, callback=None):
		''' 
		Continuously retrieves the (LiteUser) profile of all users and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
		'''
	
		logger.debug(f"Subscribing to profiles of all users with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")

		job = Job(action="add",
		  function=self._update_all_users,
		  params=(),
		  job_type="interval",
		  callbacks=[
			  {
				  "function": callback,
				  "polling_time": polling_time,
			  }
		  ])

		self._jobs_queue.put(job) 

	def unsubscribe_to_all_users(self):
		job = Job(action="remove",
		  function=self._update_all_users,
		  params=()) 

		self._jobs_queue.put(job)
  
	def update_all_users(self):
		'''
		Retrieves the (LiteUser) profile of all users and updates the manifold database with the fetched data.
		NOTE: This function can take roughly 5 seconds to complete given the current API speeds.
		''' 
		future = Future()	
  
		job = Job(action="add",
		  function=self._update_all_users,
		  params=(),
		  job_type="oneoff",
		  future=future)
   
		self._jobs_queue.put(job)
		return future
  
	def _update_all_users(self):
		logger.debug(f"Updating profiles of all users")
  
		users = self._manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_users, data=users).result()

	def subscribe_to_all_markets(self, polling_time=3600, callback=None):
		''' 
  		Continuously retrieves all (LiteMarket) markets and updates the manifold database with it.
		
		:param polling_time: The number of seconds between updates. Default is 3600 seconds.
		:param callback: Optional. The function to be called when the job finishes.
		:returns: job. The apscheduler job object.
  
		NOTE: Currently only supports binary choice and multiple choice markets
		'''
  
		logger.debug(f"Subscribing to all markets with polling time {polling_time} seconds and callback {callback.__name__ if callback else None}")
 
		job = Job(action="add",
			function=self._update_all_markets,
			params=(),
			job_type="interval",
			callbacks=[
				{
					"function": callback,
					"polling_time": polling_time	
				}
			])

		self._jobs_queue.put(job) 

	def unsubscribe_to_all_markets(self):
		job = Job(action="remove",
		  function=self._update_all_markets,
		  params=()) 

		self._jobs_queue.put(job)

	def update_all_markets(self):
		future = Future()	
  
		job = Job(action="add",
			function=self._update_all_markets,
			params=(),
			job_type="oneoff",
			future=future
			)
   
		self._jobs_queue.put(job)
		return future
		
	def _update_all_markets(self):
		'''
		Retrieves all (LiteMarket) markets and updates the manifold database with the fetched data.
  
		NOTE: Currently only supports binary choice and multiple choice markets 
		NOTE: This function can take roughly 45 seconds to complete given the current API speeds.
		''' 
	
		logger.debug("Updating all markets")
  
		markets = self._manifold_api.retrieve_all_data(self._manifold_api.get_markets, max_limit=1000)
		binary_choice_markets = []
		multiple_choice_markets = []
		for market in markets:
			if market["outcomeType"] == "BINARY":
				binary_choice_markets.append(market)
			elif market["outcomeType"] == "MULTIPLE_CHOICE":
				multiple_choice_markets.append(market)
   
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_binary_choice_markets, data=binary_choice_markets).result()
		self._manifold_db_writer.queue_write_operation(function=self._manifold_db.upsert_multiple_choice_markets, data=multiple_choice_markets).result()
  