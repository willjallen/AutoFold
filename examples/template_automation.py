import time
from loguru import logger
from tinydb import where
from autofold.automation import Automation
from autofold.bot import AutomationBot


class TemplateAutomation(Automation):
	def __init__(self, tiny_db_path):
		super().__init__(tiny_db_path)
		
	
	def start(self):
		self.running = True
		logger.info("Running the automation")
		
		# Automation startup
		init_status = self.db.search(where('init').exists())
		if not init_status:
			logger.info("Automation is not initialized. Initializing now.") 
			self.init_automation()
		else:
			logger.info("Automation has already been initialized.") 
		  	# ... logic
   
		# You can add extra logic here to repeat the automation every hour or whatever
		next_run_timestamp = time.time() + 60 * 60
		while self.running:
			if time.time() >= next_run_timestamp:
				next_run_timestamp = time.time() + 60 * 60
				# ... logic
				pass

			# Check the self.running condition frequently, otherwise you will have trouble exiting the program
			time.sleep(1)
	
	def stop(self):
		self.running = False
		logger.info("Shutdown method called. Automation has been halted.") 
		
	def init_automation(self):
		logger.info("Initializing the automation.") 
	
		# ... logic
 	
		# Done!
		self.db.insert({'init': True}) 

def main():


	# Set up logging
	log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

	# Configure the logger
	logger.add("logs/{time:YYYY-MM-DD}.log", rotation="1 day", format=log_format, level="TRACE", enqueue=True) 
	logger.info("Logging has been set up!") 

	# Init automation
	example_automation = TemplateAutomation(tiny_db_path='dbs/template_automation.json')

	# Init bot
	automation_bot = AutomationBot(manifold_db_path="dbs/manifold_database.db")

	# Register it
	automation_bot.register_automation(example_automation, "template_automation")

	# Run the bot
	# Add try-except for CTRL+C, otherwise you'll get dangling threads when exiting this way
	try:	
		automation_bot.start()

		input("Press any key to exit")
	except KeyboardInterrupt:
		automation_bot.stop()
		return
	
	automation_bot.stop()

if __name__ == "__main__":
	main() 
  