Xsection
=======

.. figure:: docs/img/xsection-logo-blue.png
   :align: center


Xsection is a Python-written script for creating cross sectional river profiles, normally used in 1D hydraulic modelling.
The program features:

- vertex sampling of 2D shapefiles to pick their elevation values from underyling Digital Elevation Models (DEM)
- automatic setting of river and cross section direction/orientation (no need for careful manual creation anymore!)
- automatic calculation of the profile chainages according to the desired incrementation (upstream or downstream)
- conversion of the results into ASCII version of the *XNS11* geometry file from **Mike11 by DHI** software.
- different profile creation options:

  - auto-generated profiles (based on DEM and input parameters)
  - profiles from 2D Line Shapefile and DEM
  - profiles from a 3D geodetic suverying points in Shapefile



How To:
-------

For installation and usage guidelines, see `the Official documentation <http://xsection.readthedocs.io/en/latest/>`__.


To Do:
------

-  Conversion into a QGIS plugin (GUI)
-  EPSG projection equality checking

License
-------

This project is licensed under the MIT License - see the
`LICENSE.txt <https://github.com/marjanmo/xsection/blob/master/LICENSE.txt>`__
file for more details.
