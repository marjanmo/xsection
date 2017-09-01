=============
Installation
=============


* Make sure you have ``conda`` installed and your Python in virtual environment is ready to work with geospatial libraries.
  If not sure, see a detailed instructions in this `walkthrough`_.


* In your terminal, ``cd`` into a place where you want Xsection to reside and download the source code with ``git clone https://github.com/marjanmo/xsection.git`` or,
  if you don't have git, just manually download and extract the ZIP version of the code from the project's `github`_ page (green button!).

* Create a new, dedicated virtual enviroment with conda:

::

    conda create -n xsection python=3.5

* Activate a freshly created dedicated virtual environment by ``source activate xsection`` (skip a word ``source`` on Windows).
  This will add a ``(xsection)`` at the beginning of your command line, signalling that you are using this virtual env. Install
  needed libraries:

::

    conda install -c conda-forge geopandas natsort scipy



* Modify the ``inputs.py`` file in a project's root directory to populate set the input parameters. For more, see the docs.


* Now you are free to run the script with with activated virtual environment:

::

    python xsection.py




















.. _walkthrough: https://gist.github.com/marjanmo/66a14b3cc475c6e35f279a297d98c825
.. _github: https://github.com/marjanmo/xsection
.. _conda: https://conda.io/miniconda.html
