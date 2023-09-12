# ManifoldBot

Hassle-free and easy to use bot for [Manifold](https://manifold.markets)

## Features:
- Fully asynchronous API interface with processing queues to respect rate limits
- Local sqlite3 database for offline processing of manifold data
- Subscriber interface to update offline information with granularity

## Setup
1. Clone this repository
2. (Recommended) create a virtual environment, then activate it
   ```
   python -m venv /path/to/new/virtual/environment
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
