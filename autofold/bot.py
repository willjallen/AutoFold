from concurrent.futures import ThreadPoolExecutor
from loguru import logger
import sys
import signal
import threading
import time
from autofold.automation import Automation
from autofold.api import ManifoldAPI
from autofold.database import ManifoldDatabase
from autofold.database import ManifoldDatabaseWriter
from autofold.database import ManifoldDatabaseReader
from autofold.subscriber import ManifoldSubscriber



class AutomationBot:
	'''
	The AutomationBot is responsible for starting, stopping and maintaining threads and connections to the manifold API, manifold database and manifold subscriber.
 	Additionally, AutomationBot is reponsible for maintaining, adding, removing, starting and stopping automations. 

	:param bool dev_api_endpoint: Optional. 
 		Whether to use the dev.manifold.markets endpoint. Useful for testing. Requires an API key for dev.manifold.markets. Default is False.
 
	Attributes:
	-----------
	- ``dev_api_endpoint``: Whether to use the dev.manifold.markets endpoint
	- ``manifold_api``: The ManifoldAPI instance
	- ``manifold_db``: The ManifoldDatabase instance
	- ``manifold_db_reader``: The ManifoldDatabaseReader instance
	- ``manifold_db_writer``: The ManifoldDatabaseWriter instance
	- ``manifold_subscriber``: The ManifoldSubscriber instance
	''' 
	def __init__(self, dev_api_endpoint=False):
	
		self.dev_api_endpoint = dev_api_endpoint
  
		self._started = False
  
		self._automations = []
		self._automation_futures = []
 
		self._shutdown_event = threading.Event()  
  
		self.manifold_api = None
		self.manifold_db = None
		self.manifold_db_reader = None
		self.manifold_db_writer = None
		self.manifold_subscriber = None

	def register_automation(self, automation_obj, automation_name, run_on_bot_start=True):
		'''
		Registers an automation with the bot.

		:param Strategy automation_obj: Required. The automation class to register. Must be a subclass of the `Automation` class.
		:param str automation_name: Required. The name of the automation.
		:param bool run_on_bot_start: Optional. Whether the automation should be automatically run when the bot first starts. Default True.
		:raises TypeError: if the automation is not a class type.
		:raises ValueError: if the automation is not a subclass of `Automation`.

		Example:

		.. code-block:: python

			bot = ManifoldBot()
			bot.register_automation(MyCustomAutomation)
		''' 
		if not isinstance(automation_obj, Automation):
			logger.error(f"{automation_obj} must be of a subclass of type Automation")
			return

		self._automations.append({'object': automation_obj, 
								  'name': automation_name,
								  'registered': False,
								  'shouldRun': run_on_bot_start,
							   	  'running': False,
             					  'finished': False})

  
 	
	def start(self):
		self.thread = threading.Thread(target=self._start, daemon=True)
		self.thread.start()
  
	def _start(self):
		'''
		Starts the bot's operation.

		Initializes the manifold API, databases, subscriber, and thread executor. Schedules the automations to run in the thread pool.

		:raises RuntimeError: if no automations have been registered.
		''' 

		self.manifold_api = ManifoldAPI(dev_mode=self.dev_api_endpoint)

		self.manifold_db = ManifoldDatabase()
		self.manifold_db_reader = ManifoldDatabaseReader(self.manifold_db)
		self.manifold_db_writer = ManifoldDatabaseWriter(self.manifold_db)
		self.manifold_db.create_tables()

		self.manifold_subscriber = ManifoldSubscriber(self.manifold_api, self.manifold_db, self.manifold_db_writer)

		self._executor = ThreadPoolExecutor(thread_name_prefix="BOT_AUTOMATION_POOL", max_workers=20) 

		self.started = True
	
		# Loop to check for the stop condition
		while not self._shutdown_event.is_set():
			# Check for unregistered automations and/or automations that should be executed
			for automation in self._automations:
				if not automation['registered']:
					logger.debug("Registering automation {automation}")
					automation['object']._register(self)
					automation['registered'] = True
				if not automation['running'] and automation['shouldRun']:
					automation['running'] = True
					automation['shouldRun'] = False
					self._automation_futures.append(self._executor.submit(self._run_automation, automation))
	
			time.sleep(1)  # Sleep for 1 second
	

	'''
		Runs an automation.

		:param str automation_name: Required. The name of the automation.
		:raises RuntimeError: if the automation has not been registered with the bot.
		:raises RuntimeError: if the automation is not found.
  
 	'''
	def run_automation(self, automation_name):
		for automation in self._automations:
			if automation['name'] == automation_name:
				if automation['registered'] != True:
					raise RuntimeError(f"Automation {automation_name} has not been registered.")
				if automation['running']:
					logger.error(f"Automation {automation_name} is already running.")
					return
				self._automation_futures.append(self._executor.submit(self._run_automation, automation))
				return

		raise RuntimeError(f"Automation {automation_name} not found.")

	def _run_automation(self, automation):
		logger.debug(f"Running automation {automation['name']}")
	 
		try:
			automation['object'].start()
		except Exception as e:
			logger.error(f"Caught exception in automation: {automation['name']}", e)
			self.stop()
		
		# When the automation finishes
		automation['running'] = False
		automation['finished'] = True


	def stop(self, *args):
		'''
		Stops the bot's operation.

		Shuts down the API, stops all running automations, and shuts down the thread pool and subscriber.
		''' 
 		# API must be shut down first
		if self.manifold_api:
			self.manifold_api.shutdown()

		for automation in self._automations:
			automation['object'].stop()
  
		if self._executor:
			self._executor.shutdown(wait=False)
  
		# Subscriber
		if self.manifold_subscriber:
			self.manifold_subscriber.shutdown()

		# Database 
		if self.manifold_db_writer:
			self.manifold_db_writer.shutdown()  
  
		self._shutdown_event.set() 
  
		self.thread.join()
  


	def get_id(self):
		# Set bot id
		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
