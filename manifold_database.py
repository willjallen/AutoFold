import requests
import sqlite3
import json
import time

class ManifoldDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("manifold.db")


    def create_tables(self):
        c = self.conn.cursor()

        # Create users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            createdTime INTEGER,
            name TEXT,
            username TEXT,
            url TEXT,
            avatarUrl TEXT,
            bio TEXT,
            balance REAL,
            totalDeposits REAL,
            totalPnLCached REAL
        );
        """)

        # Create markets table
        c.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            id TEXT PRIMARY KEY,
            creatorUsername TEXT,
            creatorName TEXT,
            createdTime INTEGER,
            creatorAvatarUrl TEXT,
            closeTime INTEGER,
            question TEXT,
            url TEXT,
            outcomeType TEXT,
            mechanism TEXT,
            probability REAL,
            volume REAL,
            volume24Hours REAL,
            isResolved INTEGER,
            resolutionTime INTEGER,
            resolution TEXT,
            resolutionProbability REAL,
            lastUpdatedTime INTEGER
        );
        """)

        # Create contract_metrics table
        c.execute("""
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
        
        c.execute("""
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
        c.execute("""
        CREATE TABLE IF NOT EXISTS contract_metrics_totalShares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractId TEXT,
            outcome TEXT,
            numberOfShares REAL,
            FOREIGN KEY (contractId) REFERENCES contract_metrics(contractId)
        ); 
        """)

        # Create bets table
        c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id TEXT PRIMARY KEY,
            isFilled INTEGER,
            amount REAL,
            userId TEXT,
            contractId TEXT,
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

        self.conn.commit()
        self.conn.close()


    '''
    ########################################################
    ####                    USERS                       ####
    ########################################################
    '''

    def upsert_user(self, user: dict):
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO users (id, createdTime, name, username, url, avatarUrl, bio, balance, totalDeposits, profitCached)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user['id'], 
                user['createdTime'], 
                user['name'], 
                user['username'], 
                user['url'], 
                user['avatarUrl'], 
                user['bio'], 
                user['balance'], 
                user['totalDeposits'], 
                json.dumps(user.get('profitCached', {}))
                )
            )
    
    '''
    ########################################################
    ####                    MARKETS                      ####
    ########################################################
    '''
    # Upsert LiteMarket
    def upsert_lite_market(self, lite_market: dict):
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO lite_markets (
                id, creatorUsername, creatorName, createdTime, creatorAvatarUrl,
                closeTime, question, url, outcomeType, mechanism, probability,
                volume, volume24Hours, isResolved, resolutionTime, resolution,
                resolutionProbability, lastUpdatedTime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lite_market['id'], 
                lite_market['creatorUsername'], 
                lite_market['creatorName'],
                lite_market['createdTime'], 
                lite_market['creatorAvatarUrl'], 
                lite_market['closeTime'],
                lite_market['question'], 
                lite_market['url'], 
                lite_market['outcomeType'],
                lite_market['mechanism'], 
                lite_market['probability'], 
                lite_market['volume'],
                lite_market['volume24Hours'], 
                lite_market['isResolved'], 
                lite_market['resolutionTime'],
                lite_market['resolution'], 
                lite_market['resolutionProbability'], 
                lite_market['lastUpdatedTime']
            ))

    def get_liteMarket_by_id(self, liteMarket_id: str) -> dict:
        cur = self.conn.execute("SELECT * FROM liteMarkets WHERE id = ?", (liteMarket_id,))
        return cur.fetchone()

    def delete_liteMarket(self, liteMarket_id: str):
        with self.conn:
            self.conn.execute("DELETE FROM liteMarkets WHERE id = ?", (liteMarket_id,))


    # Upsert FullMarket
    def upsert_full_market(self, full_market: dict):
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO full_markets (
                id, description, textDescription, groupSlugs
            )
            VALUES (?, ?, ?, ?)
            """, (
                full_market['id'], json.dumps(full_market['description']), full_market['textDescription'],
                json.dumps(full_market.get('groupSlugs', []))
            ))
            
    '''
    ########################################################
    ####                 CONTRACT METRICS               ####
    ########################################################
    '''
    def create_or_update_contract_metric(self, contract_metric: dict):
        c = self.conn.cursor()
        
        # Insert or Replace into main table
        c.execute("""
        INSERT OR REPLACE INTO contract_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contract_metric['contractId'],
            int(contract_metric['hasNoShares']),
            int(contract_metric['hasShares']),
            int(contract_metric['hasYesShares']),
            contract_metric['invested'],
            contract_metric['loan'],
            contract_metric['maxSharesOutcome'],
            contract_metric['payout'],
            contract_metric['profit'],
            contract_metric['profitPercent'],
            contract_metric['userId'],
            contract_metric['userUsername'],
            contract_metric['userName'],
            contract_metric['userAvatarUrl'],
            contract_metric['lastBetTime']
        ))

        # Delete existing nested 'from' data, then insert new data
        c.execute("DELETE FROM contract_metrics_from WHERE contractId = ?", (contract_metric['contractId'],))
        for period, data in contract_metric.get('from', {}).items():
            c.execute("""
            INSERT INTO contract_metrics_from (contractId, period, value, profit, invested, prevValue, profitPercent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                contract_metric['contractId'],
                period,
                data['value'],
                data['profit'],
                data['invested'],
                data['prevValue'],
                data['profitPercent']
            ))

        # Delete existing nested 'totalShares' data, then insert new data
        c.execute("DELETE FROM contract_metrics_totalShares WHERE contractId = ?", (contract_metric['contractId'],))
        for outcome, shares in contract_metric.get('totalShares', {}).items():
            c.execute("""
            INSERT INTO contract_metrics_totalShares (contractId, outcome, numberOfShares)
            VALUES (?, ?, ?)
            """, (
                contract_metric['contractId'],
                outcome,
                shares
            ))

        self.conn.commit() 