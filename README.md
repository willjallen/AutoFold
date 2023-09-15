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

You can easily add your own functionality to this bot by creating a new strategy class in `strategies/your_strategy.py` and adding it to the `config.toml`. An example is provided for you in `strategies/example_strategy.py`.

# ManifoldBot Database Schema

## Tables

### 1. Users

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

### 2. Binary Choice Markets

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

### 3. Multiple Choice Markets

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

#### 4. Multiple Choice Market Answers

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

### 5. Contract Metrics

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

#### 6. Contract Metrics From

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

#### 7. Contract Metrics TotalShares

| Column         | Type    | Description                                                                             |
| -------------- | ------- | --------------------------------------------------------------------------------------- |
| id             | INTEGER | Unique identifier                                                                       |
| contractId     | TEXT    | Contract ID                                                                             |
| userId         | TEXT    | User ID                                                                                 |
| outcome        | TEXT    | Outcome type                                                                            |
| numberOfShares | REAL    | Number of shares                                                                        |
| FOREIGN KEY    | -       | `(contractId, userId)` references the `contract_metrics` table's `(contractId, userId)` |

### 8. Bets

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

#### 9. Bet Fees

| Column             | Type    | Description                                |
| ------------------ | ------- | ------------------------------------------ |
| id                 | INTEGER | Unique identifier                          |
| betId              | TEXT    | Bet ID                                     |
| userId             | TEXT    | User ID                                    |
| fee                | REAL    | Fee amount                                 |
| retrievedTimestamp | INTEGER | Data retrieval timestamp                   |
| FOREIGN KEY        | -       | `betId` references the `bets` table's `id` |

#### 10. Bet Fills

| Column       | Type    | Description                                |
| ------------ | ------- | ------------------------------------------ |
| id           | INTEGER | Unique identifier                          |
| betId        | TEXT    | Bet ID                                     |
| timestamp    | INTEGER | Timestamp for when the bet was filled      |
| matchedBetId | TEXT    | The ID of the bet which filled this bet    |
| amount       | REAL    | Amount that was filled                     |
| shares       | REAL    | Number of shares that were filled          |
| FOREIGN KEY  | -       | `betId` references the `bets` table's `id` |

