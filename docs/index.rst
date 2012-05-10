Welcome to the awsfabrictasks documentation!
============================================

Fabric (http://fabfile.org) tasks for Amazon Web Services with some extra utilities for Ubuntu.


Getting started
===============

Fabric
------
Learn how to use `Fabric <http://fabfile.org>`_.


The awsfab command
------------------
Fabric is great for remote execution because it allows you to run a task on any SSH-server
with the following syntax::

    $ fab -H server1,server2,server3 task1 task2

The problem with Fabric on AWS EC2 is that we do not have a static dns address
to give to ``-H``. ``awsfab`` wraps ``fab`` and allows us to use::

    $ bin/awsfab -E <Name-tag of an EC2 instance>,<Name-tag of another....> task1 task2

If your instance is not tagged with a name (the tag must be capitalized:
``Name``), you can use ``--ec2ids`` instead.


Settings
--------

See :ref:`awsfabsettigs`.


Making a fabfile.py and use awsfabrictasks
==========================================

Example fabfile.py
------------------
Create a ``fabfile.py`` just as you would with Fabric, and import tasks from
``awsfabrictasks``:

.. literalinclude:: example_fabfile.py


Using the example
-----------------
List basic information about your instances with::

    $ bin/awsfab ec2_list_instances

Start one of your existing EC2 instances (the example assumes it is tagged with
``Name="mytest"``):

    $ bin/awsfab -E mytest ec2_start_instance

Login (SSH) to the instance we just started::

    $ bin/awsfab -E mytest ec2_login

See::

    $ bin/awsfab -l

or :ref:`tasks` for more tasks.


Launch/create new EC2 instances
-------------------------------
See :ref:`examplesettings` for and example of how to setup your EC2 launch configurations.
After you have added ``EC2_LAUNCH_CONFIGS`` to your ``awsfab_settings.py``, simply run::

    $ awsfab ec2_launch_instance:<nametag>

where ``<nametag>`` is the name you want to tag your new instance with. You
will be asked to choose a config from ``EC2_LAUNCH_CONFIGS``, and to confirm
all your choices before the instance in created.


More task-examples
==================
The best examples are the provided tasks. Just browse the source, or use the
``[source]`` links in the :ref:`tasks docs (tasks)`.


Documentation
=============

.. toctree::
   :maxdepth: 2

   tasks
   api
   awsfab_settings


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
