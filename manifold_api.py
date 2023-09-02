import json
import time
import requests
from datetime import datetime
import threading
from queue import Queue, Full
from concurrent.futures import ThreadPoolExecutor, Future


# Load API key from the local .secrets file
with open(".secrets", "r") as f:
	secrets = json.load(f)
	api_key = secrets["manifold-api-key"]
	
log_file = "api_call_logs.json"




'''
From docs:
Keep your bets to less than 10 per minute, amortized (transient spikes of over 10/min are okay).
Keep your reads to less than 100 per second.
'''
REQUESTS_PER_SECOND = 100
BETS_PER_MINUTE = 5

class ManifoldAPI():
	def __init__(self):
		self.bets_queue = Queue(maxsize=1000)
		self.reads_queue = Queue(maxsize=1000) 
		self.log_buffer = []
		self.bet_timestamps = []
  
		self.executor = ThreadPoolExecutor(max_workers=50)
	 
		# Start processing the request queues in a separate thread
		threading.Thread(target=self.process_queues, daemon=True).start()

	def log_api_call(self, endpoint):
		self.log_buffer.append({"timestamp": datetime.now().isoformat(), "endpoint": endpoint})
		
		if len(self.log_buffer) >= 1000:
			with open(log_file, "a") as f:
				for log in self.log_buffer:
					json.dump(log, f)
					f.write('\n')
			self.log_buffer = []
   
	def make_request(self, endpoint, method="GET", params=None, future=None):
		headers = {"Authorization": f"Key {api_key}"}
		self.log_api_call(endpoint)

		try:
			if method == "GET":
				response = requests.get(endpoint, headers=headers, params=params)
			elif method == "POST":
				response = requests.post(endpoint, headers=headers, json=params)

			if response.status_code != 200:
				print(f"Error: {response.status_code}, {response.json()}")
				if future:
					future.set_exception(Exception(f"HTTP Error: {response.status_code}"))
			else:
				if future:
					future.set_result(response.json())
		except Exception as e:
			if future:
				future.set_exception(e)
				
	def process_queues(self):
		while True:
			current_time = time.time()
			
			self.bet_timestamps = [t for t in self.bet_timestamps if current_time - t < 60]

			# Process bet requests if we can
			while len(self.bet_timestamps) < BETS_PER_MINUTE and not self.bets_queue.empty():
				endpoint, method, params, future = self.bets_queue.get()
				self.executor.submit(self.make_request, endpoint, method, params, future)
				self.bet_timestamps.append(current_time)

			# Process read requests
			reads_counter = 0
			while reads_counter < REQUESTS_PER_SECOND and not self.reads_queue.empty():
				endpoint, method, params, future = self.reads_queue.get()
				self.executor.submit(self.make_request, endpoint, method, params, future)
				reads_counter += 1
			
			time.sleep(1)



	'''
	GET /v0/user/[username]
	Gets a user by their username. Remember that usernames may change.
	Requires no authorization.
	'''	
	def get_user_by_username(self, username):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/{username}", "GET", None, future))
		return future

	'''
	GET /v0/user/by-id/[id]
	Gets a user by their unique ID. Many other API endpoints return this as the userId.
	Requires no authorization
	'''	
	def get_user_by_id(self, id):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/by-id/{id}", "GET", None, future))
		return future

	'''
	GET /v0/me
	Returns the authenticated user.
	'''	
	#TODO

 
	'''
	GET /v0/groups
	Gets all groups, in no particular order.

	Parameters:
	availableToUserId: Optional. if specified, only groups that the user can join and groups they've already joined will be returned.
	Requires no authorization.
	'''
	def get_groups(self):
		future = Future()
		
		self.reads_queue.put(("https://manifold.markets/api/v0/groups", "GET", None, future))
		return future

	'''
	GET /v0/group/[slug]
	Gets a group by its slug.

	Requires no authorization. Note: group is singular in the URL.
	'''
	def get_group_by_slug(self, slug):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/group/{slug}", "GET", None, future))
		return future

	'''
	GET /v0/group/by-id/[id]
	Gets a group by its unique ID.

	Requires no authorization. Note: group is singular in the URL.
	'''
	# TODO
 
	'''
	GET /v0/markets
	Lists all markets, ordered by creation date descending.

	Parameters:

	limit: Optional. How many markets to return. The maximum is 1000 and the default is 500.
	before: Optional. The ID of the market before which the list will start. For example, if you ask for the most recent 10 markets, and then perform a second query for 10 more markets with before=[the id of the 10th market], you will get markets 11 through 20.
	''' 
	def get_markets(self, limit=500, before=None):
		future = Future()
		
		params = {"limit": limit}
		if before:
			params["before"] = before
		self.reads_queue.put(("https://manifold.markets/api/v0/markets", "GET", params, future))
		return future
	
	'''
	GET /v0/market/[marketId]
	Gets information about a single market by ID. Includes answers, but not bets and comments. 
 	Use /bets or /comments with a market ID to retrieve bets or comments.

	Requires no authorization.
	'''
	def get_market_by_id(self, id):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/market/{id}", "GET", None, future))
		return future

	# Fetch a user's assets by username
	def get_user_assets_by_username(self, username):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/{username}/assets", "GET", None, future))
		return future

	# Fetch a user's predictions by username
	def get_user_predictions_by_username(self, username):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/{username}/predictions", "GET", None, future))
		return future

	# Fetch comments for a specific market
	def get_market_comments_by_id(self, id):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/market/{id}/comments", "GET", None, future))
		return future

	# Fetch trades for a specific market
	def get_market_trades_by_id(self, id):
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/market/{id}/trades", "GET", None, future))
		return future
