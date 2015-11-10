=======
Kio CLI
=======

.. image:: https://travis-ci.org/zalando-stups/kio-cli.svg?branch=master
   :target: https://travis-ci.org/zalando-stups/kio-cli
   :alt: Build Status

.. image:: https://coveralls.io/repos/zalando-stups/kio-cli/badge.svg
   :target: https://coveralls.io/r/zalando-stups/kio-cli
   :alt: Code Coverage

.. image:: https://img.shields.io/pypi/dw/stups-kio.svg
   :target: https://pypi.python.org/pypi/stups-kio/
   :alt: PyPI Downloads

.. image:: https://img.shields.io/pypi/v/stups-kio.svg
   :target: https://pypi.python.org/pypi/stups-kio/
   :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/l/stups-kio.svg
   :target: https://pypi.python.org/pypi/stups-kio/
   :alt: License

Convenience command line tool for Kio application registry.

.. code-block:: bash

    $ sudo pip3 install --upgrade stups-kio

Usage
=====

.. code-block:: bash

    $ kio app

You can also run it locally from source:

.. code-block:: bash

    $ python3 -m kio

Running Unit Tests
==================

.. code-block:: bash

    $ python3 setup.py test --cov-html=true

Releasing
=========

.. code-block:: bash

    $ ./release.sh <NEW-VERSION>
