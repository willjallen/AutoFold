import json
import os
import time
from loguru import logger
import requests
from datetime import datetime
import threading
from queue import Queue, Full
from concurrent.futures import ThreadPoolExecutor, Future


DEV_DOMAIN = 'https://dev.manifold.markets' 
MAIN_DOMAIN = 'https://manifold.markets'

# Load API key from the environment variable
api_key = os.environ.get("MANIFOLD_API_KEY")
if api_key is None:
    logger.error("Environment variable MANIFOLD_API_KEY is not set")
	


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

READS_PER_SECOND = 100
BETS_PER_MINUTE = 5

class TokenBucket:
	def __init__(self, tokens, fill_rate):
		""" Tokens is the total tokens in the bucket. fill_rate is the rate in tokens/second."""
		self.capacity = tokens
		self._tokens = tokens
		self.fill_rate = fill_rate
		self.timestamp = time.time()

	def consume(self, tokens):
		""" Consume tokens from the bucket. Returns 0 if there are sufficient tokens, otherwise the expected time to wait in seconds."""
		if tokens > self._tokens:
			return (tokens - self._tokens) / self.fill_rate
		self._tokens -= tokens
		return 0

	def refill(self):
		""" Add new tokens to the bucket."""
		now = time.time()
		delta = self.fill_rate * (now - self.timestamp)
		self._tokens = min(self.capacity, self._tokens + delta)
		self.timestamp = now

class ManifoldAPI():
	def __init__(self, dev_mode=False):
		'''
        Initialize ManifoldAPI.

        :param bool dev_mode: Optional. Whether to enable developer mode. Default is False.
        
        .. note::
			- API key must be provided as an environment variable as MANIFOLD_API_KEY
            - Token buckets for reads and bets are initialized.
            - Request queues for reads and bets are set up.
            - Thread pool executor is set up.
            - Separate threads for processing read and bet queues are started.
        ''' 
		logger.debug("Initializing ManifoldAPI")
		self.dev_mode = dev_mode
		self._reads_bucket = TokenBucket(100, READS_PER_SECOND) 
		self._bets_bucket = TokenBucket(10, BETS_PER_MINUTE/60.0) 
		self._bets_queue = Queue(maxsize=1000)
		self._reads_queue = Queue(maxsize=1000) 
  
		self._executor = ThreadPoolExecutor(thread_name_prefix="MF_API", max_workers=5)
	
		self.running = True
  
		# Start processing the request queues in a separate thread
		self._read_thread = threading.Thread(target=self._process_read_queue, daemon=True)
		self._read_thread.start()

		# Start processing the bets queues in a separate thread
		self._bet_thread = threading.Thread(target=self._process_bet_queue, daemon=True)
		self._bet_thread.start()

	def is_alive(self):
		"""
		Checks if all relevant threads and the executor are running.

		:return: True if all relevant threads and the executor are running, False otherwise.
		:rtype: bool
		"""
		# Check if the ThreadPoolExecutor is running (this is a bit of a workaround)
		executor_alive = not self._executor._shutdown

		# Check if individual threads are alive
		read_thread_alive = self._read_thread.is_alive()
		bet_thread_alive = self._bet_thread.is_alive()

		# Combine these checks to return the overall status
		return executor_alive and read_thread_alive and bet_thread_alive

	def shutdown(self):
		'''
        Shutdown the ManifoldAPI.

        .. note::
            - Stops all running threads.
            - Shuts down the thread pool _executor.
            - Sets all pending Futures to exceptions stating "API is shutting down".
            
        :return: None
        :rtype: None
        ''' 
		logger.info("Shutting down ManifoldAPI") 
		self.running = False
		self._read_thread.join()
		self._bet_thread.join()
		self._executor.shutdown(wait=False)
  
		# Set futures to exceptions
		while not self._reads_queue.empty():
			_, _, _, future = self._reads_queue.get()
			future.set_exception(Exception("API is shutting down"))
		while not self._bets_queue.empty():
			_, _, _, future = self._bets_queue.get()
			future.set_exception(Exception("API is shutting down")) 

	def _make_request(self, endpoint, method="GET", params=None, future=None):
		headers = {"Authorization": f"Key {api_key}"}
		log_data = {
				"timestamp": datetime.now().isoformat(),
				"endpoint": endpoint,
				"method": method,
				"params": params
			}
		logger.debug(f"API call: {json.dumps(log_data)}")

		if not self.dev_mode:
			endpoint = MAIN_DOMAIN + endpoint
		else:
			endpoint = DEV_DOMAIN + endpoint

		try:
			if method == "GET":
				response = requests.get(endpoint, headers=headers, params=params, timeout=5)
			elif method == "POST":
				response = requests.post(endpoint, headers=headers, json=params, timeout=5)

			if response.status_code != 200:
				logger.error(f"Error in API call: {response.status_code}, {response.json}")
				if future:
					future.set_exception(Exception(f"HTTP Error: {response.status_code}"))
			else:
				if future:
					future.set_result(response.json())
		except Exception as e:
			logger.error(f"Exception occurred while making a request: {e}") 
			if future:
				future.set_exception(e)
				
	def _process_read_queue(self):
		while self.running:

			self._reads_bucket.refill() 

			# Process read requests
			while not self._reads_queue.empty():
				wait_time = self._reads_bucket.consume(1)
				if wait_time > 0:
					time.sleep(wait_time)
				endpoint, method, params, future = self._reads_queue.get()
				self._executor.submit(self._make_request, endpoint, method, params, future)

			time.sleep(0.1)  # Sleep 100 milliseconds if the queue is empty 


	def _process_bet_queue(self):
		while self.running:
      
			self._bets_bucket.refill() 

			# Process bet requests if we can
			while not self._bets_queue.empty():
				wait_time = self._bets_bucket.consume(1)
				if wait_time > 0:
					time.sleep(wait_time)
				endpoint, method, params, future = self._bets_queue.get()
				self._executor.submit(self._make_request, endpoint, method, params, future)
    
			time.sleep(0.1)  # Sleep 100 milliseconds if the queue is empty 
    

	def retrieve_all_data(self, api_call_func, max_limit=1000, **api_params):
		'''
		Iteratively retrieves all available data from an API endpoint that supports pagination via a `before` parameter.

		:param Callable api_call_func: 
			Required. A function that makes the API call and returns a Future object.
		:param int max_limit: 
			Optional. The maximum number of items to request in a single API call. Default is 1000.
		:param api_params: 
			Optional. Additional parameters to pass to the API call function. Must be passed as keyword arguments.
		:type api_params: dict
		:return: 
			A list containing all retrieved items.
		:rtype: list

		.. note::

			This function is blocking.

		**Example**

		.. code-block:: python

			retrieve_all_data(api_function, max_limit=200, param1="value1", param2="value2")

		'''
  
		logger.debug(f"Starting retrieve_all_data") 
		all_data = []
		last_item_id = None
		has_more_data = True
		
		while has_more_data:
			if not self.running:
				raise Exception("retrieve_all_data interrupted by thread exit")
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
				logger.error(f"An error occurred during retrieve_all_data: {e}")
				has_more_data = False

		return all_data   

	def get_user_by_username(self, username):
		'''
		GET /v0/user/[username]

		Gets a user by their username. Remember that usernames may change.

		:param str username: Required. The username of the user.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
	 
		future = Future()
	
		self._reads_queue.put((f"/api/v0/user/{username}", "GET", None, future))
		return future

	def get_user_by_id(self, user_id):
		'''
		GET /v0/user/by-id/[id]

		Gets a user by their unique ID. Many other API endpoints return this as the user_id.

		:param str user_id: Required. The ID of the user.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
	 
		future = Future()
		
		self._reads_queue.put((f"/api/v0/user/by-id/{user_id}", "GET", None, future))
		return future

	def get_me(self):
		'''
		GET /v0/me

		Returns the authenticated user.

		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''

		future = Future()
  
		self._reads_queue.put((f"/api/v0/me", "GET", None, future))
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
		
	# 	self._reads_queue.put(("/api/v0/groups", "GET", None, future))
	# 	return future

	def get_group_by_slug(self, group_slug):
		'''
		GET /v0/group/[slug]

		Gets a group by its slug.
		
		Note: group is singular in the URL.

		:param str group_slug: Required. The slug of the group.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
	 
		future = Future()
		
		self._reads_queue.put((f"/api/v0/group/{group_slug}", "GET", None, future))
		return future

	def get_group_by_id(self, group_id):
		'''
		GET /v0/group/by-id/[id]

		Gets a group by its unique ID.

		:param str group_id: Required. The id of the group.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
	 
		future = Future()
		
		self._reads_queue.put((f"/api/v0/group/by-id/{group_id}", "GET", None, future))
		return future
 
	def get_group_markets_by_id(self, group_id):
		'''
		GET /v0/group/by-id/[id]/markets

		Gets a group's markets by its unique ID.

		:param str group_id: Required. The id of the group.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
		future = Future()
		
		self._reads_queue.put((f"/api/v0/group/by-id/{group_id}/markets", "GET", None, future))
		return future

	def get_markets(self, limit=500, before=None):
	 
		'''
		GET /v0/markets

		Lists all markets, ordered by creation date descending.

		:param int limit: Optional. How many markets to return. The maximum is 1000 and the default is 500.
		:param str before: Optional. The ID of the market before which the list will start.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
		future = Future()
		
		params = {"limit": limit}
		if before:
			params["before"] = before
		self._reads_queue.put((f"/api/v0/markets", "GET", params, future))
		return future
	
	def get_market_by_id(self, market_id):
		'''
		GET /v0/market/[marketId]

		Gets information about a single market by ID. Includes answers, but not bets and comments. Use /bets or /comments with a market ID to retrieve bets or comments.

		:param str market_id: Required. The ID of the market.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
	 
		future = Future()
		
		self._reads_queue.put((f"/api/v0/market/{market_id}", "GET", None, future))
		return future

	def get_market_positions(self, market_id, order='profit', top=None, bottom=None, user_id=None):
		'''
		.. note:: 
  			This API endpoint will break for markets with > 4650 positions. Setting either the top or bottom parameters is required to mitigate a 500 server error.
			See https://github.com/manifoldmarkets/manifold/issues/2031 

		GET /v0/market/[marketId]/positions

		Get positions information about a single market.

		:param str market_id: Required. The ID of the market.
		:param str order: Optional. The field to order results by. Default is 'profit'. Options are 'shares' or 'profit'.
		:param int top: Optional. The number of top positions (ordered by 'order') to return. Default is None.
		:param int bottom: Optional. The number of bottom positions (ordered by 'order') to return. Default is None.
		:param str userId: Optional. The user ID to query by. Default is None. If provided, only the positions for this user will be returned.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
		future = Future()
		
		params = {"order": order}
		if top:
			params["top"] = top
		if bottom:
			params["bottom"] = bottom
		if user_id:
			params["userId"] = user_id
   
		self._reads_queue.put((f"/api/v0/market/{market_id}/positions", "GET", params, future))
		return future

	def get_market_by_slug(self, market_slug):
		'''
		GET /v0/slug/[market_slug]
	
		Gets information about a single market by slug (the portion of the URL path after the username).

		:param str market_slug: Required. The slug of the market.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
		future = Future()
		self._reads_queue.put((f"/api/v0/slug/{market_slug}", "GET", None, future))
		return future


	def search_markets(self, terms=None):
		'''
		GET /v0/search-markets

		Search markets by keywords, limited to 100 results.

		:param str terms: Optional. A space-separated list of keywords to search for.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''

		future = Future()
		params = {}
		if terms:
			params["terms"] = terms
   
		self._reads_queue.put((f"/api/v0/search-markets", "GET", params, future))
		return future	

	def get_users(self, limit=None, before=None):
		'''
		GET /v0/users

		Lists all users, ordered by creation date descending.

		:param int limit: Optional. How many users to return. The maximum is 1000 and the default is 500.
		:param str before: Optional. The ID of the user before which the list will start. For example, if you ask for the most recent 10 users, and then perform a second query for 10 more users with before=[the id of the 10th user], you will get users 11 through 20.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future
		'''

		future = Future()
		params = {}
		if limit:
			params["limit"] = limit 
		if before:
			params["before"] = before
   
		self._reads_queue.put((f"/api/v0/users", "GET", params, future))
		return future	

	def make_bet(self, amount, contract_id, outcome, limit_prob=None, expires_at=None):
		'''
		POST /v0/bet

		Places a new bet on behalf of the authorized user.

		:param float amount:
			Required. The amount to bet, in mana, before fees.
		:param str contract_id:
			Required. The ID of the contract (market) to bet on. 
		:param str outcome:
			Required. The outcome to bet on. The outcome type is market-specific:
			
			- For binary markets: "YES" or "NO"
			- For free-response markets: ID of the free response answer
			- For numeric markets: String representing the target bucket
			
		:param float limit_prob:
			Optional. A number between 0.01 and 0.99 inclusive representing the limit probability for your bet. 
			
			- For example, if the current market probability is 50%:
				- A M$10 bet on "YES" with ``limitProb=0.4`` would not be filled until the market probability moves down to 40%.
				- A M$100 bet on "YES" with ``limitProb=0.6`` would fill partially or completely depending on current market conditions.
				
			Any remaining unfilled bet will remain as an open offer for future matches.
			
		:param int expires_at:
			Optional. A Unix timestamp (in milliseconds) at which the limit bet should be automatically canceled.

		:return:
			A Future object representing the eventual result of the API call.

		:rtype: Future

		**Examples**

		.. code-block:: python

			make_bet(100, "contractId123", "YES", limitProb=0.6)
		'''

		future = Future()
		params = {"amount": amount, "contractId": contract_id, "outcome": outcome}
		if limit_prob:
			params["limitProb"] = limit_prob
		if expires_at:
			params["expiresAt"] = expires_at
   
		self._bets_queue.put((f"/api/v0/bet", "POST", params, future))
		return future	

	def cancel_bet(self, bet_id):
		'''
		POST /v0/bet/cancel/[betId]

		Cancels the limit order of a bet with the specified id.

		:param str bet_id: 
			Required. The unique identifier for the bet to be cancelled.
			
		:return:
			A Future object representing the eventual result of the API call.
		:rtype: Future

		.. note:: 
			This action is irreversible.

		**Examples**

		.. code-block:: python

			cancel_bet("betId123")
		'''
		future = Future()
		self._bets_queue.put((f"/api/v0/bet/cancel/{bet_id}", "POST", None, future))
		return future

	def create_market(self, outcome_type, question, description=None, close_time=None, visibility=None, group_id=None, initial_prob=None, min=None, max=None, is_log_scale=None, initial_value=None, answers=None):
		'''
		POST /v0/market

		Creates a new market on behalf of the authorized user.

		:param str outcome_type: Required. The type of outcome for the market.
		:param str question: Required. The main question for the market.
		:param str description: Optional. A detailed description for the market.
		:param int close_time: Optional. Time when the market closes.
		:param str visibility: Optional. The visibility setting for the market.
		:param str group_id: Optional. The group ID associated with the market.
		:param float initial_prob: Optional. The initial probability for the market outcome.
		:param float min: Optional. The minimum value for a numeric market.
		:param float max: Optional. The maximum value for a numeric market.
		:param bool is_log_scale: Optional. Whether the market uses a logarithmic scale.
		:param float initial_value: Optional. The initial value for the market.
		:param list[str] answers: Optional. Possible answers for a free-response market.
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future

		**Examples**

		.. code-block:: python

		   create_market("binary", "Will it rain?", description="Weather prediction", closeTime=1633027200, visibility="public")
		'''
		future = Future()
		params = {"outcomeType": outcome_type, "question": question}
		if description: params["description"] = description
		if close_time: params["closeTime"] = close_time
		if visibility: params["visibility"] = visibility
		if group_id: params["groupId"] = group_id
		if initial_prob: params["initialProb"] = initial_prob
		if min: params["min"] = min
		if max: params["max"] = max
		if is_log_scale: params["isLogScale"] = is_log_scale
		if initial_value: params["initialValue"] = initial_value
		if answers: params["answers"] = answers

		self._bets_queue.put((f"/api/v0/market", "POST", params, future))
		return future

	def add_liquidity(self, market_id, amount):
		'''
		POST /v0/market/[marketId]/add-liquidity

		Adds liquidity to a specific market.

		:param str market_id: 
			The ID of the market. This parameter is required.
		:param float amount: 
			The amount of liquidity to be added. This parameter is required.

		:return: 
			A Future object representing the eventual result of the API call.

		:rtype: Future

		**Examples**

		.. code-block:: python

			add_liquidity("marketId123", 500.0)
		'''
		future = Future()
		params = {"amount": amount}
		self._bets_queue.put((f"/api/v0/market/{market_id}/add-liquidity", "POST", params, future))
		return future

	def close_market(self, market_id, close_time=None):
		'''
		POST /v0/market/[marketId]/close
		
		Closes a market on behalf of the authorized user.
		
		:param str market_id: 
			The unique identifier for the market to be closed. This parameter is required.
		:param int close_time: 
			Optional. Milliseconds since the epoch to close the market at. If not provided, the market will be closed immediately. Cannot provide close time in the past.
		:return: 
			A Future object representing the eventual result of the API call.

		:rtype: Future
		
		**Examples**

		.. code-block:: python

			close_market("marketId123")
			close_market("marketId123", closeTime=1672444800000)
		'''
		future = Future()
		params = {}
		if close_time: params["closeTime"] = close_time
		self._bets_queue.put((f"/api/v0/market/{market_id}/close", "POST", params, future))
		return future

	def manage_group_market(self, market_id, group_id, remove=None):
		'''
		POST /v0/market/[marketId]/group

		Add or remove a market to/from a group.

		:param str market_id: Required. The ID of the market.
		:param str group_id: Required. The ID of the group. Must be an admin, moderator, or creator of the group if curated/private. Must be the market creator or trustworthy-ish if the group is public.
		:param bool remove: Optional. Set to true to remove the market from the group.
		
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future

		**Example Usage**

		.. code-block:: python

			manage_group_market("marketId123", "groupId456", remove=True)
		'''
		future = Future()
		params = {"groupId": group_id}
		if remove: params["remove"] = remove
		self._bets_queue.put((f"/api/v0/market/{market_id}/group", "POST", params, future))
		return future

	def resolve_market(self, market_id, outcome, probability_int=None, resolutions=None, value=None):
		'''
		POST /v0/market/[marketId]/resolve

		Resolves a market on behalf of the authorized user.

		:param str market_id: 
			Required. The ID of the market.

		:param str outcome: 
			Required. Outcome varies based on the type of market.
			
			- For binary markets: One of "YES", "NO", "MKT", or "CANCEL".
			- For free response or multiple choice markets: One of "MKT", "CANCEL", or a number indicating the answer index.
			- For numeric markets: One of "CANCEL", or a number indicating the selected numeric bucket ID.

		:param int probability_int: 
			Optional. The probability to use for MKT resolution in binary markets.
			Also, required if `value` is present in numeric markets.

		:param list[dict] resolutions:
			Optional. An array of {answer, pct} objects to use as the weights for resolving in favor of multiple free response options.
			Can only be set with "MKT" outcome. Note that the total weights must add to 100.

		:param int value: 
			Optional. The value that the market resolves to in numeric markets.

		:raises ValueError: 
			If the total weights in `resolutions` do not add up to 100.
			
		**Examples**

		.. code-block:: python

			resolve_market("marketId123", "YES", probabilityInt=80)
			resolve_market("marketId456", "MKT", resolutions=[{"answer": "A", "pct": 40}, {"answer": "B", "pct": 60}])
		'''
		future = Future()
		params = {"outcome": outcome}
		if probability_int: params["probabilityInt"] = probability_int
		if resolutions: params["resolutions"] = resolutions
		if value: params["value"] = value

		self._bets_queue.put((f"/api/v0/market/{market_id}/resolve", "POST", params, future))
		return future

	def sell_shares(self, market_id, outcome=None, shares=None):
		'''
		POST /v0/market/[marketId]/sell

		Sells some quantity of shares in a binary market.

		:param str market_id: The unique identifier for the binary market where shares are being sold. This parameter is required.
		:param str outcome: Optional. Specifies the outcome for which shares are being sold. Can be "YES" or "NO".
		:param float shares: Optional. The amount of shares to sell for the given outcome. If not provided, all shares owned will be sold.
		
		:return: A Future object representing the eventual result of the API call.
		:rtype: Future

		**Examples**

		.. code-block:: python

			sell_shares("marketId123", "YES", 10)
		'''
		future = Future()
		params = {}
		if outcome:
			params["outcome"] = outcome
		if shares:
			params["shares"] = shares
		self._bets_queue.put((f"/api/v0/market/{market_id}/sell", "POST", params, future))
		return future

	def create_comment(self, contract_id, content=None, html=None, markdown=None):
		'''
		POST /v0/comment
		
		Creates a comment in the specified market.

		:param str contract_id:
			Required. The ID of the market to comment on.
		:param content:
			Optional. The comment to post, formatted as TipTap json.
			:conflicted: html, markdown
		:type content: str or None
		:param html:
			Optional. The comment to post, formatted as an HTML string.
			:conflicted: content, markdown
		:type html: str or None
		:param markdown:
			Optional. The comment to post, formatted as a markdown string.
			:conflicted: content, html
		:type markdown: str or None
		:return:
			A Future object representing the eventual result of the API call.
		:rtype: Future
		
		.. note::
		   You should provide either `content`, `html`, or `markdown` but not multiple at the same time. They are mutually exclusive.

		**Examples**

		.. code-block:: python

			create_comment("contractId123", content="some TipTap json content")
			create_comment("contractId123", html="<p>some HTML content</p>")
			create_comment("contractId123", markdown="## some markdown content")
		'''
		future = Future()
		params = {"contractId": contract_id}
		if content:
			params["content"] = content
		elif html:
			params["html"] = html
		elif markdown:
			params["markdown"] = markdown
		self._reads_queue.put((f"/api/v0/comment", "POST", params, future))
		return future

	def get_comments(self, contract_id=None, contract_slug=None):
		'''
		GET /v0/comments
		
		Gets a list of comments for a contract.

		:param str contract_id: Optional. The ID of the contract to read comments for.
			Either an ID or a slug must be specified.
		:param str contract_slug: Optional. The slug of the contract to read comments for.
			Either an ID or a slug must be specified.

		:return: A Future object representing the eventual result of the API call.
		:rtype: Future

		.. note::
		   Either `contractId` or `contractSlug` must be specified.

		**Examples**

		.. code-block:: python

		   get_comments(contractId="someContractId")
		   get_comments(contractSlug="someContractSlug")
		'''
		future = Future()
		params = {}
		if contract_id:
			params["contractId"] = contract_id
		if contract_slug:
			params["contractSlug"] = contract_slug
		self._reads_queue.put((f"/api/v0/comments", "GET", params, future))
		return future

	def get_bets(self, user_id=None, username=None, contract_id=None, contract_slug=None, limit=None, before=None):
		'''
		GET /v0/bets

		Retrieves a list of bets, sorted by their creation date in descending order.

		:param str user_id: 
			Optional. If provided, returns only bets created by the user with this ID.
		:param str username: 
			Optional. If provided, returns only bets created by the user with this username.
		:param str contract_id: 
			Optional. If provided, returns only bets associated with this contract ID.
		:param str contract_slug: 
			Optional. If provided, returns only bets associated with this contract slug.
		:param int limit: 
			Optional. The number of bets to return. Defaults to and maxes out at 1000.
		:param str before: 
			Optional. Specifies the ID of the bet to start the list from, effectively functioning as an offset. 
			For instance, after requesting the 10 most recent bets, supplying the ID of the 10th bet in a new query would yield bets 11 through 20.
			
		:return: 
			A Future object representing the eventual result of the API call.
		:rtype: Future
		'''
		future = Future()
		params = {}
		if user_id:
			params["userId"] = user_id
		if username:
			params["username"] = username
		if contract_id:
			params["contractId"] = contract_id
		if contract_slug:
			params["contractSlug"] = contract_slug
		if limit:
			params["limit"] = limit
		if before:
			params["before"] = before
		self._reads_queue.put((f"/api/v0/bets", "GET", params, future))
		return future

