from abc import ABC, abstractmethod
from tinydb import TinyDB
import threading

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
	def __init__(self, db_name: str=""):
		'''
		Initializer for the automation class.

		:param str db_name: Required. The name of the database file to use, without the extension.
		''' 
		self.db_name = db_name

	def _register(self, automation_bot):
		self.automation_bot = automation_bot
		self.manifold_api = automation_bot.manifold_api
		self.manifold_db_reader = automation_bot.manifold_db_reader
		self.manifold_subscriber = automation_bot.manifold_subscriber
		if self.db_name:
			self.db = TinyDB('dbs/'+self.db_name+'.json')
		
	
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
