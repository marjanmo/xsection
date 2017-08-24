============
Installation
============


* In order to enjoy the functionality of the project without interferring with your other python projects, it is best
to run the scripts though its own `conda`_ virtual environment.If you have never worked with `conda`_ or geospatial
libraries (like GDAL) before, make sure to setup your the environment according to this `walkthrough`_. It might be a
bit of a pain to setup everyting at first, especially on Windows, but most of the steps are one-time-only installations
and will get your system ready for all sorts of other awesome github and/or geospatial stuff from all around the internet.


* Download the code to your computer with ``git clone https://github.com/marjanmo/xsection.git``  or,
if you don't have git, download and extract the ZIP version of the code from the project's `github`_ page.


* In your terminal, move into the project's root folder and create a new conda virtual environment by typing:

::

    conda env create -n xsection -f environment.yml


* Activate a freshly created dedicated virtual environment by ``source activate xsection`` (skip a word ``source`` on
Windows). This will ad a ``(xsection)`` at the beginning of your command line, signalling which virtual env are you using.

* Modify the inputs.py file in order to set the running parameters. For more, see :ref:`usage`.

* Now you are free to run the script with your settings from within a independent virtual environment:

::

    python xsection.py






















.. _walkthrough: https://gist.github.com/marjanmo/66a14b3cc475c6e35f279a297d98c825
.. _github: https://github.com/marjanmo/xsection
.. _conda: https://conda.io/miniconda.html
