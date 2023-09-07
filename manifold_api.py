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

A non-refundable transaction fee of M0.25 will be levied on any bet, sell, or limit order placed through the API, or by any account marked as a bot.
Comments placed through the API will incur a M1 transaction fee.
'''

'''
API interface is most recent with 2023-05-15 on changelog.
'''

REQUESTS_PER_SECOND = 60
BETS_PER_MINUTE = 5

class ManifoldAPI():
	def __init__(self):
		self.bets_queue = Queue(maxsize=1000)
		self.reads_queue = Queue(maxsize=1000) 
		self.log_buffer = []
		self.bet_timestamps = []
  
		self.executor = ThreadPoolExecutor(max_workers=50)
	 
		# Start processing the request queues in a separate thread
		threading.Thread(target=self._process_read_queue, daemon=True).start()

		# Start processing the bets queues in a separate thread
		threading.Thread(target=self._process_bet_queue, daemon=True).start()

	def _log_api_call(self, endpoint, method, params):
		self.log_buffer.append({"timestamp": datetime.now().isoformat(), "endpoint": endpoint, "method": method, "params": params})
		
		if len(self.log_buffer) >= 1:
			with open(log_file, "a") as f:
				for log in self.log_buffer:
					json.dump(log, f)
					f.write('\n')
			self.log_buffer = []

	def _make_request(self, endpoint, method="GET", params=None, future=None):
		headers = {"Authorization": f"Key {api_key}"}
		self._log_api_call(endpoint, method, params)

		try:
			if method == "GET":
				response = requests.get(endpoint, headers=headers, params=params)
			elif method == "POST":
				response = requests.post(endpoint, headers=headers, json=params)

			if response.status_code != 200:
				print(f"Error: {response.status_code}, {response}")
				if future:
					future.set_exception(Exception(f"HTTP Error: {response.status_code}"))
			else:
				if future:
					future.set_result(response.json())
		except Exception as e:
			if future:
				future.set_exception(e)
				
	def _process_read_queue(self):
		while True:
			# Process read requests
			reads_counter = 0
			while reads_counter < REQUESTS_PER_SECOND and not self.reads_queue.empty():
				endpoint, method, params, future = self.reads_queue.get()
				self.executor.submit(self._make_request, endpoint, method, params, future)
				reads_counter += 1
			
			time.sleep(1)

	def _process_bet_queue(self):
		while True:
			bets_counter = 0	
			# Process bet requests if we can
			while len(self.bet_timestamps) < BETS_PER_MINUTE and not self.bets_queue.empty():
				endpoint, method, params, future = self.bets_queue.get()
				self.executor.submit(self._make_request, endpoint, method, params, future)
				bets_counter += 1	
    
			time.sleep(60)

	@staticmethod
	def retrieve_all_data(api_call_func, max_limit=1000, **api_params):
		"""
		Iteratively retrieves all available data from an API endpoint that supports pagination via a `before` parameter.

		:param api_call_func: A function that makes the API call and returns a Future object.
		:param max_limit: The maximum number of items to request in a single API call. Defaults to 1000.
		:param api_params: Additional parameters to pass to the API call function.
		
		:return: A list containing all retrieved items.
  
		Note: This function is blocking.
		"""
		all_data = []
		last_item_id = None
		has_more_data = True
		
		while has_more_data:
			try:
				# Include the 'before' parameter if we have a last_item_id to work with
				if last_item_id:
					api_params['before'] = last_item_id

				# Make the API call
				future_response = api_call_func(limit=max_limit, **api_params)
				response = future_response.result()

				if response:
					all_data.extend(response)
					last_item_id = response[-1]['id']
					has_more_data = len(response) == max_limit
				else:
					has_more_data = False
			except Exception as e:
				print(f"An error occurred: {e}")
				has_more_data = False

		return all_data   

	def get_user_by_username(self, username):
		'''
		GET /v0/user/[username]

		Gets a user by their username. Remember that usernames may change.

		Parameters:
		username: Required. The username of the user.
		'''	
	 
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/{username}", "GET", None, future))
		return future

	def get_user_by_id(self, userId):
		'''
		GET /v0/user/by-id/[id]

		Gets a user by their unique ID. Many other API endpoints return this as the userId.

		Pramaters:
		userId: Required. The id of the user.
		'''	
	 
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/user/by-id/{userId}", "GET", None, future))
		return future

	def get_me(self):
		'''
		GET /v0/me

		Returns the authenticated user.
		'''	

		future = Future()
  
		self.reads_queue.put((f"https://manifold.markets/api/v0/me", "GET", None, future))
		return future

	# Returns 500 error	
	# def get_groups(self):
	# 	'''
	# 	GET /v0/groups

	# 	Gets all groups, in no particular order.

	# 	Parameters:
	# 	availableToUserId: Optional. if specified, only groups that the user can join and groups they've already joined will be returned.
	# 	Requires no authorization.
	# 	'''
	 
	# 	future = Future()
		
	# 	self.reads_queue.put(("https://manifold.markets/api/v0/groups", "GET", None, future))
	# 	return future

	def get_group_by_slug(self, groupSlug):
		'''
		GET /v0/group/[slug]

		Gets a group by its slug.
		
  		Note: group is singular in the URL.
    
		Paramaters:
		groupSlug: Required. The slug of the group.
		'''
	 
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/group/{groupSlug}", "GET", None, future))
		return future

	def get_group_by_id(self, groupId):
		'''
		GET /v0/group/by-id/[id]

		Gets a group by its unique ID.
  
		Parameters:
		groupId: Required. The id of the group.
		'''
	 
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/group/by-id/{groupId}", "GET", None, future))
		return future
 
	def get_group_markets_by_id(self, groupId):
		'''
		GET /v0/group/by-id/[id]/markets

		Gets a group's markets by its unique ID.

		Paramaters:
		groupId: Required. The id of the group.
		'''
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/group/by-id/{groupId}/markets", "GET", None, future))
		return future

	def get_markets(self, limit=500, before=None):
	 
		'''
		GET /v0/markets

		Lists all markets, ordered by creation date descending.

		Parameters:
		limit: Optional. How many markets to return. The maximum is 1000 and the default is 500.
		before: Optional. The ID of the market before which the list will start. For example, if you ask for the most recent 10 markets, and then perform a second query for 10 more markets with before=[the id of the 10th market], you will get markets 11 through 20.
		''' 
		future = Future()
		
		params = {"limit": limit}
		if before:
			params["before"] = before
		self.reads_queue.put(("https://manifold.markets/api/v0/markets", "GET", params, future))
		return future
	
	def get_market_by_id(self, marketId):
		'''
		GET /v0/market/[marketId]

		Gets information about a single market by ID. Includes answers, but not bets and comments. Use /bets or /comments with a market ID to retrieve bets or comments. 

		Paramaters:
		marketId: Required. The id of the market.
		'''
	 
		future = Future()
		
		self.reads_queue.put((f"https://manifold.markets/api/v0/market/{marketId}", "GET", None, future))
		return future

	def get_market_positions(self, order='profit', top=None, bottom=None, userId=None):
		'''
		GET /v0/market/[marketId]/positions
  
		Get positions information about a single market.

		Parameters:
		order: Optional. The field to order results by. Default: profit. Options: shares or profit,
		top: Optional. The number of top positions (ordered by order) to return. Default: null.
		bottom: Optional. The number of bottom positions (ordered by order) to return. Default: null.
		userId: Optional. The user ID to query by. Default: null. If provided, only the positions for this user will be returned.
		'''
		future = Future()
		
		params = {"order": order}
		if top:
			params["top"] = top
		if bottom:
			params["bottom"] = bottom
		if userId:
			params["userId"] = userId
   
		self.reads_queue.put(("https://manifold.markets/api/v0/market/{id}/positions", "GET", params, future))
		return future

	def get_market_by_slug(self, marketSlug):
		'''
		GET /v0/slug/[marketSlug]
  
		Gets information about a single market by slug (the portion of the URL path after the username).

		Paramters:
		marketSlug: Required. The slug of the market.
		'''
		future = Future()
		self.reads_queue.put((f"https://manifold.markets/api/v0/slug/{marketSlug}", "GET", None, future))
		return future


	def search_markets(self, terms=None):
		'''
		GET /v0/search-markets

		Search markets by keywords, limited to 100 results.

		Paramaters:
		terms: Optional. A space-separated list of keywords to search for.
		'''

		future = Future()
		params = {}
		if terms:
			params["terms"] = terms
   
		self.reads_queue.put(("https://manifold.markets/api/v0/search-markets", "GET", params, future))
		return future	

	def get_users(self, limit=None, before=None):
		'''
		GET /v0/users

		Lists all users, ordered by creation date descending.

		Parameters:
		limit: Optional. How many users to return. The maximum is 1000 and the default is 500.
		before: Optional. The ID of the user before which the list will start. For example, if you ask for the most recent 10 users, and then perform a second query for 10 more users with before=[the id of the 10th user], you will get users 11 through 20.
		'''

		future = Future()
		params = {}
		if limit:
			params["limit"] = limit 
		if before:
			params["before"] = before
   
		self.reads_queue.put(("https://manifold.markets/api/v0/users", "GET", params, future))
		return future	

	def make_bet(self, amount, contractId, outcome, limitProb=None, expiresAt=None):
		'''
		POST /v0/bet

		Places a new bet on behalf of the authorized user.

		Parameters:
		amount: Required. The amount to bet, in mana, before fees.
		contractId: Required. The ID of the contract (market) to bet on.
		outcome: Required. The outcome to bet on. For binary markets, this is YES or NO. For free response markets, this is the ID of the free response answer. For numeric markets, this is a string representing the target bucket, and an additional value parameter is required which is a number representing the target value. (Bet on numeric markets at your own peril.)
		limitProb: Optional. A number between 0.01 and 0.99 inclusive representing the limit probability for your bet (i.e. 1% to 99% — multiply by 100 for the probability percentage). The bet will execute immediately in the direction of outcome, but not beyond this specified limit. If not all the bet is filled, the bet will remain as an open offer that can later be matched against an opposite direction bet.
		For example, if the current market probability is 50%:
		A M$10 bet on YES with limitProb=0.4 would not be filled until the market probability moves down to 40% and someone bets M$15 of NO to match your bet odds.
		A M$100 bet on YES with limitProb=0.6 would fill partially or completely depending on current unfilled limit bets and the AMM's liquidity. Any remaining portion of the bet not filled would remain to be matched against in the future.
		An unfilled limit order bet can be cancelled using the cancel API.
		expiresAt: Optional. A Unix timestamp (in milliseconds) at which the limit bet should be automatically canceled. 
		''' 

		future = Future()
		params = {"amount": amount, "contractId": contractId, "outcome": outcome}
		if limitProb:
			params["limitProb"] = limitProb
		if expiresAt:
			params["expiresAt"] = expiresAt
   
		self.bets_queue.put(("https://manifold.markets/api/v0/bet", "POST", params, future))
		return future	

	def cancel_bet(self, betId):
		'''
		POST /v0/bet/cancel/[betId]

		Cancels the limit order of a bet with the specified id.

		Parameters:
		betId: Required. The unique identifier for the bet to be cancelled.

		Note: This action is irreversible.
		'''
		future = Future()
		self.bets_queue.put((f"https://manifold.markets/api/v0/bet/cancel/{betId}", "POST", None, future))
		return future

	def create_market(self, outcomeType, question, description=None, closeTime=None, visibility=None, groupId=None, initialProb=None, min=None, max=None, isLogScale=None, initialValue=None, answers=None):
		'''
		POST /v0/market

		Creates a new market on behalf of the authorized user.

		Parameters:
		outcomeType: Required. The type of outcome for the market.
		question: Required. The main question for the market.
		description: Optional. A detailed description for the market.
		closeTime: Optional. Time when the market closes.
		visibility: Optional. The visibility setting for the market.
		groupId: Optional. The group ID associated with the market.
		initialProb: Optional. The initial probability for the market outcome.
		min: Optional. The minimum value for a numeric market.
		max: Optional. The maximum value for a numeric market.
		isLogScale: Optional. Whether the market uses a logarithmic scale.
		initialValue: Optional. The initial value for the market.
		answers: Optional. Possible answers for a free response market.
		'''
		future = Future()
		params = {"outcomeType": outcomeType, "question": question}
		if description: params["description"] = description
		if closeTime: params["closeTime"] = closeTime
		if visibility: params["visibility"] = visibility
		if groupId: params["groupId"] = groupId
		if initialProb: params["initialProb"] = initialProb
		if min: params["min"] = min
		if max: params["max"] = max
		if isLogScale: params["isLogScale"] = isLogScale
		if initialValue: params["initialValue"] = initialValue
		if answers: params["answers"] = answers

		self.bets_queue.put(("https://manifold.markets/api/v0/market", "POST", params, future))
		return future

	def add_liquidity(self, marketId, amount):
		'''
		POST /v0/market/[marketId]/add-liquidity

		Adds liquidity to a specific market.

		Parameters:
		marketId: Required. The id of the market.
		amount: Required. The amount of liquidity to be added.
		'''
		future = Future()
		params = {"amount": amount}
		self.bets_queue.put((f"https://manifold.markets/api/v0/market/{marketId}/add-liquidity", "POST", params, future))
		return future

	def close_market(self, marketId, closeTime=None):
		'''
		POST /v0/market/[marketId]/close

		Closes a market on behalf of the authorized user.
  
		Parameters:
		marketId: Required. The unique identifier for the market to be closed.
		closeTime: Optional. Milliseconds since the epoch to close the market at. If not provided, the market will be closed immediately. Cannot provide close time in the past.
		'''
		future = Future()
		params = {}
		if closeTime: params["closeTime"] = closeTime
		self.bets_queue.put((f"https://manifold.markets/api/v0/market/{marketId}/close", "POST", params, future))
		return future

	def manage_group_market(self, marketId, groupId, remove=None):
		'''
		POST /v0/market/[marketId]/group

		Add or remove a market to/from a group.

		marketId: Required. The id of the market.
		groupId: Required. The id of the group. Must be admin/moderator/creator of group if curated/private. Must be market creator or trustworthyish if group is public.
		remove: Optional. Set to true to remove the market from the group. 
		'''
		future = Future()
		params = {"groupId": groupId}
		if remove: params["remove"] = remove
		self.bets_queue.put((f"https://manifold.markets/api/v0/market/{marketId}/group", "POST", params, future))
		return future

	def resolve_market(self, marketId, outcome, probabilityInt=None, resolutions=None, value=None):
		'''
		POST /v0/market/[marketId]/resolve

		Resolves a market on behalf of the authorized user.
  
		Parameters:
		marketId: Required. The id of the market.
  
		For binary markets:
		outcome: Required. One of YES, NO, MKT, or CANCEL.
		probabilityInt: Optional. The probability to use for MKT resolution.

		For free response or multiple choice markets:
		outcome: Required. One of MKT, CANCEL, or a number indicating the answer index.
		resolutions: An array of { answer, pct } objects to use as the weights for resolving in favor of multiple free response options. Can only be set with MKT outcome. Note that the total weights must add to 100.

		For numeric markets:
		outcome: Required. One of CANCEL, or a number indicating the selected numeric bucket ID.
		value: The value that the market resolves to.
		probabilityInt: Required if value is present. Should be equal to
		If log scale: log10(value - min + 1) / log10(max - min + 1)
		Otherwise: (value - min) / (max - min) 
		'''
		future = Future()
		params = {"outcome": outcome}
		if probabilityInt: params["probabilityInt"] = probabilityInt
		if resolutions: params["resolutions"] = resolutions
		if value: params["value"] = value

		self.bets_queue.put((f"https://manifold.markets/api/v0/market/{marketId}/resolve", "POST", params, future))
		return future


	def cancel_bet(self, betId):
		'''
		POST /v0/bet/cancel/[betId]

		Cancel the limit order of a bet with the specified id.
  
		Parameters:
		id: required. The id of the bet.

		Note: This action is irreversible. 
		'''
		future = Future()
		self.bets_queue.put((f"https://manifold.markets/api/v0/bet/cancel/{betId}", "POST", None, future))
		return future

	def sell_shares(self, marketId, outcome=None, shares=None):
		'''
		POST /v0/market/[marketId]/sell

		Sells some quantity of shares in a binary market.
  
		Parameters:
		marketId: required. The unique identifier for the binary market where shares are being sold.
		outcome: Optional. One of YES, or NO. If you leave it off, and you only own one kind of shares, you will sell that kind of shares. 
		shares: Optional. The amount of shares to sell of the outcome given above. If not provided, all the shares you own will be sold.
		'''
		future = Future()
		params = {}
		if outcome:
			params["outcome"] = outcome
		if shares:
			params["shares"] = shares
		self.bets_queue.put((f"https://manifold.markets/api/v0/market/{marketId}/sell", "POST", params, future))
		return future

	def create_comment(self, contractId, content=None, html=None, markdown=None):
		'''
		POST /v0/comment

		Creates a comment in the specified market.
  
		Paramaters:
		contractId: Required. The id of the market to comment on.
		content: The comment to post, formatted as TipTap json, OR
		html: The comment to post, formatted as an HTML string, OR
		markdown: The comment to post, formatted as a markdown string. 
		'''
		future = Future()
		params = {"contractId": contractId}
		if content:
			params["content"] = content
		elif html:
			params["html"] = html
		elif markdown:
			params["markdown"] = markdown
		self.reads_queue.put((f"https://manifold.markets/api/v0/comment", "POST", params, future))
		return future

	def get_comments(self, contractId=None, contractSlug=None):
		'''
		GET /v0/comments

		Gets a list of comments for a contract.
  
		Parameters:
		contractId: Optional. Which contract to read comments for. Either an id or slug must be specified.
		contractSlug: Optional. 
		'''
		future = Future()
		params = {}
		if contractId:
			params["contractId"] = contractId
		if contractSlug:
			params["contractSlug"] = contractSlug
		self.reads_queue.put((f"https://manifold.markets/api/v0/comments", "GET", params, future))
		return future

	def get_bets(self, userId=None, username=None, contractId=None, contractSlug=None, limit=None, before=None):
		'''
		GET /v0/bets

		Gets a list of bets, ordered by creation date descending.
  
		Parameters:
		userId: Optional. If set, the response will include only bets created by this user.
		username: Optional. If set, the response will include only bets created by this user.
		contractId: Optional. If set, the response will only include bets on this contract.
		contractSlug: Optional. If set, the response will only include bets on this contract.
		limit: Optional. How many bets to return. The maximum and the default are 1000.
		before: Optional. The ID of the bet before which the list will start. For example, if you ask for the most recent 10 bets, and then perform a second query for 10 more bets with before=[the id of the 10th bet], you will get bets 11 through 20. 
		'''
		future = Future()
		params = {}
		if userId:
			params["userId"] = userId
		if username:
			params["username"] = username
		if contractId:
			params["contractId"] = contractId
		if contractSlug:
			params["contractSlug"] = contractSlug
		if limit:
			params["limit"] = limit
		if before:
			params["before"] = before
		self.reads_queue.put((f"https://manifold.markets/api/v0/bets", "GET", params, future))
		return future

