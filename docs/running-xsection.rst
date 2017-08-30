----------------
Running Xsection
----------------

A typical workflow for profile creation with Xsection looks like this:

**1. Collecting and preparing DEM, rivers and embankments in GIS**
    - Creating a DEM file
    - Collecting or hand-drawing rivers and embankments in their own shapefile
    - Making sure all the spatial data are saved in the same projected cartesian coordinate system
      (hint: WGS84 is **NOT** a projected coordinate system!)

**2. Collection and preparing cross sectional data in GIS**

    This step depends on your chosen ``CREATION_METHOD``:
    - Converting survey point data into a properly defined shapefile (LINES) or
    - Hand-drawing cross section lines in it's own shapefile (MEASUREMENTS) or
    - Thinking about the best ``PROFILE_WIDTH`` and ``PROFILE_DENSITY`` settings (AUTO)


**3. Filling out the ``ìnputs.py`` to tell the Xsection about your input data and settings**

   You can find a file in a root directory of the project.

   .. figure:: img/inputs.png
      :align: center

      Think of ``inputs.py`` as an fill out form for the program

**4. Running a script**

Once you are happy with the input parameters in ``inputs.py`` you are free to run Xsection. Remember to run it
with a correct Python interpreter (= activate virtual environment)!

::

    cd xsection_root_dir
    activate xsection               #(or source activate xsection  on Linux)
    python xsection.py


**5. Check for any error messages in terminal or in log.txt**

Xsection will error-check your input parameters and will complain in case of any illogical choices, such as:

    - wrong data types (e.g. not using .tif or .shp format as an input or output file)
    - wrong Shapefile types (e.g. LineString when it should be a Point)
    - non-existing files or shapefile fields
    - ...
