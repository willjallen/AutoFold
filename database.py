import json
import sqlite3
import threading
import time

class Database:
    def __init__(self):
        self.local_storage = threading.local()

    def get_conn(self):
        if not hasattr(self.local_storage, "conn"):
            self.local_storage.conn = sqlite3.connect("database.db")
            self.local_storage.conn.execute("PRAGMA journal_mode=WAL;")
        return self.local_storage.conn

    def create_tables(self):
        conn = self.get_conn()
        
        '''
        ########################################################
        ####                    USERS                       ####
        ########################################################
        '''
        # Create users table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            createdTime INTEGER,
            name TEXT,
            username TEXT,
            url TEXT,
            bio TEXT,
            balance REAL,
            totalDeposits REAL,
            totalPnLCached REAL
        );
        """)
        
        '''
        ########################################################
        ####                    MARKETS                     ####
        ########################################################
        '''
        # Create binary markets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS binary_choice_markets (
            id TEXT PRIMARY KEY,
            closeTime INTEGER,
            createdTime INTEGER,
            creatorId TEXT,
            creatorName TEXT,
            creatorUsername TEXT,
            isResolved BOOLEAN,
            lastUpdatedTime INTEGER,
            mechanism TEXT,
            outcomeType TEXT,
            p REAL,
            probability REAL,
            question TEXT,
            textDescription TEXT,
            totalLiquidity REAL,
            url TEXT,
            volume REAL,
            volume24Hours REAL,
            pool_NO REAL,
            pool_YES REAL,
            groupSlugs TEXT,
            retrieved_timestamp INTEGER,
            lite INTEGER
        );
        """)
        
        # Create multiple choice markets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS multiple_choice_markets (
            id TEXT PRIMARY KEY,
            closeTime INTEGER,
            createdTime INTEGER,
            creatorId TEXT,
            creatorName TEXT,
            creatorUsername TEXT,
            isResolved BOOLEAN,
            lastUpdatedTime INTEGER,
            mechanism TEXT,
            outcomeType TEXT,
            question TEXT,
            textDescription TEXT,
            totalLiquidity REAL,
            volume REAL,
            volume24Hours REAL,
            url TEXT,
            groupSlugs TEXT,
            retrieved_timestamp INTEGER,
            lite INTEGER
        );
        """)

        # Create 'nested' answers table for multiple choice markets
        conn.execute("""
        CREATE TABLE IF NOT EXISTS multiple_choice_market_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            createdTime INTEGER,
            fsUpdatedTime TEXT,
            isOther INTEGER,
            answerIndex INTEGER,
            probability REAL,
            subsidyPool REAL,
            text TEXT,
            totalLiquidity REAL,
            userId TEXT,
            pool_NO REAL,
            pool_YES REAL,
            FOREIGN KEY(contractId) REFERENCES multiple_choice_markets(id)
        ); 
        """)

        '''
        ########################################################
        ####                 CONTRACT METRICS               ####
        ########################################################
        '''
        # Create contract_metrics table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics (
            contractId TEXT PRIMARY KEY,
            hasNoShares INTEGER,
            hasShares INTEGER,
            hasYesShares INTEGER,
            invested REAL,
            loan REAL,
            maxSharesOutcome TEXT,
            payout REAL,
            profit REAL,
            profitPercent REAL,
            userId TEXT,
            userUsername TEXT,
            userName TEXT,
            userAvatarUrl TEXT,
            lastBetTime INTEGER
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics_from (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            period TEXT,
            value REAL,
            profit REAL,
            invested REAL,
            prevValue REAL,
            profitPercent REAL,
            FOREIGN KEY (contractId) REFERENCES contract_metrics(contractId)
        ); 
        """)

        # contract_metrics_totalShares table to represent 'totalShares' nested structure
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics_totalShares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            outcome TEXT,
            numberOfShares REAL,
            FOREIGN KEY (contractId) REFERENCES contract_metrics(contractId)
        ); 
        """)

        '''
        ########################################################
        ####                    BETS                        ####
        ########################################################
        '''
        # Create bets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id TEXT PRIMARY KEY,
            userId TEXT,
            contractId TEXT,
            isFilled INTEGER,
            amount REAL,
            probBefore REAL,
            isCancelled INTEGER,
            outcome TEXT,
            shares REAL,
            limitProb REAL,
            loanAmount REAL,
            orderAmount REAL,
            probAfter REAL,
            createdTime INTEGER
        );
        """)

        # Create fees table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            betId TEXT,
            creatorFee REAL,
            liquidityFee REAL,
            platformFee REAL,
            FOREIGN KEY (betId) REFERENCES bets(id)
        );
        """)

        # Create fills table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bet_fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            betId TEXT,
            timestamp INTEGER,
            matchedBetId TEXT,
            amount REAL,
            shares REAL,
            FOREIGN KEY (betId) REFERENCES bets(id)
        );
        """)

        conn.commit()


    '''
    ########################################################
    ####                    USERS                       ####
    ########################################################
    '''

    def upsert_users(self, users: list[dict]):
        conn = self.get_conn()
        try:
            with conn:
                # Base fields that are common to all users
                fields = [
                    "id", "createdTime", "name", "username", 
                    "url", "bio", "balance", "totalDeposits", 
                    "totalPnLCached"
                ]

                # Create SQL query strings
                sql_fields_str = ", ".join(fields)
                sql_placeholders_str = ", ".join("?" for _ in fields)

                sql_query = f"""
                INSERT OR REPLACE INTO users (
                    {sql_fields_str}
                )
                VALUES (
                    {sql_placeholders_str}
                )
                """

                # Create tuple of values
                values_tuples = [tuple(user.get(field, None) for field in fields) for user in users]

                # Execute the SQL query
                conn.executemany(sql_query, values_tuples)
        except sqlite3.Error as e:
            print("Database error in upsert_users:", e)

    
    '''
    ########################################################
    ####                    MARKETS                     ####
    ########################################################
    '''
    
    # Upsert Market
    def upsert_binary_choice_markets(self, markets: list[dict], lite=True):
        conn = self.get_conn()
        try:
            with conn:
                fields = [
                    "id", "closeTime", "createdTime", "creatorId", "creatorName", 
                    "creatorUsername", "isResolved", "lastUpdatedTime", "mechanism", 
                    "outcomeType", "p", "probability", "question", "textDescription",
                    "totalLiquidity", "url", "volume", "volume24Hours", "pool_NO", 
                    "pool_YES", "groupSlugs", "retrieved_timestamp", "lite"
                ]
                

                # Create SQL query strings
                sql_fields_str = ", ".join(fields)
                sql_placeholders_str = ", ".join("?" for _ in fields)

                sql_query = f"""
                INSERT OR REPLACE INTO binary_choice_markets (
                    {sql_fields_str}
                )
                VALUES (
                    {sql_placeholders_str}
                )
                """

                # Create tuple of values
                values_tuple = []

                for market in markets:
                    market_values = []
                    for field in fields:
                        if field == "pool_NO":
                            value = market["pool"].get("NO", None)
                            
                        elif field == "pool_YES":
                            value = market["pool"].get("YES", None)
                            
                        elif field == "groupSlugs":
                            if market.get("groupSlugs", None):
                                def collapse(lst):
                                    return ' ' .join(item for item in lst)
                                value = collapse(market["groupSlugs"])
                            else: 
                                value = None
                                
                        elif field == "retrieved_timestamp":
                            value = int(time.time())  # Set to current UNIX epoch time
                            
                        elif field == "lite":
                            value = int(lite)
                            
                        else:
                            value = market.get(field, None)
                        
                        market_values.append(value)
                    
                    values_tuple.append(tuple(market_values))
                
                # Execute the SQL query
                conn.executemany(sql_query, values_tuple)


        except sqlite3.Error as e:
            print("Database error in upsert_binary_choice_markets", e)

    def upsert_multiple_choice_markets(self, markets: list[dict], lite=True):
        conn = self.get_conn()
        try:
            with conn:
                fields = [
                    "id", "closeTime", "createdTime", "creatorId", "creatorName", 
                    "creatorUsername", "isResolved", "lastUpdatedTime", "mechanism", 
                    "outcomeType", "question", "textDescription", 
                    "totalLiquidity", "volume", "volume24Hours", 
                    "url", "groupSlugs", "retrieved_timestamp", "lite"
                ]
                
                # Create SQL query strings
                sql_fields_str = ", ".join(fields)
                sql_placeholders_str = ", ".join("?" for _ in fields)

                sql_query = f"""
                INSERT OR REPLACE INTO multiple_choice_markets (
                    {sql_fields_str}
                )
                VALUES (
                    {sql_placeholders_str}
                )
                """

                # Create tuple of values
                values_tuple = []

                for market in markets:
                    market_values = []
                    for field in fields:
                        if field == "groupSlugs":
                            if market.get("groupSlugs", None):
                                def collapse(lst):
                                    return ' ' .join(item for item in lst)
                                value = collapse(market["groupSlugs"])
                            else:
                                value = None
                                
                        elif field == "retrieved_timestamp":
                            value = int(time.time())  # Set to current UNIX epoch time
                            
                        elif field == "lite":
                            value = int(lite)
                            
                        else:
                            value = market.get(field, None)
                        
                        market_values.append(value)
                        
                    values_tuple.append(tuple(market_values))
                
                # Execute the SQL query
                conn.executemany(sql_query, values_tuple)
                
                # Handle answers
                if not lite:
                    for market in markets:
                        conn.execute("DELETE FROM multiple_choice_market_answers WHERE contractId = ?", (market['id'],))
                        for answer in market["answers"]:
                            answer_fields = [
                                    "contractId", "createdTime", "fsUpdatedTime", "isOther", "answerIndex", 
                                    "probability", "subsidyPool", "text", "totalLiquidity", "userId", 
                                    "pool_NO", "pool_YES"
                            ] 

                            # Create SQL query strings
                            sql_answer_fields_str = ", ".join(answer_fields)
                            sql_answer_placeholders_str = ", ".join("?" for _ in answer_fields)

                            sql_answer_query = f"""
                            INSERT OR REPLACE INTO multiple_choice_market_answers (
                                {sql_answer_fields_str}
                            )
                            VALUES (
                                {sql_answer_placeholders_str}
                            )
                            """ 
                            
                            # Create tuple of values
                            answer_values = []

                            for field in answer_fields:
                                if field == "pool_NO":
                                    value = answer["pool"]["NO"]
                                elif field == "pool_YES":
                                    value = answer["pool"]["YES"]
                                elif field == "answerIndex":
                                    value == answer.get("index", None)
                                else:
                                    value = answer.get(field, None)
                                
                                answer_values.append(value)
                                
                            conn.execute(sql_answer_query, tuple(answer_values))
        except sqlite3.Error as e:
            print("Database error in upsert_multiple_choice_markets", e)
        

    # '''
    # ########################################################
    # ####                 CONTRACT METRICS               ####
    # ########################################################
    # '''
    # def upsert_contract_metric(self, contract_metric: dict):
    #     with self.conn:
    #         # Base fields that are common to all contract metrics
    #         base_fields = [
    #             "contractId", "hasNoShares", "hasShares", "hasYesShares",
    #             "invested", "loan", "maxSharesOutcome", "payout", 
    #             "profit", "profitPercent", "userId", "userUsername", 
    #             "userName", "userAvatarUrl", "lastBetTime"
    #         ]

    #         # Create SQL query strings
    #         sql_fields_str = ", ".join(base_fields)
    #         sql_placeholders_str = ", ".join("?" for _ in base_fields)

    #         sql_query = f"""
    #         INSERT OR REPLACE INTO contract_metrics (
    #             {sql_fields_str}
    #         )
    #         VALUES (
    #             {sql_placeholders_str}
    #         )
    #         """

    #         # Create tuple of values
    #         values_tuple = tuple(contract_metric.get(field, None) for field in base_fields)

    #         # Execute the SQL query for the main table
    #         self.conn.execute(sql_query, values_tuple)

    #         # Delete existing nested 'from' data, then insert new data
    #         self.conn.execute("DELETE FROM contract_metrics_from WHERE contractId = ?", (contract_metric['contractId'],))
    #         for period, data in contract_metric.get('from', {}).items():
    #             self.conn.execute("""
    #             INSERT INTO contract_metrics_from (contractId, period, value, profit, invested, prevValue, profitPercent)
    #             VALUES (?, ?, ?, ?, ?, ?, ?)
    #             """, (
    #                 contract_metric['contractId'],
    #                 period,
    #                 data['value'],
    #                 data['profit'],
    #                 data['invested'],
    #                 data['prevValue'],
    #                 data['profitPercent']
    #             ))

    #         # Delete existing nested 'totalShares' data, then insert new data
    #         self.conn.execute("DELETE FROM contract_metrics_totalShares WHERE contractId = ?", (contract_metric['contractId'],))
    #         for outcome, shares in contract_metric.get('totalShares', {}).items():
    #             self.conn.execute("""
    #             INSERT INTO contract_metrics_totalShares (contractId, outcome, numberOfShares)
    #             VALUES (?, ?, ?)
    #             """, (
    #                 contract_metric['contractId'],
    #                 outcome,
    #                 shares
    #             ))

    #         self.conn.commit()
            
    # '''
    # ########################################################
    # ####                      BETS                      ####
    # ########################################################
    # '''
    # def upsert_bet(self, bet: dict):
    #     with self.conn:
    #         # Base fields that are common to all bets
    #         base_fields = [
    #             "id", "userId", "contractId", "isFilled", "amount", 
    #             "probBefore", "isCancelled", "outcome", "shares", 
    #             "limitProb", "loanAmount", "orderAmount", 
    #             "probAfter", "createdTime"
    #         ]

    #         # Create SQL query strings
    #         sql_fields_str = ", ".join(base_fields)
    #         sql_placeholders_str = ", ".join("?" for _ in base_fields)

    #         sql_query = f"""
    #         INSERT OR REPLACE INTO bets (
    #             {sql_fields_str}
    #         )
    #         VALUES (
    #             {sql_placeholders_str}
    #         )
    #         """

    #         # Create tuple of values
    #         values_tuple = tuple(bet.get(field, None) for field in base_fields)

    #         # Execute the SQL query for the main table
    #         self.conn.execute(sql_query, values_tuple)

    #         # Insert data into bet_fees table
    #         fees = bet.get('fees', {})
    #         self.conn.execute("""
    #         INSERT OR REPLACE INTO bet_fees (betId, creatorFee, liquidityFee, platformFee)
    #         VALUES (?, ?, ?, ?)
    #         """, (
    #             bet['id'],
    #             fees.get('creatorFee', 0),
    #             fees.get('liquidityFee', 0),
    #             fees.get('platformFee', 0)
    #         ))

    #         # Delete existing nested 'fills' data, then insert new data
    #         self.conn.execute("DELETE FROM bet_fills WHERE betId = ?", (bet['id'],))
    #         for fill in bet.get('fills', []):
    #             self.conn.execute("""
    #             INSERT INTO bet_fills (betId, timestamp, matchedBetId, amount, shares)
    #             VALUES (?, ?, ?, ?, ?)
    #             """, (
    #                 bet['id'],
    #                 fill['timestamp'],
    #                 fill.get('matchedBetId', None),
    #                 fill['amount'],
    #                 fill['shares']
    #             ))

    #         self.conn.commit()
