``ManifoldBot Database Schema``
================================

.. _1-users:

1. Users
--------

+--------------------+---------+-------------------------------------+
| Column             | Type    | Description                         |
+====================+=========+=====================================+
| id                 | TEXT    | User's unique id                    |
+--------------------+---------+-------------------------------------+
| createdTime        | INTEGER | Timestamp when the user was created |
|                    |         | (milliseconds since epoch)          |
+--------------------+---------+-------------------------------------+
| name               | TEXT    | Display name, may contain spaces    |
+--------------------+---------+-------------------------------------+
| username           | TEXT    | Username, used in URLs              |
+--------------------+---------+-------------------------------------+
| url                | TEXT    | Link to the user's profile          |
+--------------------+---------+-------------------------------------+
| bio                | TEXT    | Optional user's biography           |
+--------------------+---------+-------------------------------------+
| balance            | REAL    | User's balance                      |
+--------------------+---------+-------------------------------------+
| totalDeposits      | REAL    | Total deposits made by the user     |
+--------------------+---------+-------------------------------------+
| totalPnLCached     | REAL    | Cached Profit/Loss of the user      |
+--------------------+---------+-------------------------------------+
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved   |
+--------------------+---------+-------------------------------------+

.. _2-binary-choice-markets:

2. Binary Choice Markets
------------------------

+--------------------+---------+-------------------------------------+
| Column             | Type    | Description                         |
+====================+=========+=====================================+
| id                 | TEXT    | Unique identifier for this market   |
+--------------------+---------+-------------------------------------+
| closeTime          | INTEGER | Min of creator's chosen date, and   |
|                    |         | resolutionTime                      |
+--------------------+---------+-------------------------------------+
| createdTime        | INTEGER | Timestamp when the market was       |
|                    |         | created (milliseconds since epoch)  |
+--------------------+---------+-------------------------------------+
| creatorId          | TEXT    | Identifier for the market creator   |
+--------------------+---------+-------------------------------------+
| creatorName        | TEXT    | Name of the market creator          |
+--------------------+---------+-------------------------------------+
| creatorUsername    | TEXT    | Username of the market creator      |
+--------------------+---------+-------------------------------------+
| isResolved         | BOOLEAN | Whether the market is resolved or   |
|                    |         | not                                 |
+--------------------+---------+-------------------------------------+
| lastUpdatedTime    | INTEGER | Last update timestamp               |
+--------------------+---------+-------------------------------------+
| mechanism          | TEXT    | Market mechanism (``dpm-2`` or      |
|                    |         | ``cpmm-1``)                         |
+--------------------+---------+-------------------------------------+
| outcomeType        | TEXT    | Type of outcome (``BINARY``,        |
|                    |         | ``FREE_RESPONSE``, etc.)            |
+--------------------+---------+-------------------------------------+
| p                  | REAL    | For CPMM markets only, probability  |
|                    |         | constant                            |
+--------------------+---------+-------------------------------------+
| probability        | REAL    | Probability associated with the     |
|                    |         | market                              |
+--------------------+---------+-------------------------------------+
| question           | TEXT    | Market question                     |
+--------------------+---------+-------------------------------------+
| textDescription    | TEXT    | Description of the market           |
+--------------------+---------+-------------------------------------+
| totalLiquidity     | REAL    | For CPMM markets, the amount of     |
|                    |         | mana deposited into the liquidity   |
|                    |         | pool                                |
+--------------------+---------+-------------------------------------+
| url                | TEXT    | URL related to the market           |
+--------------------+---------+-------------------------------------+
| volume             | REAL    | Trading volume for the market       |
+--------------------+---------+-------------------------------------+
| volume24Hours      | REAL    | Trading volume for the market in    |
|                    |         | the last 24 hours                   |
+--------------------+---------+-------------------------------------+
| pool_NO            | REAL    | Liquidity of the 'NO' pool          |
+--------------------+---------+-------------------------------------+
| pool_YES           | REAL    | Liquidity of the 'YES' pool         |
+--------------------+---------+-------------------------------------+
| groupSlugs         | TEXT    | Group slugs associated with the     |
|                    |         | market                              |
+--------------------+---------+-------------------------------------+
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved   |
+--------------------+---------+-------------------------------------+
| lite               | INTEGER | Whether the market was retrieved as |
|                    |         | a LiteMarket                        |
+--------------------+---------+-------------------------------------+

.. _3-multiple-choice-markets:

3. Multiple Choice Markets
--------------------------

+--------------------+---------+-------------------------------------+
| Column             | Type    | Description                         |
+====================+=========+=====================================+
| id                 | TEXT    | Unique identifier for the market    |
+--------------------+---------+-------------------------------------+
| closeTime          | INTEGER | Min of creator's chosen date, and   |
|                    |         | resolutionTime                      |
+--------------------+---------+-------------------------------------+
| createdTime        | INTEGER | Timestamp when the market was       |
|                    |         | created (milliseconds since epoch)  |
+--------------------+---------+-------------------------------------+
| creatorId          | TEXT    | ID of the creator                   |
+--------------------+---------+-------------------------------------+
| creatorName        | TEXT    | Name of the creator                 |
+--------------------+---------+-------------------------------------+
| creatorUsername    | TEXT    | Username of the creator             |
+--------------------+---------+-------------------------------------+
| isResolved         | BOOLEAN | Whether the market is resolved      |
+--------------------+---------+-------------------------------------+
| lastUpdatedTime    | INTEGER | Last update timestamp               |
+--------------------+---------+-------------------------------------+
| mechanism          | TEXT    | Market mechanism (``dpm-2`` or      |
|                    |         | ``cpmm-1``)                         |
+--------------------+---------+-------------------------------------+
| outcomeType        | TEXT    | Type of outcome (``BINARY``,        |
|                    |         | ``FREE_RESPONSE``, etc.)            |
+--------------------+---------+-------------------------------------+
| question           | TEXT    | Market question                     |
+--------------------+---------+-------------------------------------+
| textDescription    | TEXT    | Description of the market           |
+--------------------+---------+-------------------------------------+
| totalLiquidity     | REAL    | For CPMM markets, the amount of     |
|                    |         | mana deposited into the liquidity   |
|                    |         | pool                                |
+--------------------+---------+-------------------------------------+
| volume             | REAL    | Market volume                       |
+--------------------+---------+-------------------------------------+
| volume24Hours      | REAL    | Market volume in the last 24 hours  |
+--------------------+---------+-------------------------------------+
| url                | TEXT    | URL related to the market           |
+--------------------+---------+-------------------------------------+
| groupSlugs         | TEXT    | Market group slugs                  |
+--------------------+---------+-------------------------------------+
| retrievedTimestamp | INTEGER | Timestamp when data was retrieved   |
+--------------------+---------+-------------------------------------+
| lite               | INTEGER | Whether the market was retrieved as |
|                    |         | a LiteMarket flag                   |
+--------------------+---------+-------------------------------------+

.. _4-multiple-choice-market-answers:

4. Multiple Choice Market Answers
-----------------------------------

+----------------+---------+-----------------------------------------+
| Column         | Type    | Description                             |
+================+=========+=========================================+
| id             | INTEGER | Unique identifier for the answer,       |
|                |         | auto-incremented                        |
+----------------+---------+-----------------------------------------+
| contractId     | TEXT    | Identifier for the associated market    |
|                |         | contract                                |
+----------------+---------+-----------------------------------------+
| createdTime    | INTEGER | Timestamp when the answer was created   |
+----------------+---------+-----------------------------------------+
| fsUpdatedTime  | TEXT    | Timestamp of the last update for the    |
|                |         | answer                                  |
+----------------+---------+-----------------------------------------+
| isOther        | INTEGER | Indicator if this is an 'other' option  |
|                |         | (usually 0 or 1)                        |
+----------------+---------+-----------------------------------------+
| answerIndex    | INTEGER | Index or order of this answer in the    |
|                |         | list                                    |
+----------------+---------+-----------------------------------------+
| probability    | REAL    | Probability associated with the answer  |
+----------------+---------+-----------------------------------------+
| subsidyPool    | REAL    | Subsidy pool amount for this answer     |
+----------------+---------+-----------------------------------------+
| text           | TEXT    | Textual description or content of the   |
|                |         | answer                                  |
+----------------+---------+-----------------------------------------+
| totalLiquidity | REAL    | Total liquidity associated with this    |
|                |         | answer                                  |
+----------------+---------+-----------------------------------------+
| userId         | TEXT    | Identifier for the user associated with |
|                |         | this answer                             |
+----------------+---------+-----------------------------------------+
| pool_NO        | REAL    | Liquidity of the 'NO' pool for this     |
|                |         | answer                                  |
+----------------+---------+-----------------------------------------+
| pool_YES       | REAL    | Liquidity of the 'YES' pool for this    |
|                |         | answer                                  |
+----------------+---------+-----------------------------------------+
| FOREIGN KEY    | -       | ``contractId`` references the           |
|                |         | ``multiple_choice_markets`` table's     |
|                |         | ``id``                                  |
+----------------+---------+-----------------------------------------+

.. _5-contract-metrics:

5. Contract Metrics
---------------------

+---------------------+---------+------------------------------------------+
| Column              | Type    | Description                              |
+=====================+=========+==========================================+
| contractId          | TEXT    | Contract identifier                      |
+---------------------+---------+------------------------------------------+
| hasNoShares         | INTEGER | Whether there are No shares              |
+---------------------+---------+------------------------------------------+
| hasShares           | INTEGER | Whether there are shares                 |
+---------------------+---------+------------------------------------------+
| hasYesShares        | INTEGER | Whether there are Yes shares             |
+---------------------+---------+------------------------------------------+
| invested            | REAL    | Amount invested                          |
+---------------------+---------+------------------------------------------+
| loan                | REAL    | Loan amount                              |
+---------------------+---------+------------------------------------------+
| maxSharesOutcome    | TEXT    | Maximum shares outcome                   |
+---------------------+---------+------------------------------------------+
| payout              | REAL    | Payout amount                            |
+---------------------+---------+------------------------------------------+
| profit              | REAL    | Profit amount                            |
+---------------------+---------+------------------------------------------+
| profitPercent       | REAL    | Profit percentage                        |
+---------------------+---------+------------------------------------------+
| userId              | TEXT    | User ID                                  |
+---------------------+---------+------------------------------------------+
| userUsername        | TEXT    | User username                            |
+---------------------+---------+------------------------------------------+
| userName            | TEXT    | User name                                |
+---------------------+---------+------------------------------------------+
| lastBetTime         | INTEGER | Last bet timestamp                       |
+---------------------+---------+------------------------------------------+
| retrievedTimestamp  | INTEGER | Timestamp when data was retrieved        |
+---------------------+---------+------------------------------------------+


.. _6-contract-metrics-from:

6. Contract Metrics From
--------------------------

+---------------+---------+------------------------------------------+
| Column        | Type    | Description                              |
+===============+=========+==========================================+
| id            | INTEGER | Unique identifier                        |
+---------------+---------+------------------------------------------+
| contractId    | TEXT    | Contract ID                              |
+---------------+---------+------------------------------------------+
| userId        | TEXT    | User ID                                  |
+---------------+---------+------------------------------------------+
| period        | TEXT    | Time period (one of day, week, month)    |
+---------------+---------+------------------------------------------+
| value         | REAL    | Value amount                             |
+---------------+---------+------------------------------------------+
| profit        | REAL    | Profit amount                            |
+---------------+---------+------------------------------------------+
| invested      | REAL    | Investment amount                        |
+---------------+---------+------------------------------------------+
| prevValue     | REAL    | Previous value                           |
+---------------+---------+------------------------------------------+
| profitPercent | REAL    | Profit percentage                        |
+---------------+---------+------------------------------------------+
| FOREIGN KEY   | -       | ``(contractId, userId)`` references the  |
|               |         | ``contract_metrics`` table's             |
|               |         | ``(contractId, userId)``                 |
+---------------+---------+------------------------------------------+

.. _7-contract-metrics-totalshares:

1. Contract Metrics TotalShares
---------------------------------

+----------------+---------+-----------------------------------------+
| Column         | Type    | Description                             |
+================+=========+=========================================+
| id             | INTEGER | Unique identifier                       |
+----------------+---------+-----------------------------------------+
| contractId     | TEXT    | Contract ID                             |
+----------------+---------+-----------------------------------------+
| userId         | TEXT    | User ID                                 |
+----------------+---------+-----------------------------------------+
| outcome        | TEXT    | Outcome type                            |
+----------------+---------+-----------------------------------------+
| numberOfShares | REAL    | Number of shares                        |
+----------------+---------+-----------------------------------------+
| FOREIGN KEY    | -       | ``(contractId, userId)`` references the |
|                |         | ``contract_metrics`` table's            |
|                |         | ``(contractId, userId)``                |
+----------------+---------+-----------------------------------------+

.. _8-bets:

8. Bets
---------

+---------------------+---------+------------------------------------------+
| Column              | Type    | Description                              |
+=====================+=========+==========================================+
| id                  | TEXT    | Unique identifier for the bet            |
+---------------------+---------+------------------------------------------+
| userId              | TEXT    | User ID                                  |
+---------------------+---------+------------------------------------------+
| contractId          | TEXT    | Contract ID                              |
+---------------------+---------+------------------------------------------+
| isFilled            | INTEGER | Whether the bet is filled                |
+---------------------+---------+------------------------------------------+
| amount              | REAL    | Amount of the bet                        |
+---------------------+---------+------------------------------------------+
| probBefore          | REAL    | Probability before the bet               |
+---------------------+---------+------------------------------------------+
| isCancelled         | INTEGER | Whether the bet is cancelled             |
+---------------------+---------+------------------------------------------+
| outcome             | TEXT    | Bet outcome                              |
+---------------------+---------+------------------------------------------+
| shares              | REAL    | Number of shares                         |
+---------------------+---------+------------------------------------------+
| limitProb           | REAL    | Limit probability                        |
+---------------------+---------+------------------------------------------+
| loanAmount          | REAL    | Loan amount                              |
+---------------------+---------+------------------------------------------+
| orderAmount         | REAL    | Order amount                             |
+---------------------+---------+------------------------------------------+
| probAfter           | REAL    | Probability after the bet                |
+---------------------+---------+------------------------------------------+
| createdTime         | INTEGER | Bet creation timestamp                   |
+---------------------+---------+------------------------------------------+
| retrievedTimestamp  | INTEGER | Timestamp when data was retrieved        |
+---------------------+---------+------------------------------------------+


.. _9-bet-fees:

9. Bet Fees
------------

+--------------------+---------+-------------------------------------+
| Column             | Type    | Description                         |
+====================+=========+=====================================+
| id                 | INTEGER | Unique identifier                   |
+--------------------+---------+-------------------------------------+
| betId              | TEXT    | Bet ID                              |
+--------------------+---------+-------------------------------------+
| userId             | TEXT    | User ID                             |
+--------------------+---------+-------------------------------------+
| fee                | REAL    | Fee amount                          |
+--------------------+---------+-------------------------------------+
| retrievedTimestamp | INTEGER | Data retrieval timestamp            |
+--------------------+---------+-------------------------------------+
| FOREIGN KEY        | -       | ``betId`` references the ``bets``   |
|                    |         | table's ``id``                      |
+--------------------+---------+-------------------------------------+

.. _10-bet-fills:

10. Bet Fills
--------------

+----------------+---------+--------------------------------------------------+
| Column         | Type    | Description                                      |
+================+=========+==================================================+
| id             | INTEGER | Unique identifier                                |
+----------------+---------+--------------------------------------------------+
| betId          | TEXT    | Bet ID                                           |
+----------------+---------+--------------------------------------------------+
| timestamp      | INTEGER | Timestamp for when the bet was filled            |
+----------------+---------+--------------------------------------------------+
| matchedBetId   | TEXT    | The ID of the bet which filled this bet          |
+----------------+---------+--------------------------------------------------+
| amount         | REAL    | Amount that was filled                           |
+----------------+---------+--------------------------------------------------+
| shares         | REAL    | Number of shares that were filled                |
+----------------+---------+--------------------------------------------------+
| FOREIGN KEY    | -       | ``betId`` references the ``bets`` table's ``id`` |
+----------------+---------+--------------------------------------------------+