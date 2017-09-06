=============
Installation
=============


* Make sure you have ``conda`` and system dependencies installed and your Python is properly set up.
  If not sure, see a detailed instructions in this `walkthrough`_ (the **System requirements** part).


* In your terminal, ``cd`` into a place where you want Xsection to reside and download the source code with ``git clone https://github.com/marjanmo/xsection.git`` or,
  if you don't have git, just manually download and extract the ZIP version of the code from the project's `github`_ page (green button!).

* Create a new, dedicated conda virtual enviroment, named *xsection*:

::

    conda create -n xsection python=3.5

* Activate a freshly created dedicated virtual environment by ``source activate xsection`` (skip a word ``source`` on Windows).
  This will add a ``(xsection)`` at the beginning of your command line, signalling that you are using this virtual env.

* **ONLY FOR WINDOWS:** If you are using Windows, you will first have to install GDAL, Fiona and Shapely as a *.whl* file.
  See the above mentioned `walkthrough`_ (the **Geospatial Python libraries** part).

* Install the required Python libraries (and its dependencies) with conda:

::

    conda install -c conda-forge geopandas natsort scipy


The installation process itself should now be completed. For program usage, see the chapter **Running Xsection** of this
documentation.



.. _walkthrough: https://gist.github.com/marjanmo/66a14b3cc475c6e35f279a297d98c825
.. _github: https://github.com/marjanmo/xsection
.. _conda: https://conda.io/miniconda.html
