=============
Installation
=============


* Make sure you have ``conda`` installed and your system is ready to work with geospatial Python. In case you need help,
  see a detailed instructions in this `walkthrough`_.


* In your terminal, ``cd`` into a place where you want Xsection to reside and download the source code with ``git clone https://github.com/marjanmo/xsection.git`` or,
  if you don't have git, just manually download and extract the ZIP version of the code from the project's `github`_ page (green button!).


* ``cd`` into the project's root folder and create a new conda virtual environment by typing:

::

    conda create -n xsection -f environment.yml


* Activate a freshly created dedicated virtual environment by ``source activate xsection`` (skip a word ``source`` on Windows).
  This will add a ``(xsection)`` at the beginning of your command line, signalling that you are using this virtual env.


* Modify the ``inputs.py`` file in a project's root directory to populate set the input parameters. For more, see the docs.


* Now you are free to run the script with your settings from within a independent virtual environment:

::

    python xsection.py




















.. _walkthrough: https://gist.github.com/marjanmo/66a14b3cc475c6e35f279a297d98c825
.. _github: https://github.com/marjanmo/xsection
.. _conda: https://conda.io/miniconda.html
