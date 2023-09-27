autofold
===========

.. image:: https://readthedocs.org/projects/manifoldbot/badge/?version=latest
    :target: https://manifoldbot.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status



All-in-one API, local database, data subscriber and bot interface for
`Manifold.markets <https://manifold.markets>`__

`Full documentation here <https://manifoldbot.readthedocs.io/en/latest/>`__

Features:
---------

-  **ManifoldAPI**:

   -  Asynchronous future-based API interface with full coverage
   -  Token-bucket rate limiting

-  **ManifoldDatabse**:

   -  Local sqlite3 database for offline processing of manifold data
   -  Simple interface for reading & executing queries
   -  Writing is handled via subscribers

-  **ManifoldSubscriber**:

   -  Subscriber interface to automatically retrieve and update offline
      information with granularity
   -  Allows registering callbacks to updates

-  **AutomationBot**

   -  Autonomously run multiple custom automations
 


.. _list of API calls: https://loguru.readthedocs.io/en/stable/api/logger.html#file

Installation
------------

To get started with the package, you can install it using pip.

::

   pip install autofold

Setting Up the API Key
----------------------

After installing the package, you'll need to set up your API key. You should set this key as an environment variable, named ``MANIFOLD_API_KEY``.

Unix/Linux/macOS
~~~~~~~~~~~~~~~~

If you're using a Unix-like operating system, you can set the environment variable in your shell session using the ``export`` command:

::

   export MANIFOLD_API_KEY="your_api_key_here"

You may also want to add this command to your ``.bashrc`` or ``.zshrc`` file to ensure the variable is set whenever you open a new terminal window.

Windows
~~~~~~~~

On Windows, you can set an environment variable using the ``setx`` command:

::

   setx MANIFOLD_API_KEY "your_api_key_here"

Note that this will set the environment variable permanently but it won't affect currently open command prompts. You'll need to restart any open command prompts or open a new one to see the change.


Quick Start
-------------


AutomationBot
~~~~~~~~~~~~~~
The AutomationBot is responsible for starting, stopping and maintaining threads and connections to the manifold API, manifold database and manifold subscriber.
Additionally, AutomationBot is reponsible for maintaining, adding, removing, starting and stopping automations. 
This class provides everything you need to start writing automations.

Initialization
^^^^^^^^^^^^^^^
Create an instance of the ``AutomationBot`` class.

.. code-block:: python3

   automation_bot = AutomationBot()

Instantiate your automation. (Details on automations in the next section)

.. code-block:: python3

   my_automation = MyStrategy()

Register your automation with the bot

.. code-block:: python3

   automation_bot.register_automation(my_automation, "my_strategy")

Start the bot

.. code-block:: python3

   automation_bot.start()

Optionally add something blocking to prevent the main thread from exiting and put a ``stop()`` call after.

.. code-block:: python3

   input('Press any key to stop')
   automation_bot.stop()

Automations
~~~~~~~~~~~~

You can easily add your own automations by implementing a subclass of ``Automation``:

.. code-block:: python3

   class Automation(ABC):

      def __init__(self, db_name: str=""):
         '''
         Initializer for the automation class.

         :param str db_name: Required. The name of the database file to use, without the extension.


         Attributes:
         -----------
         - ``automation_bot``: The ManifoldBot instance.
         - ``manifold_api``: The ManifoldAPI instance extracted from automation_bot.
         - ``manifold_db_reader``: The ManifoldDatabaseReader instance extracted from automation_bot.
         - ``manifold_subscriber``: The ManifoldSubscriber instance extracted from automation_bot.
         - ``db``: The TinyDB instance for this automation.
         ''' 
         self.db_name = db_name

      @abstractmethod
      def start(self, *args, **kwargs):
         '''
         Abstract method to start the automation.

         .. note::
            This method must be implemented in subclasses.

         :param args: Additional positional arguments.
         :param kwargs: Additional keyword arguments.
         '''
         pass
      
      @abstractmethod
      def stop(self, *args, **kwargs):
         '''
         Abstract method to stop the automation.

         .. note::
            This method must be implemented in subclasses.

         :param args: Additional positional arguments.
         :param kwargs: Additional keyword arguments.
         '''
         pass

.. warning::

   Automations MUST be registered with the bot for the object attributes to be set. This must be done before you run the automation.

.. note::

   All child classes of automation are provided a local tinydb for non-volatile storage if needed.
   Note that tinydb is NOT threadsafe; proper access safety should be used when accessing data between automations.
   Feel free to use your own storage medium as you see fit.

An instance of ``AutomationBot``, ``ManifoldAPI``, ``ManifoldDatabaseReader`` and
``ManifoldSubscriber`` is provided to each automation.

When the ``AutomationBot`` is started, by default it will call the ``run()`` function for
each automation. Likewise, when the program gets a shutdown signal it will
call the ``stop()`` function for each automation.

An example automation is available in ``automations/bet_automation.py``

.. end-of-readme-intro

Manifold API
~~~~~~~~~~~~

The ``ManifoldAPI`` class provides an interface to interact with
the Manifold.markets API. 

Key Features:
^^^^^^^^^^^^^

-  **Token Bucket Rate Limiting**: The class implements a
   token-bucket-based rate limiting mechanism to ensure compliance with
   the Manifold.markets API rate limits.
-  **Asynchronous Execution**: Operations that make API calls are
   executed asynchronously using Python's ``ThreadPoolExecutor``.
-  **Future-based Interface**: The methods in the class return
   ``Future`` objects, allowing you flexibility on how to handle the results.

Initialization
^^^^^^^^^^^^^^

Create an instance of the ``ManifoldAPI`` class.

.. code-block:: python3

   api = ManifoldAPI()

Making API Calls
^^^^^^^^^^^^^^^^^

You can find a full `list of API calls`_ in the documentation.

Get a user by their username:

.. code-block:: python3

   future_result = api.get_user_by_username("sampleUsername")
   user_data = future_result.result()

Sell your shares in a market:

.. code-block:: python3

   future_result = api.sell_shares("marketId123", "YES", 10)
   status = future_result.resut()

To fetch all available data from a paginated API endpoint, use the retrieve_all_data method:

.. code-block:: python3

   users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)

.. Note:: 

   ``retrieve_all_data`` returns all of the data instead of a ``Future`` object and is blocking.

Manifold Database
~~~~~~~~~~~~~~~~~

-  There are two classes you should use directly:
   ``ManifoldDatabaseReader`` and ``ManifoldDatabaseWriter``.

.. Note:: 

   You should only need to use ``ManifoldDatabaseReader`` as inserting/updating new data is handled for you when you use the ``ManifoldSubscriber`` class.

Initialization
^^^^^^^^^^^^^^^

Create an instance of the ``ManifoldDatabase`` class.

.. code-block:: python3

   manifold_db = ManifoldDatabase()

Create the tables:

.. code-block:: python3

      manifold_db.create_tables()

Using the database
^^^^^^^^^^^^^^^^^^^

Create an instance of the ``ManifoldDatabaseReader`` and ``ManifoldDatabaseWriter`` classes:

.. code-block:: python3

   manifold_db_reader = ManifoldDatabaseReader(manifold_db)
   manifold_db_writer = ManifoldDatabaseWriter(manifold_db)

Writing information to the database:

.. code-block:: python3

   users = self.manifold_api.retrieve_all_data(self.manifold_api.get_users, max_limit=1000)
   manifold_db_writer.queue_write_operation(function=self.manifold_db.upsert_users, data=users).result()

Reading information from the database

.. code-block:: python3

   # Find top 10 binary choice markets with highest volume 
   markets = manifold_db_reader.execute_query(
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

Manifold Subscriber
~~~~~~~~~~~~~~~~~~~

-  Provides an easy way to schedule fetching specific data from the
   Manifold API
-  Allows registering callbacks for each fetch operation

Initialization
^^^^^^^^^^^^^^^

Create an instance of the ``ManifoldSubscriber`` class.

.. code-block:: python3

   manifold_subscriber = ManifoldSubscriber(manifold_api, manifold_db, manifold_db_writer)

Using the subscriber
^^^^^^^^^^^^^^^^^^^^^

Subscribe to an endpoint and update the database every 60 seconds:

.. code-block:: python3

   manifold_subscriber.subscribe_to_bets(username='Joe', polling_time=60, callback=foo)

Do something upon update

.. code-block:: python3

   def foo():
      pass






