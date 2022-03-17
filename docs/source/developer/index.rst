-------------------------
Developer's documentation
-------------------------

Hacking on existing packages
============================
The CYST framework is developed and distributed as a set of loosely-dependent packages (with the exception of cyst-core).
Thanks to the magic of pip, this is much less painful than it may seem, especially if you find yourself in a
situation when you need to do a parallel development of a subset of packages.

In this guide, we will illustrate the needed steps on the example of developing the AIF behavioral model, which at
some point will necessitate changes to the cyst-core. The example of an existing package with model is chosen to ignore
the stuff needed to set up the package itself. This is covered later in the guide.

Getting the AIF package and setting it all up
---------------------------------------------

.. tabs::

    .. tab:: Windows CMD

        ! Get Python 3.9 any way you can !

        Clone the AIF package

        .. code-block:: console

            ...> git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-models-aif.git

        Prepare and activate the virtual environment

        .. code-block:: console

            ...> cd cyst-models-aif
            ...\cyst-models-aif> python -m venv venv
            ...\cyst-models-aif> venv\Scripts\activate.bat

        Set up all the requirements. The following command will attempt to fetch the packages from both the official
        and test PYPI repositories and will also install cyst-models-aif as an editable package. This is necessary
        to enable correct loading of it by the cyst-core.

        .. code-block:: console

            (venv) ...\cyst-models-aif> pip install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) ...\cyst-models-aif> cd tests
            (venv) ...\cyst-models-aif\tests> python -m unittest

        If you see something like this, everything is ready and correctly working.

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 9 tests in 0.749s

            OK


    .. tab:: Linux shell

        ! Get Python 3.9 any way you can !

        Clone the AIF package

        .. code-block:: console

            ...$ git clone https://<username>:<token>@gitlab.ics.muni.cz/cyst/cyst-models-aif.git

        Prepare and activate the virtual environment

        .. code-block:: console

            ...$ cd cyst-models-aif
            .../cyst-models-aif$ python3 -m venv venv
            .../cyst-models-aif$ source venv/bin/activate

        Set up all the requirements. The following command will attempt to fetch the packages from both the official
        and test PYPI repositories and will also install cyst-models-aif as an editable package. This is necessary
        to enable correct loading of it by the cyst-core.

        .. code-block:: console

            (venv) .../cyst-models-aif$ pip3 install -i https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple -e .

        Now, test if everything went smooth and the package is ready for hacking.

        .. code-block:: console

            (venv) .../cyst-models-aif$ cd tests
            (venv) .../cyst-models-aif/tests$ python3 -m unittest

        If you see something like this, everything is ready and correctly working.

        .. code-block:: console

            ----------------------------------------------------------------------
            Ran 9 tests in 0.749s

            OK

    .. tab:: PyCharm

        This is using the PyCharm



Where?
======

How?
====
