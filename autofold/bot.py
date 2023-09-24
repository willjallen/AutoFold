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
	The AutomationBot is responsible for maintaining, adding, removing, starting and stopping automations. 
 
	Attributes:
	-----------
	- ``manifold_api``: The ManifoldAPI instance
	- ``manifold_db``: The ManifoldDatabase instance
	- ``manifold_db_reader``: The ManifoldDatabaseReader instance
	- ``manifold_db_writer``: The ManifoldDatabaseWriter instance
	- ``manifold_subscriber``: The ManifoldSubscriber instance
	''' 
	def __init__(self):
	 
		# Bind Ctrl+C to the stop function
		signal.signal(signal.SIGINT, self.stop) 
  
		# Dynamically set the excepthook
		sys.excepthook = self.automation_bot_excepthook
  
		self._automations = []
		self._automation_futures = []
 
		self._shutdown_event = threading.Event()  
  
		self.manifold_api = None
		self.manifold_db = None
		self.manifold_db_reader = None
		self.manifold_db_writer = None
		self.manifold_subscriber = None
  
	def automation_bot_excepthook(self, exc_type, exc_value, exc_traceback):
		self.stop()
		
		# Call the original excepthook
		sys.__excepthook__(exc_type, exc_value, exc_traceback) 

	def register_automation(self, automation):
		'''
		Registers an automation with the bot.

		:param type automation: Required. The automation class to register. Must be a subclass of the `Automation` class.
		:raises TypeError: if the automation is not a class type.
		:raises ValueError: if the automation is not a subclass of `Automation`.

		Example:

		.. code-block:: python

			bot = ManifoldBot()
			bot.register_automation(MyCustomAutomation)
		''' 
		if not isinstance(automation, Automation):
			logger.error(f"{automation} must be of a subclass of type Automation")
			return

		self._automations.append(automation)

  
 	
	def start(self):
		'''
		Starts the bot's operation.

		Initializes the manifold API, databases, subscriber, and thread executor. Schedules the automations to run in the thread pool.

		:raises RuntimeError: if no automations have been registered.
		''' 

		# if len(self._automations) == 0:
		# 	logger.error("No automations have been registered for the bot. Exiting.")
		# 	self.stop()

		self.manifold_api = ManifoldAPI()

		self.manifold_db = ManifoldDatabase()
		self.manifold_db_reader = ManifoldDatabaseReader(self.manifold_db)
		self.manifold_db_writer = ManifoldDatabaseWriter(self.manifold_db)
		self.manifold_db.create_tables()
  
		self.manifold_subscriber = ManifoldSubscriber(self.manifold_api, self.manifold_db, self.manifold_db_writer)
  
		self._executor = ThreadPoolExecutor(thread_name_prefix="BOT", max_workers=20) 
	
		# # Wait for all threads to come alive
		# threads = {
		# 	'manifold_api': self.manifold_api,
		# 	'manifold_db_writer': self.manifold_db_writer,
		# 	'manifold_subscriber': self.manifold_subscriber
		# }

		# timeout_counter = 0
		# while True:
		# 	# Using list comprehension to find components that are not alive
		# 	failed_threads = [name for name, thread in threads.items() if not thread.is_alive()]
			
		# 	if not failed_threads:
		# 		break
			
		# 	if timeout_counter >= 5:
		# 		self.stop()
		# 		raise RuntimeError(f"Failed to start {failed_threads}.")
				
		# 	time.sleep(1)
		# 	timeout_counter += 1
  
		# Schedule automations to run in the thread pool

		for automation in self._automations:
			logger.debug("Registering automation {automation}")
			automation._register(self)
			self._automation_futures.append(self._executor.submit(self._run_automation, automation))
 	
  
		# Loop to check for the stop condition
		while not self._shutdown_event.is_set():
			time.sleep(1)  # Sleep for 1 second

	def _run_automation(self, automation):
		logger.debug("Running automation {automation}")
     
		try:
			automation.start()
		except Exception as e:
			logger.exception("An error occurred in automation: ", e)
			self.stop()

	def stop(self, *args):
		'''
		Stops the bot's operation.

		Shuts down the API, stops all running automations, and shuts down the thread pool and subscriber.
		''' 
 		# API must be shut down first
		if self.manifold_api:
			self.manifold_api.shutdown()

		for automation in self._automations:
			automation.stop()
  
		if self._executor:
			self._executor.shutdown(wait=False)
  
		# Subscriber
		if self.manifold_subscriber:
			self.manifold_subscriber.shutdown()

		# Database 
		if self.manifold_db_writer:
			self.manifold_db_writer.shutdown()  
  
		self._shutdown_event.set() 


	def get_id(self):
		# Set bot id
		self.me = self.manifold_api.get_me().result()
		self.id = self.me["id"]
