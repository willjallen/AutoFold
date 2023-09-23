##########
User guide
##########


Installing APScheduler
----------------------

The preferred installation method is by using `pip <http://pypi.python.org/pypi/pip/>`_::

    $ pip install apscheduler

If you don't have pip installed, you can easily install it by downloading and running
`get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_.

If, for some reason, pip won't work, you can manually `download the APScheduler distribution
<https://pypi.python.org/pypi/APScheduler/>`_ from PyPI, extract and then install it::

    $ python setup.py install


Code examples
-------------

The source distribution contains the :file:`examples` directory where you can find many working
examples for using APScheduler in different ways. The examples can also be
`browsed online <https://github.com/agronholm/apscheduler/tree/3.x/examples/?at=master>`_.


Basic concepts
--------------

APScheduler has four kinds of components:

* triggers
* job stores
* executors
* schedulers

*Triggers* contain the scheduling logic. Each job has its own trigger which determines when the job
should be run next. Beyond their initial configuration, triggers are completely stateless.

*Job stores* house the scheduled jobs. The default job store simply keeps the jobs in memory, but
others store them in various kinds of databases. A job's data is serialized when it is saved to a
persistent job store, and deserialized when it's loaded back from it. Job stores (other than the
default one) don't keep the job data in memory, but act as middlemen for saving, loading, updating
and searching jobs in the backend. Job stores must never be shared between schedulers.

*Executors* are what handle the running of the jobs. They do this typically by submitting the
designated callable in a job to a thread or process pool. When the job is done, the executor
notifies the scheduler which then emits an appropriate event.

*Schedulers* are what bind the rest together. You typically have only one scheduler running in your
application. The application developer doesn't normally deal with the job stores, executors or
triggers directly. Instead, the scheduler provides the proper interface to handle all those.
Configuring the job stores and executors is done through the scheduler, as is adding, modifying and
removing jobs.


Choosing the right scheduler, job store(s), executor(s) and trigger(s)
----------------------------------------------------------------------

Your choice of scheduler depends mostly on your programming environment and what you'll be using
APScheduler for. Here's a quick guide for choosing a scheduler:

* :class:`~apscheduler.schedulers.blocking.BlockingScheduler`:
  use when the scheduler is the only thing running in your process
* :class:`~apscheduler.schedulers.background.BackgroundScheduler`:
  use when you're not using any of the frameworks below, and want the scheduler to run in the
  background inside your application
* :class:`~apscheduler.schedulers.asyncio.AsyncIOScheduler`:
  use if your application uses the asyncio module
* :class:`~apscheduler.schedulers.gevent.GeventScheduler`:
  use if your application uses gevent
* :class:`~apscheduler.schedulers.tornado.TornadoScheduler`:
  use if you're building a Tornado application
* :class:`~apscheduler.schedulers.twisted.TwistedScheduler`:
  use if you're building a Twisted application
* :class:`~apscheduler.schedulers.qt.QtScheduler`:
  use if you're building a Qt application

Simple enough, yes?

To pick the appropriate job store, you need to determine whether you need job persistence or not.
If you always recreate your jobs at the start of your application, then you can probably go with
the default (:class:`~apscheduler.jobstores.memory.MemoryJobStore`). But if you need your jobs to
persist over scheduler restarts or application crashes, then your choice usually boils down to what
tools are used in your programming environment. If, however, you are in the position to choose
freely, then :class:`~apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore` on a
`PostgreSQL <http://www.postgresql.org/>`_ backend is the recommended choice due to its strong data
integrity protection.

Likewise, the choice of executors is usually made for you if you use one of the frameworks above.
Otherwise, the default :class:`~apscheduler.executors.pool.ThreadPoolExecutor` should be good
enough for most purposes. If your workload involves CPU intensive operations, you should consider
using :class:`~apscheduler.executors.pool.ProcessPoolExecutor` instead to make use of multiple CPU
cores. You could even use both at once, adding the process pool executor as a secondary executor.

When you schedule a job, you need to choose a *trigger* for it. The trigger determines the logic by
which the dates/times are calculated when the job will be run. APScheduler comes with three
built-in trigger types:

* :mod:`~apscheduler.triggers.date`:
  use when you want to run the job just once at a certain point of time
* :mod:`~apscheduler.triggers.interval`:
  use when you want to run the job at fixed intervals of time
* :mod:`~apscheduler.triggers.cron`:
  use when you want to run the job periodically at certain time(s) of day

It is also possible to combine multiple triggers into one which fires either on times agreed on by
all the participating triggers, or when any of the triggers would fire. For more information, see
the documentation for :mod:`combining triggers <apscheduler.triggers.combining>`.

You can find the plugin names of each job store, executor and trigger type on their respective API
documentation pages.


.. _scheduler-config:

Configuring the scheduler
-------------------------