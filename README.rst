xsection
=======

A Python library for creation Mike11 by DHI cross sections files from ESRI Shapefiles and DEM rasters.


About
-----


Demands:

All dataset must be in the same projected coordinate system. Make sure to perform projections before any calculations!

INPUTS:
- river shapefile in projected coordinate system with an existing atrubute field with river names
- dem file covering the whole area of interest (at least for figuring out river direction!)
- cross section files
- longitudinal lines if interest (embankments,...) in separate shapefile



xsection is a python written library converting surveying point measurements
or DEM raster data into cross sections in a format, that is usually required in 1D river flood modelling software.

Library currently supports generation of the river profiles with the Program supports two most commonly used transformating methods for 2D
point transformations:

- **triangle:** affine 6-parametric 2D triangle transformation, based on 899 `Slovenian reference points <http://www.e-prostor.gov.si/zbirke-prostorskih-podatkov/drzavni-koordinatni-sistem/horizontalni-drzavni-koordinatni-sistem-d96tm/d96tm/transformacijski-parametri/>`__ (best accuracy)

- **24regions:** a simplified 4-parametric 2D transformation, where parameteres are precalculated for 24 Slovenian regions (`more info <http://www.e-prostor.gov.si/zbirke-prostorskih-podatkov/drzavni-koordinatni-sistem/horizontalni-drzavni-koordinatni-sistem-d96tm/d96tm/transformacijski-parametri/>`__)

Program contains spatailly precalculated regional transformation
parameters, but also allows a manual specification of transformation
parameters for both available methods.

**IMPORTANT NOTICE:** Library is primarily intended and therefore mostly
suitable for slovenian coordinate systems d48GK (espg: 3912) and d96TM
(epsg: 3794)!

For more theoretical background, see the official GURS
`webpage <http://www.e-prostor.gov.si/zbirke-prostorskih-podatkov/drzavni-koordinatni-sistem/transformacija-v-novi-koordinatni-sistem/>`__.

Installation:
-------------

**Installing on Linux:**

Library is available on PyPi repository, so it can easily be installed with pip:

::

    pip install xsection

Mind that prerequisites for such a simplicity of course include having Python (2 or 3) and pip installed on your system.
Library depends on some powerful, but sometimes hard-to-install Python libraries (numpy,scipy,pandas,geopandas),
that themselves need some (standard) geospatial system dependencies (`GEOS <https://trac.osgeo.org/geos/>`__,
`GDAL <http://www.gdal.org/>`__), all installable by ``sudo apt-get ...``. For more on installing those on Linux, see
`this page <https://docs.djangoproject.com/en/1.11/ref/contrib/gis/install/geolibs/>`__.

**Installing on Windows:**

Installing xsection on Windows is straightforward, but it takes a bit more steps:

-  First, if you don't even have a Python installed,
   the easiest way to setup the proper Python environment and its dependencies is by installing `Anaconda <https://www.continuum.io/downloads>`__.
   This is a Python distibution that ships with most of the popular libraries out of the box. Make sure to add
   ``conda`` and ``python`` to ``path`` system environment variable.
-  Despite Anaconda's awesomeness, libraries that require non-python GEOS and GDAL are best
   separetely installed by downloading the .whl file that matches your python and system version from `this repo <http://www.lfd.uci.edu/~gohlke/pythonlibs/>`__.
   Download appropriate wheels for **GDAL, Fiona and Shapely** and install them with ``pip install *.whl``.
-  Compliling non-pure Python dependencies on Windows also requires `Visual C++ Build Tools package <http://landinghub.visualstudio.com/visual-cpp-build-tools>`__
-  Then you can install xsection with pip as in the above, Linux example.



Usage:
------

1. Python API
~~~~~~~~~~~~~

**1.1. Transforming python lists of points:**

.. code:: python

    from xsection import SloTransformation

    # List of point that you want converted into d96 via several methods
    D48_POINTS = [(500000,100000),(0,0),(650000,200000)]


    # Initialize a Triangle Transformation object
    ts_triangle = SloTransformation(from_crs="d48",method="triangle")

    # Initialize a 24regions transformation object
    ts_24region = SloTransformation(from_crs="d48",method="24regions")

    # Initialize a affine transformation object with your own parameters
    ts_triangle_manual = SloTransformation(from_crs="d48",method="triangle",params="1.00001;0.000040647;-374.668;-0.00002241;1.000006;494.8428".split(";"))

    # Note, that seemingly redundant recreation of different transformations as a separate object comes very handy, when you want to
    # transform many files/lists at once, so you don't have to perform the expensive transformation object initialization
    # for every file/list separately.


    # Once you have transformation object initialized, you can use it's .transform() method to transform old points into
    # new points quite cheaply:
    print("Triangle transformation (affine 6parametric):")
    print(ts_triangle.transform(D48_POINTS))
    print("24regions transformation (4parametric):")
    print( ts_24region.transform(D48_POINTS))
    print("Triangle transformation with custom parameters:")
    print(ts_triangle_manual.transform(D48_POINTS))

**1.2. Transforming files with python**

.. code:: python

    from xsection import shp_transformation,csv_transformation
    from xsection.utils import recognize_csv_separator,check_for_csv_header
    import geopandas as gpd
    import pandas as pd


    # SHAPEFILES:

    #read shapefile into GeoDataFrame and transform it and save it as into new shapefile
    df_in = gpd.read_file("shapefile_in_d48.shp")
    df_out = shp_transformation(df_in,from_crs="d48",method="24regions")
    df_out.to_file("shapefile_in_d96.shp")


    # ASCII CSVS:
    csv_file = "terrain_measurements_in_d48.csv"

    sep = recognize_csv_separator(csv_file) #guess the separator type
    header = check_for_csv_header(csv_file) #check if file has header

    #read csv file into DataFrame, transform them by triangle method with custom parameters and save it to csv.
    csv_in = pd.read_csv(csv_file, sep=sep, header=header)
    csv_out = csv_transformation(df_in=csv_in, from_crs="d48", method="triangle", params="1.00001;0.000040647;-374.668;-0.00002241;1.000006;494.8428".split(";"))
    csv_out.to_file("terrain_measurements_in_d96.csv")

**1.3. Using low level functions to transform point-by-point**

.. code:: python

    from xsection import trans_2R_4params,trans_2R_6params

    D48_POINTS = [(500000,100000), (0,0), (650000,200000)]

    for point in D48_POINTS:
        # 4parametric transformation with params: scale,rotation,trans_x,trans_y
        x, y = trans_2R_4params(point[0], point[1], params=[0.9999873226,0.0009846750,378.755,-493.382])
        print(x, y)
        # 6parametric transformation with params a,b,c,d,e,f
        x, y = trans_2R_6params(point[0], point[1], params=[1.00001,0.000040647,-374.668,-0.00002241,1.000006,494.8428])
        print(x, y)

2. Command Line Utility
~~~~~~~~~~~~~~~~~~~~~~~

Transformations on a file (directory) level are best carried out by
using the command line utility, that automatically ships and installs
with the library. Utility can be invoked with the command ``sitra`` in
your shell. Calling ``sitra --help`` brings up commands overview with
available options:

::

    $ sitra --help
    Usage: sitra [OPTIONS] FILE_IN [FILE_OUT]

    Options:
      --to_crs [d48|d96]             Coordinate system to transform your data into
                                     [required]
      --method [triangle|24regions]  Transformation method to be used
      --params TEXT                  Optional argument: semicolon separated manual
                                     parameters, required for each transformation
                                     method (24regions:4params,
                                     triangle:6params,...
      --help                         Show this message and exit.

**2.1. RULES AND DEFAULT CMD BEHAVIOUR**

-  ``FILE_IN`` is a mandatory input. Valid input file type are ESRI
   Shapefiles (\*.shp) or plain ASCII csv files (\*.csv, \*.txt)
-  If no outfile name is given as input ``FILE_OUT``, the same filename
   with extension \_{crs} will be used automaticaly! (e.g.:
   shapefile.shp --> shapefile\_d96.shp)
-  If input file is ASCII type, program will try to autodetect field for
   easting and northing by checking the column values range and column
   names
-  If input file is type \*.shp, program check its EPSG code and will
   complain if input's crs is not reverse of the desired crs! No such
   test can be performed with ascii input types
-  parameter ``--to_crs`` is mandatory and can only be
   ``d96``\ (=EPSG:3794) or ``d48`` (=EPSG:3912).
-  default value for ``--method`` is ``triangle`` (best accuracy)
-  default value for ``--params`` is ``None`` (they get calculated
   automatically - best accuracy)
-  in case you want to perform transformation with your own
   transformation parameters, you have to specify them manually with an
   option ``--params`` in a following style:

   -  for affine triangle transformation (=2R-6parameters
      transformation):
      ::

      ... -method=triangular --params="scale_x;rotation_y;translation_x;rotation_x;scale_y;translation_y" ...

   -  for simplified 2R-4parameters transformation (which is used in
      24regions transformation)

      ::

          ... --method=24regions --params="scale;CCW_rotation[dec °];translation_x[m];translation_y[m]" ...

   -  note the apostrophe ``"`` or ``'`` around the semicolon-separated
      values in both cases! See the actual examples below!

**2.2. CMD EXAMPLES**:

1. A minimal example usage for transforming
   shapefile with default settings (--method=triangle) will save result into 'old\_shapefile\_d96.shp'

   ::

    sitra --to_crs=d96 old_shapefile.shp

2. Another example, this time with --method=24regions and specified
   output:

   ::

    sitra --to_crs=d96 --method=24regions old_shapefile.shp new_shapefile.shp

3. Example with csv file (note that no csv format specification is
   needed --> separator and x,y,z columns are automatically guessed!):

   ::

    sitra --to_crs=d48 --method=24regions Cool_points.csv Back_to_MariaTheresa_times.csv

4. In all the above examples the transformation parameters were
   automatically calculated based on a chosen method and point location.
   But you can also specify your own parameters, but you have to make
   sure you pass correct number of parameters in right order for the
   corresponding transformation method. Here is an example for custom
   affine 6-parametric 2R transformation (~triangle) d48-->d96
   tranformation. (*Parameters are given in order a,b,c,d,e,f, based on
   this `standard naming
   convention <http://geocoordinateconverter.tk/>`__*):

   ::

    sitra --to_crs=d96 --method=triangle --params='1.00001;0.000040647;-374.668;-0.00002241;1.000006;494.8428' old_points.csv new_points.csv

5. For a 4-parameteric 2R transformation (~24regions) from d96 to back
   to d48 using your own transformation parameters, do the following:
   (*example parameters based on a region No.1 of the `d96-->d48
   24region
   transformation <http://www.e-prostor.gov.si/fileadmin/ogs/drz_parametri/24_regij_PARAMETRI_D96-D48.pdf>`__)*
   :

   ::

       sitra --to_crs=d96 --method=24regions --params="0.9999873226;0.0009846750;378.755;-493.382" old_points.csv new_points.csv

TODO:
-----

-  Adding GUI as a QGIS plugin

Authors
-------

-  **Marjan Moderc**, ARSO, Slovenia - *the coding wizardy* -
   `GitHub <https://github.com/marjanmo>`__


License
-------

This project is licensed under the MIT License - see the
`LICENSE.txt <https://github.com/marjanmo/xsection/blob/master/LICENSE.txt>`__
file for details
