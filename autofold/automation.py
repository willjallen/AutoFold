from abc import ABC, abstractmethod
from tinydb import TinyDB
import os

class Automation(ABC):
	'''
	.. warning::

		Automations MUST be registered with the bot for the object attributes to be set. This must be done before you run the automation.

	.. note::

		All child classes of automation are provided a local tinydb for non-volatile storage if needed.
		Note that tinydb is NOT threadsafe; proper access safety should be used when accessing data between automations.
		Feel free to use your own storage medium as you see fit.

	Attributes:
	-----------
	- ``automation_bot``: The ManifoldBot instance.
	- ``manifold_api``: The ManifoldAPI instance extracted from automation_bot.
	- ``manifold_db_reader``: The ManifoldDatabaseReader instance extracted from automation_bot.
	- ``manifold_subscriber``: The ManifoldSubscriber instance extracted from automation_bot.
	- ``db``: The TinyDB instance for this automation.
	''' 
	def __init__(self, tiny_db_path: str):
		'''
		Initializer for the automation class.

		:param str tiny_db_path: Required. The path to the desired tinydb file to use. Should be a .json file.
		''' 
		self.tiny_db_path = tiny_db_path
  
		# Ensure the directory exists
		dir_name = os.path.dirname(self.tiny_db_path)
		if dir_name and not os.path.exists(dir_name):
			os.makedirs(dir_name) 

	def _register(self, automation_bot):
		self.automation_bot = automation_bot
		self.manifold_api = automation_bot.manifold_api
		self.manifold_db_reader = automation_bot.manifold_db_reader
		self.manifold_subscriber = automation_bot.manifold_subscriber
		self.db = TinyDB(self.tiny_db_path)
		
	
	@abstractmethod
	def start(self, *args, **kwargs):
		'''
		Abstract method to start the automation.

		.. note::
			This method must be implemented in subclasses.

		:param args: Additional positional arguments.
		:param kwargs: Additional keyword arguments.
		'''
		pass
	
	@abstractmethod
	def stop(self, *args, **kwargs):
		'''
		Abstract method to stop the automation.

		.. note::
			This method must be implemented in subclasses.

		:param args: Additional positional arguments.
		:param kwargs: Additional keyword arguments.
		'''
		pass
