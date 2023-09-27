import time
from loguru import logger
from tinydb import where
from autofold.automation import Automation
from autofold.bot import AutomationBot


class BetAutomation(Automation):
	def __init__(self, db_name):
		super().__init__(db_name)
		
	
	def start(self):
		self.running = True
		logger.info("Running the automation")
		'''
			In this example:
				- Find the top 10 unresolved binary choice markets with the highest daily volume
				- Find the user with the highest profit percent position of the 10 markets
				- Find their most recent bet and the market it was in
				- Make a bet in the direction of their last bet in the market
				- Subscribe to the user position in the market and do what they do
				Includes:
				- Persistence between automation executions

			
			NOTE: This is just an example to demonstrate how to use this system. There are a lot of problems/edge cases with this. 
   				  A real automation might be much more sophisticated. You will probably lose mana with this automation!!!
		'''
  
		# Automation startup
		init_status = self.db.search(where('init').exists())
		if not init_status:
			logger.info("Automation is not initialized. Initializing now.") 
			self.init_automation()
		else:
			logger.info("Automation has already been initialized.") 
		   
			# Get the ids for our stuff from the db 
			self.best_position_db_id = self.db.get(where('best_position').exists()).doc_id
			self.best_position_shares_db_id = self.db.get(where('best_position_shares').exists()).doc_id
			
			best_position = self.db.get(doc_id=self.best_position_db_id)["best_position"]
			
			logger.info(f"Subscribing to future bets of user {best_position['userName']} in market {best_position['contractId']} with polling time {60} seconds")
			self.manifold_subscriber.subscribe_to_market_positions(marketId=best_position["contractId"],
															   userId=best_position["userId"],
															   polling_time=60,
															   callback=self.track_position) 
   
		# You can add extra logic here to repeat the automation every hour or whatever
		while not self.running:
			# ... logic
			time.sleep(60 * 60)
	
	def stop(self):
		self.running = False
		logger.info("Shutdown method called. Automation has been halted.") 
		
	def init_automation(self):
		logger.info("Initializing the automation.") 

		# clear db
		self.db.truncate() 
		logger.debug("Database truncated.") 

		# Update the manifold database with all markets
		logger.info("Updating the manifold database with all markets. (This may take a while)") 
		# self.manifold_subscriber.update_all_markets()

		# Find top 10 binary choice markets with highest volume 
		logger.debug("Finding top 10 unresolved markets with highest 24hr volume")
		markets = \
			self.manifold_db_reader.execute_query(
				"""
				SELECT 
					id,
					volume24Hours,
					question,
					url
				FROM 
					binary_choice_markets
				WHERE
					isResolved = FALSE
				ORDER BY 
					volume24Hours DESC
				LIMIT 10;
				""")
		if not markets:
			logger.error("Failed to fetch top 10 binary choice markets.")
		else:
			logger.success(f"Found top 10 markets by 24 hr volume") 
			logger.debug(f"Markets: {markets}")

		# Save them to local db
		self.markets_db_id = self.db.insert({"markets": markets}) 
		logger.debug(f"Saved markets to db with id: {self.markets_db_id}") 
		
		# Update the manifold database with all the positions (contractMetrics) associated with these markets
		logger.info("Fetching positions for each of the top 10 markets")
		for market in markets:
			logger.debug(f"Fetching positions for market {market['id']}")
			self.manifold_subscriber.update_market_positions(marketId=market["id"])
		   
		# Extract market ids
		market_ids = [market["id"] for market in markets]
		
		# Find the highest profit percent position
		logger.debug("Finding best position (highest profit percent) from top 10 markets.")
		best_position = \
			self.manifold_db_reader.execute_query(
				"""
				SELECT 
					contractId,
					userId,
					userUsername,
					userName,
					profitPercent
				FROM 
					contract_metrics
				WHERE 
					contractId IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				ORDER BY 
					profitPercent DESC
				LIMIT 1;
				""", market_ids)[0]
	  
		if not best_position:
			logger.error("Failed to fetch best position.")
		else:
			logger.success(f"Found best position") 
			logger.debug(f"Best position: {best_position}")

		# Save it to the db
		self.best_position_db_id = self.db.insert({"best_position": best_position})
		logger.debug(f"Saved best position to db with id: {self.best_position_db_id}") 
 
		
		# Find the YES/NO shares for this position
		logger.debug("Finding the YES/NO shares for the best position")
		best_position_shares = \
			self.manifold_db_reader.execute_query(
				"""
				SELECT 
					outcome,
					numberOfShares
				FROM 
					contract_metrics_totalShares
				WHERE 
					userId = ? AND contractId = ?
				ORDER BY 
					id DESC
				LIMIT 2;  -- Since there are only two outcomes, YES and NO
				""", (best_position["userId"], best_position["contractId"]))

		if not best_position_shares:
			logger.error("Failed to find YES/NO shares for best position.")
		else:
			logger.info(f"Found YES/NO shares for best position: {best_position_shares}") 
	
	 
		# Save it to the db
		self.best_position_shares_db_id = self.db.insert({"best_position_shares": best_position_shares})
		logger.debug(f"Saved best position YES/NO shares to db with id: {self.best_position_shares_db_id}")
	   
		# Update the bets from the user with the best position
		logger.info(f"Fetching bets for user {best_position['userName']}")
		self.manifold_subscriber.update_bets(userId=best_position["userId"], contractId=best_position["contractId"])
		
		# Find the most recent bet from the user with the best position
		logger.debug(f"Finding most recent bet for user {best_position['userId']}")
		recent_bet = \
			self.manifold_db_reader.execute_query(
				"""
				SELECT 
					id,
					userId,
					contractId,
					amount,
					outcome,
					createdTime
				FROM 
					bets
				WHERE 
					userId = ? AND contractId = ?
				ORDER BY 
					createdTime DESC
				LIMIT 1;
				""", (best_position["userId"], best_position["contractId"]))[0] 

		if not recent_bet:
			logger.error(f"Failed to fetch most recent bet from user {best_position['userId']} ")
		else:
			logger.info(f"Found most recent bet for user {best_position['userName']}")

		# Save the recent bet to the db
		self.recent_bet_db_id = self.db.insert({"recent_bet": recent_bet})
		logger.debug(f"Saved most recent bet to db with id: {self.recent_bet_db_id}")
		
			
		
		# Make a bet in this direction
		# NOTE: From the API docs:
		# "A non-refundable transaction fee of M0.25 will be levied on any bet, sell, or limit order placed through the API, or by any account marked as a bot."
		# NOTE: The manifold_api returns future objects for each request. You can block and wait for them to finish by calling .result() on them.
		print(f"self.manifold_api.make_bet(amount=10, contractId={recent_bet['contractId']}, outcome={recent_bet['outcome']}).result()")
		
		# NOTE: Manifold uses 'contractId' and 'marketId' interchangably. 
		# 'marketId' is used when referring directly to a market
		# 'contractId' is used _within_ bets or positions to refer to the market it is in
		# :(
		
		# Subscribe to any future changes in position
		logger.info(f"Subscribing to future bets of user {best_position['userName']} in market {recent_bet['contractId']} with polling time {60} seconds")
		self.manifold_subscriber.subscribe_to_market_positions(marketId=recent_bet["contractId"],
															   userId=recent_bet["userId"],
															   polling_time=60,
															   callback=self.track_position)
		
		# Done!
		self.db.insert({'init': True}) 

	# This will execute every 60 seconds(or polling_time) after the position from the user in the specified market have been updated into the manifold db
	def track_position(self):
		# Retrieve the best position and recent bet data from the local db
		best_position = self.db.get(doc_id=self.best_position_db_id)["best_position"]
		best_position_shares = self.db.get(doc_id=self.best_position_shares_db_id)["best_position_shares"]
		# Fetch the latest shares (YES and NO) from the nested contract_metrics_totalShares
		latest_shares = \
			self.manifold_db_reader.execute_query(
				"""
				SELECT 
					outcome,
					numberOfShares
				FROM 
					contract_metrics_totalShares
				WHERE 
					userId = ? AND contractId = ?
				ORDER BY 
					id DESC
				LIMIT 2;  -- Since there are only two outcomes, YES and NO
				""", (best_position["userId"], best_position["contractId"]))
		
		# Do what they do if their position changes from what we have
		# Convert shares list to dictionary
		latest_shares_dict = {item['outcome']: item['numberOfShares'] for item in latest_shares}
		best_position_shares_dict = {item['outcome']: item['numberOfShares'] for item in best_position_shares}

		# 1. Check for new positions
		for outcome, shares in latest_shares_dict.items():
			if outcome not in best_position_shares_dict:
				logger.info(f"New position taken: {outcome} with {shares} shares.")
				# Place a bet for the new position
				# self.manifold_api.make_bet(amount=shares, contractId=best_position["contractId"], outcome=outcome)  # you can add limitProb, expiresAt, etc. if needed

		# 2. Check for sold positions
		for outcome, shares in best_position_shares_dict.items():
			if outcome not in latest_shares_dict:
				logger.info(f"Entire position sold: {outcome} with {shares} shares.")
				# Sell the shares for the sold position
				# self.manifold_api.sell_shares(marketId=best_position["contractId"], outcome=outcome, shares=shares)

		# 3. Check for buy/sell actions on existing positions
		for outcome, shares in latest_shares_dict.items():
			if outcome in best_position_shares_dict:
				difference = shares - best_position_shares_dict[outcome]
				if difference > 0:
					logger.info(f"Bought {difference} shares of {outcome}.")
					# Place a bet for the bought shares
					self.manifold_api.make_bet(amount=difference, contractId=best_position["contractId"], outcome=outcome)
				elif difference < 0:
					logger.info(f"Sold {-difference} shares of {outcome}.")
					# Sell the sold shares
					# self.manifold_api.sell_shares(marketId=best_position["contractId"], outcome=outcome, shares=-difference)

def main():

	# Set up logging
	log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

	# Configure the logger
	logger.add("logs/{time:YYYY-MM-DD}.log", rotation="1 day", format=log_format, level="TRACE", enqueue=True) 
	logger.info("Logging has been set up!") 

	# Init automation
	example_automation = BetAutomation(db_name='example_automation')

	# Init bot
	automation_bot = AutomationBot()

	# Register it
	automation_bot.register_automation(example_automation, "example_automation")

	# Run the bot
	automation_bot.start()

	# time.sleep(2)
	input("Press any key to exit")
 
	automation_bot.stop()


main() 
  