
####### INPUT PARAMETERS LIST #####################

# 1. Creation method
# 1. Specify the desired profile creation method! Possible options: [auto/lines/measurements]
CREATION_METHOD = "auto"   #auto/lines/measurements

# 2. RIVER SHAPEFILE
# 2.1. Specify the location of the shapefile (*.shp!), representing your river branches:
RIVER_SHP = "/home/marjan/arso/frisco/static/shp_source/Dragonja_reke_d96.shp"
# 2.2. Specify the column name, containing the names of the rivers in river shapefiles!
RIVERNAME_FIELD = "river"

# 3. DEM FILE
# 3. Specify a .tiff DEM file covering the desired area! It is neccessary for the river directioning!
DEM_FILE = "/media/marjan/Delo/DMR_IZSEKI/Dragonja/Dragonja_20m.tif"

# Optional shapefile for any additional lines that you would like to have point sampled (result will be point file)
EMBANKMENTS_SHP = None
# 2.2. Specify the column name, containing the names of the embankments in embankment shapefiles!
EMBANKMENTS_NAME_FIELD = "name"

# Specify the desired point sampling density for all the cases when it's needed (embankments, profiles, rivers,...). Defaults to 1m:
SAMPLING_DENSITY = 1

# 4.2. Specify the desired general direction of the increasing chainages (upstream or downstream)
CHAINAGING_DIRECTION = "downstream"    #downstream/upstream


# 4. profile orientation and chainaging direction
# 4.1. Specify the desired profile orientation. Defaults to left
XSECTION_ORIENTATION = "left"    #left/right


#PICK ONLY ONE
#4.2. CREATION METHOD == "auto":
if CREATION_METHOD == "auto":

    # Specify the desired distance between the autogenerated profiles [in meters]. Defaults to 200m
    PROFILE_DENSITY = 200

    # Specify the desired width of the autogenerated profiles [in meters]. Defaults to 100m
    PROFILE_WIDTH = 100


# 4.2. CREATION_METHOD == "measurements":
if CREATION_METHOD == "measurements":
    # Specify the location of the Point shapefile (*.shp!), representing locations of the profile measurements.
    XSECTION_SHP = "/home/marjan/arso/frisco/clanek/test_model/Sotla_measurements.shp"

    # Specify the column name, containing the names of the profiles in cross section shapefiles.
    XSECTION_PROFILE_ID_FIELD = "profile_id"

    # Specify the column name, containing the consecutive number of the points within the same profile
    XSECTION_POINT_ID_FIELD = "point_id"

    # Specify the column name, containing the height of the measured point
    Z_FIELD= "z_LAS"

# 4.2. CREATION_METHOD == "lines":
if CREATION_METHOD == "lines":
    # Specify the location of the LineString shapefile (*.shp!), representing locations of desired cross sections:
    XSECTION_SHP = "/home/marjan/arso/frisco/clanek/test_model/Sotla_profili.shp"


# 5. RESULT FILES - ALL ARE OPTIONAL!
# Specify optional point sampling of the riverlines...
RIVER_POINT_OUT_SHP = "/home/marjan/arso/frisco/static/shp_source/Dragonja_reke_d96_vzdolzni.shp"

# Specify the absolute path of the result point file of the point sampled embankments file
EMBANKMENTS_POINT_OUT_SHP = None

# 5.1. Specify the absolute path of the Mike 11 XNS import cross section_file! (defaults to xns11_ready.txt)
XNS11_OUT_TXT = "Mike11_xns_ready.txt"

# 5.2. Specify the absolute path of the result XNS point(or lines) shapefile if you want it! (defaults to None)
XSECTION_POINTS_OUT_SHP = "/home/marjan/arso/frisco/static/shp_source/Dragonja_profili_d96_test_points.shp"
XSECTION_LINES_OUT_SHP = "/home/marjan/arso/frisco/static/shp_source/Dragonja_profili_d96_test_lines.shp"



####### END OF INPUT PARAMETERS LIST #####################