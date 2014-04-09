# awsfabrictasks

Fabric tasks for Amazon Web Services.

## Docs
http://readthedocs.org/docs/awsfabrictasks/en/latest/

## Use the wiki
The [Wiki](https://github.com/espenak/awsfabrictasks/wiki) is the perfect place to share your own solutions with other users.

## Issues/contribute
Report any issues at the github project page, and feel free to add your own
guides/experiences to the wiki, and to contribute changes using pull requests.

## History
You can of course just browse the git history, however we track major changes in ``HISTORY.rst``.


# Developing awsfabrictasks

## Setting up the development enviroment
You may need to install virtualenv:

    $ pip install virtualenv

Create a virtualenv:

    $ virtualenv venv

Activate the virtualenv in the current shell:

    $ source venv/bin/activate

Install the dependencies:

    $ pip install -r requirements.txt


## Running the tests
Once you have created a development environment, run the tests with::

    $ python setup.py nosetests

For more details, use:

    $ python setup.py nosetests --verbosity=2

Note that you have to source ``venv/bin/activate`` once for each shell instance
where you want to run the tests.


## Building the docs
Make sure you have activated the virtualenv. Then run:

    $ fab docs

Open ``build/docs/index.html`` in a browser.
