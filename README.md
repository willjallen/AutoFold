# ManifoldBot

Hassle-free and easy to use bot for [Manifold.markets](https://manifold.markets)

## Features:

- **ManifoldAPI**: 
  - Asynchronous future-based API interface with full coverage
  - Token-bucket rate limiting 
- **ManifoldDatabse**: 
  - Local sqlite3 database for offline processing of manifold data
  - Simple interface for reading & executing queries
  - Writing is handled via subscribers
- **ManifoldSubscriber**: 
  - Subscriber interface to automatically retrieve and update offline information with granularity
  - Allows registering callbacks to updates 

## Setup

1. Clone this repository
2. (Recommended) create a virtual environment, then activate it
   ```
   python -m venv .venv
   ```
3. Install requirements.txt:
   ```
   pip install -r requirements.txt
   ```
4. Create a .secrets file in the project's root directory and add your API key as a json object:
   ```
   {
       "manifold-api-key": "xxx"
   }
   ```

## Usage

### Strategies

You can easily add your own functionality to this bot by creating a new strategy class in `strategies/your_strategy.py` and adding it to the `config.toml`. An example is provided for you in `strategies/example_strategy.py`. 

A skeleton template is available in `strategies/template_strategy.py`

An instance of `Bot`, `ManifoldAPI`, `ManifoldDatabaseReader` and `ManifoldSubscriber` is provided to each strategy. 

When the `Bot` is started, it will call the `run()` function for each strategy. Likewise, when the program gets a shutdown signal it will call the `shutdown()` function for each strategy.

### Manifold API

The `ManifoldAPI` class provides a seamless interface to interact with the Manifold.markets API. Below is a quick rundown of its functionality and how to utilize it.

#### Key Features:
- **Token Bucket Rate Limiting**: The class implements a token-bucket-based rate limiting mechanism to ensure compliance with the Manifold.markets API rate limits.
- **Asynchronous Execution**: Operations that make API calls are executed asynchronously using Python's `ThreadPoolExecutor`.
- **Future-based Interface**: The methods in the class return `Future` objects, allowing you to easily handle the results or exceptions once the API call is complete.

#### Using the API:

1. Initialization:
   Create an instance of the `ManifoldAPI` class.
   ```python
   api = ManifoldAPI()
   ```
2. Making API Calls:
    Use the provided methods to make API calls. For example, to get a user by their username:
    ```python
    future_result = api.get_user_by_username("sampleUsername")
    user_data = future_result.result()
    ```
3. Retrieving All Data:
    If you need to fetch all available data from a paginated API endpoint, use the retrieve_all_data method:
    ```python
	users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
    ```
    Note that this function returns all of the data instead of a `Future` object and is blocking.

### Manifold Database
- There are two classes you should use directly: `ManifoldDatabaseReader` and `ManifoldDatabaseWriter`.
- **You should only need to use `ManifoldDatabaseReader` as inserting/updating new data is handled for you in the `ManifoldSubscriber` class.**

#### Using the Manifold Database:
1. Initialization:
   Create an instance of the `ManifoldDatabase` class.
   ```python
   manifold_db = ManifoldDatabase()
   ```
2. Create the tables:
   ```python
    manifold_db.create_tables()
   ```
3. Create an instance of the `ManifoldDatabaseReader` and `ManifoldDatabaseWriter` classes:
    ```python
    manifold_db_reader = ManifoldDatabaseReader(manifold_db)
    manifold_db_writer = ManifoldDatabaseWriter(manifold_db)
    ```
4. Writing information to the database:
    ```python
    users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
    manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, data=users).result()
    ```
5. Reading information from the database
    ```python
    # Find top 10 binary choice markets with highest volume 
    markets = \
        manifold_db_reader.execute_query(
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
    ```

### Manifold Subscriber
- Provides an easy way to schedule fetching specific data from the Manifold API
- Allows registering callbacks for each fetch operation

#### Using the Manifold Subscriber:
1. Initialization:
   Create an instance of the `ManifoldSubscriber` class.
   ```python
   manifold_subscriber = ManifoldSubscriber(manifold_api, manifold_db, manifold_db_writer)
   ```
2. Subscribe to an endpoint:
   ```python
    manifold_subscriber.subscribe_to_bets(username='Joe', polling_time=60, callback=foo)
   ```
3. Do something upon update
    ```python
        def foo():
            ...
    ```


# ManifoldBot Database Schema

## 1. Users

| Column             | Type    | Description                                                    |
| ------------------ | ------- | -------------------------------------------------------------- |
| id                 | TEXT    | User's unique id                                               |
| createdTime        | INTEGER | Timestamp when the user was created (milliseconds since epoch) |
| name               | TEXT    | Display name, may contain spaces                               |
| username           | TEXT    | Username, used in URLs                                         |
| url                | TEXT    | Link to the user's profile                                     |
| bio                | TEXT    | Optional user's biography                                      |
| balance            | REAL    | User's balance                                                 |
| totalDeposits      | REAL    | Total deposits made by the user                                |
| totalPnLCached     | REAL    | Cached Profit/Loss of the user                                 |
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved                              |

## 2. Binary Choice Markets

| Column             | Type    | Description                                                            |
| ------------------ | ------- | ---------------------------------------------------------------------- |
| id                 | TEXT    | Unique identifier for this market                                      |
| closeTime          | INTEGER | Min of creator's chosen date, and resolutionTime                       |
| createdTime        | INTEGER | Timestamp when the market was created (milliseconds since epoch)       |
| creatorId          | TEXT    | Identifier for the market creator                                      |
| creatorName        | TEXT    | Name of the market creator                                             |
| creatorUsername    | TEXT    | Username of the market creator                                         |
| isResolved         | BOOLEAN | Whether the market is resolved or not                                  |
| lastUpdatedTime    | INTEGER | Last update timestamp                                                  |
| mechanism          | TEXT    | Market mechanism (`dpm-2` or `cpmm-1`)                                 |
| outcomeType        | TEXT    | Type of outcome (`BINARY`, `FREE_RESPONSE`, etc.)                      |
| p                  | REAL    | For CPMM markets only, probability constant                            |
| probability        | REAL    | Probability associated with the market                                 |
| question           | TEXT    | Market question                                                        |
| textDescription    | TEXT    | Description of the market                                              |
| totalLiquidity     | REAL    | For CPMM markets, the amount of mana deposited into the liquidity pool |
| url                | TEXT    | URL related to the market                                              |
| volume             | REAL    | Trading volume for the market                                          |
| volume24Hours      | REAL    | Trading volume for the market in the last 24 hours                     |
| pool_NO            | REAL    | Liquidity of the 'NO' pool                                             |
| pool_YES           | REAL    | Liquidity of the 'YES' pool                                            |
| groupSlugs         | TEXT    | Group slugs associated with the market                                 |
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved                                      |
| lite               | INTEGER | Whether the market was retrieved as a LiteMarket                       |

## 3. Multiple Choice Markets

| Column             | Type    | Description                                                            |
| ------------------ | ------- | ---------------------------------------------------------------------- |
| id                 | TEXT    | Unique identifier for the market                                       |
| closeTime          | INTEGER | Min of creator's chosen date, and resolutionTime                       |
| createdTime        | INTEGER | Timestamp when the market was created (milliseconds since epoch)       |
| creatorId          | TEXT    | ID of the creator                                                      |
| creatorName        | TEXT    | Name of the creator                                                    |
| creatorUsername    | TEXT    | Username of the creator                                                |
| isResolved         | BOOLEAN | Whether the market is resolved                                         |
| lastUpdatedTime    | INTEGER | Last update timestamp                                                  |
| mechanism          | TEXT    | Market mechanism (`dpm-2` or `cpmm-1`)                                 |
| outcomeType        | TEXT    | Type of outcome (`BINARY`, `FREE_RESPONSE`, etc.)                      |
| question           | TEXT    | Market question                                                        |
| textDescription    | TEXT    | Description of the market                                              |
| totalLiquidity     | REAL    | For CPMM markets, the amount of mana deposited into the liquidity pool |
| volume             | REAL    | Market volume                                                          |
| volume24Hours      | REAL    | Market volume in the last 24 hours                                     |
| url                | TEXT    | URL related to the market                                              |
| groupSlugs         | TEXT    | Market group slugs                                                     |
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved                                      |
| lite               | INTEGER | Whether the market was retrieved as a LiteMarket flag                  |

### 4. Multiple Choice Market Answers

| Column         | Type    | Description                                                        |
| -------------- | ------- | ------------------------------------------------------------------ |
| id             | INTEGER | Unique identifier for the answer, auto-incremented                 |
| contractId     | TEXT    | Identifier for the associated market contract                      |
| createdTime    | INTEGER | Timestamp when the answer was created                              |
| fsUpdatedTime  | TEXT    | Timestamp of the last update for the answer                        |
| isOther        | INTEGER | Indicator if this is an 'other' option (usually 0 or 1)            |
| answerIndex    | INTEGER | Index or order of this answer in the list                          |
| probability    | REAL    | Probability associated with the answer                             |
| subsidyPool    | REAL    | Subsidy pool amount for this answer                                |
| text           | TEXT    | Textual description or content of the answer                       |
| totalLiquidity | REAL    | Total liquidity associated with this answer                        |
| userId         | TEXT    | Identifier for the user associated with this answer                |
| pool_NO        | REAL    | Liquidity of the 'NO' pool for this answer                         |
| pool_YES       | REAL    | Liquidity of the 'YES' pool for this answer                        |
| FOREIGN KEY    | -       | `contractId` references the `multiple_choice_markets` table's `id` |

## 5. Contract Metrics

| Column             | Type    | Description                       |
| ------------------ | ------- | --------------------------------- |
| contractId         | TEXT    | Contract identifier               |
| hasNoShares        | INTEGER | Whether there are No shares       |
| hasShares          | INTEGER | Whether there are shares          |
| hasYesShares       | INTEGER | Whether there are Yes shares      |
| invested           | REAL    | Amount invested                   |
| loan               | REAL    | Loan amount                       |
| maxSharesOutcome   | TEXT    | Maximum shares outcome            |
| payout             | REAL    | Payout amount                     |
| profit             | REAL    | Profit amount                     |
| profitPercent      | REAL    | Profit percentage                 |
| userId             | TEXT    | User ID                           |
| userUsername       | TEXT    | User username                     |
| userName           | TEXT    | User name                         |
| lastBetTime        | INTEGER | Last bet timestamp                |
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved |

### 6. Contract Metrics From

| Column        | Type    | Description                                                                             |
| ------------- | ------- | --------------------------------------------------------------------------------------- |
| id            | INTEGER | Unique identifier                                                                       |
| contractId    | TEXT    | Contract ID                                                                             |
| userId        | TEXT    | User ID                                                                                 |
| period        | TEXT    | Time period                                                                             |
| value         | REAL    | Value amount                                                                            |
| profit        | REAL    | Profit amount                                                                           |
| invested      | REAL    | Investment amount                                                                       |
| prevValue     | REAL    | Previous value                                                                          |
| profitPercent | REAL    | Profit percentage                                                                       |
| FOREIGN KEY   | -       | `(contractId, userId)` references the `contract_metrics` table's `(contractId, userId)` |

### 7. Contract Metrics TotalShares

| Column         | Type    | Description                                                                             |
| -------------- | ------- | --------------------------------------------------------------------------------------- |
| id             | INTEGER | Unique identifier                                                                       |
| contractId     | TEXT    | Contract ID                                                                             |
| userId         | TEXT    | User ID                                                                                 |
| outcome        | TEXT    | Outcome type                                                                            |
| numberOfShares | REAL    | Number of shares                                                                        |
| FOREIGN KEY    | -       | `(contractId, userId)` references the `contract_metrics` table's `(contractId, userId)` |

## 8. Bets

| Column             | Type    | Description                       |
| ------------------ | ------- | --------------------------------- |
| id                 | TEXT    | Unique identifier for the bet     |
| userId             | TEXT    | User ID                           |
| contractId         | TEXT    | Contract ID                       |
| isFilled           | INTEGER | Whether the bet is filled         |
| amount             | REAL    | Amount of the bet                 |
| probBefore         | REAL    | Probability before the bet        |
| isCancelled        | INTEGER | Whether the bet is cancelled      |
| outcome            | TEXT    | Bet outcome                       |
| shares             | REAL    | Number of shares                  |
| limitProb          | REAL    | Limit probability                 |
| loanAmount         | REAL    | Loan amount                       |
| orderAmount        | REAL    | Order amount                      |
| probAfter          | REAL    | Probability after the bet         |
| createdTime        | INTEGER | Bet creation timestamp            |
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved |

### 9. Bet Fees

| Column             | Type    | Description                                |
| ------------------ | ------- | ------------------------------------------ |
| id                 | INTEGER | Unique identifier                          |
| betId              | TEXT    | Bet ID                                     |
| userId             | TEXT    | User ID                                    |
| fee                | REAL    | Fee amount                                 |
| retrievedTimestamp | INTEGER | Data retrieval timestamp                   |
| FOREIGN KEY        | -       | `betId` references the `bets` table's `id` |

### 10. Bet Fills

| Column       | Type    | Description                                |
| ------------ | ------- | ------------------------------------------ |
| id           | INTEGER | Unique identifier                          |
| betId        | TEXT    | Bet ID                                     |
| timestamp    | INTEGER | Timestamp for when the bet was filled      |
| matchedBetId | TEXT    | The ID of the bet which filled this bet    |
| amount       | REAL    | Amount that was filled                     |
| shares       | REAL    | Number of shares that were filled          |
| FOREIGN KEY  | -       | `betId` references the `bets` table's `id` |

