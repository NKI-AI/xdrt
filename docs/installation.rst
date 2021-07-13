.. highlight:: shell

============
Installation
============
In this document the installation instructions for XDRT are detailed. XDRT is known to work on Windows, OS X and Linux.
Each OS has a few different installation requirements, detailed below.

Prerequisites
-------------
XDRT uses a C++ module to decompress the data, and requires a compiler to work. The instructions below are known to
work, if you have an alternative approach and would like it added to the documentation, please create an `issue`_, or
better, create a pull request.

Windows
^^^^^^^
Compiling on Windows is known to work with `cmake`_ and `Microsoft Visual Studio`_. Ensure that :code:`cmake` is in
your path when installing XDRT.

OS X
^^^^
Install :code:`cmake` from brew.

Linux
^^^^^
Install :code:`cmake` and the build tools for your Linux distribution.


Install from PyPi
-----------------

To install XDR Toolkit, run this command in your terminal:

.. code-block:: console

    pip install xdrt

This is the preferred method to install XDR Toolkit, as it will always install the most recent stable release.


Install from sources
--------------------

The sources for XDR Toolkit can be downloaded from the `Github repo`_. Start by cloning the repository:

.. code-block:: console

    git clone git://github.com/NKI-AI/xdrt

Once you have a copy of the source, you can install it with:

.. code-block:: console

    python setup.py install

This will require that you have `cmake`_ installed. Check the documentation of your operating system, or create
an `issue`_, so we can improve the documentation.


.. _Github repo: https://github.com/NKI-AI/xdrt
.. _issue: https://github.com/NKI-AI/xdrt/issues
.. _cmake: https://cmake.org/download/
.. _Microsoft Visual Studio: https://visualstudio.microsoft.com/downloads/
