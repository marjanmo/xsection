####### INPUT PARAMETERS LIST #####################

# RIVER SHAPEFILE
# Specify the location of the shapefile (*.shp!), representing your river branches:
RIVER_SHP = "sample_data/Rivers_sample.shp"
# Specify the column name, containing the names of the rivers in river shapefiles!
RIVERNAME_FIELD = "ime"

# Specify the desired general direction of the increasing chainages (upstream or downstream)
CHAINAGING_DIRECTION = "downstream"    #downstream/upstream

# DEM FILE
# Specify a .tiff DEM file covering the desired area! It is neccessary for the river directioning!
DEM_FILE = "sample_data/DEM_sample.tif"

# EMBANKMENTS
# Optional shapefile for any additional lines that you would like to have point sampled (result will be point file)
EMBANKMENTS_SHP = "sample_data/Embankments_sample.shp"
# Specify the column name, containing the names of the embankments in embankment shapefiles!
EMBANKMENTS_NAME_FIELD = "id"

#CROSS SECTIONS
# Specify the desired point sampling density for all the cases when it's needed (embankments, profiles, rivers,...). Defaults to 1m:
SAMPLING_DENSITY = 1

# Specify the desired profile orientation. Defaults to left
XSECTION_ORIENTATION = "left"    #left/right

# Specify internal chainage. If internal chainage should be calculated from centre or from frist point
CENTRAL_XSECTION_XZ_CHAINAGE = True

# Creation method
# Specify the desired profile creation method! Possible options: [auto/lines/measurements] --> see manual for more!
CREATION_METHOD = "lines"   #auto/lines/measurements

# PICK ONLY ONE!
if CREATION_METHOD == "auto":

    # Specify the desired distance between the autogenerated profiles [in meters]. Defaults to 200m
    PROFILE_DENSITY = 200

    # Specify the desired width of the autogenerated profiles [in meters]. Defaults to 100m
    PROFILE_WIDTH = 100

if CREATION_METHOD == "lines":
    # Specify the location of the LineString shapefile (*.shp!), representing locations of desired cross sections:
    XSECTION_SHP = "sample_data/Profiles_sample.shp"

    # Optional! Specify the column name, containing the names of the profiles in cross section shapefiles. Set to None if
    # you want Xsection to autogenerate dummy names!
    XSECTION_PROFILE_ID_FIELD = None

if CREATION_METHOD == "measurements":
    # Specify the location of the Point shapefile (*.shp!), representing locations of the profile measurements.
    XSECTION_SHP = "sample_data/Geodetic_survey_sample.shp"

    # Specify the column name, containing the names of the profiles in cross section shapefiles.
    XSECTION_PROFILE_ID_FIELD = "profile_id"

    # Specify the column name, containing the consecutive number of the points within the same profile
    XSECTION_POINT_ID_FIELD = "id"

    # Specify the column name, containing the height of the measured point
    Z_FIELD= "z"

# RESULT FILES - ALL ARE OPTIONAL!
# Specify the absolute path of the Mike 11 XNS import cross section_file! (defaults to xns11_ready.txt)
XNS11_OUT_TXT = "sample_data/Result_Mike_xns11_ready.txt"

# Specify optional point sampling of the riverlines...
RIVER_POINT_OUT_SHP = "sample_data/Result_river_point.shp"

# Specify the absolute path of the result point file of the point sampled embankments file
EMBANKMENTS_POINT_OUT_SHP = "sample_data/Result_embankment_point.shp"

# Specify the absolute path of the result XNS point(or lines) shapefile if you want it! (defaults to None)
XSECTION_POINTS_OUT_SHP = "sample_data/Result_profiles_points_points.shp"
XSECTION_LINES_OUT_SHP = "sample_data/Result_profiles_lines_points.shp"

####### END OF INPUT PARAMETERS LIST #####################