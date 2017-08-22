from inputs import *
import geopandas as gpd
import os


print(" ")
print("#################################################")
print("################ WELCOME TO XSECTION ############")
print("#################################################")
print(" ")
print("#################################################")
print("############### Version 1.0, 2017 ###############")
print("#################################################")
print("## Author: Marjan Moderc, marjan.moderc@gov.si ##")
print("#################################################")
print(" ")


print("Make sure you that all the data source are in the same projected coordinate system!"
      "\nIn order to keep program as lightweight as possible, coordinate reference cross checking is turned off!")
print("Make sure you have read the manual in README file and you understand the meaning and options of the inputs you are going to specify!")
print("")



#PERFORM ERROR CHECK OF THE INPUTS!

CREATION_METHOD = CREATION_METHOD.lower()
print("Selected CREATION_METHOD: {}\n".format(CREATION_METHOD))
if CREATION_METHOD not in ["auto","lines","measurements"]:
    raise Exception("{} is not a valid creation method! See the instructions!".format(CREATION_METHOD))


print("Selected RIVER_SHP: {}\n".format(RIVER_SHP))
if not os.path.isfile(RIVER_SHP):
    raise Exception("I can't find a shapefile {}. Make sure the file exists and is within the script's visible scope!".format(RIVER_SHP))
elif not RIVER_SHP.endswith(".shp"):
    raise Exception("Specified file doesn't have the extension *.shp! It must be a shapefile!")
else:
    df_r = gpd.read_file(RIVER_SHP)
    river_shp_fields = df_r.columns.tolist()


print("Selected RIVERNAME_FIELD: {}\n".format(RIVERNAME_FIELD))
if RIVERNAME_FIELD not in river_shp_fields:
    raise Exception("Specifed river shapefile doesn't have any column with a name {}. Pick one from the following:\n"
                "{}".format(RIVERNAME_FIELD,",".join(river_shp_fields)))


print("Selected DEM_FILE: {}\n".format(DEM_FILE))
if not os.path.isfile(DEM_FILE):
    raise Exception("I can't find a dem {}. Make sure the file exists and is within the script's visible scope!")
elif DEM_FILE.split(".")[-1].lower() not in ["tiff", "tif"]:
    raise Exception("Specified file doesn't have the extension *.tif! It must be a tiff raster!")


print("Selected XSECTION_ORIENTATION: {}\n".format(XSECTION_ORIENTATION))
if XSECTION_ORIENTATION not in ["left", "right"]:
    raise Exception("{} is not a valid profile orientation! This switch can only be left or right!".format(XSECTION_ORIENTATION))


print("Selected SAMPLING_DENSITY: {}\n".format(SAMPLING_DENSITY))
try:
    SAMPLING_DENSITY = int(SAMPLING_DENSITY)
except:
    raise Exception("Sampling density must be an full number, integer!")

if CREATION_METHOD == "auto":

    print("Selected PROFILE_WIDTH: {}\n".format(PROFILE_WIDTH))
    try:
        PROFILE_WIDTH = int(PROFILE_WIDTH)
    except:
        raise Exception("Profile width size must be an integer!")


    print("Selected PROFILE DENSITY: {}\n".format(PROFILE_DENSITY))
    try:
        PROFILE_DENSITY = int(PROFILE_DENSITY)
    except:
        raise Exception("Profile density must be an integer!")


elif CREATION_METHOD == "measurements":

    print("Selected XSECTION_SHP: {}\n".format(XSECTION_SHP))
    if not os.path.isfile(XSECTION_SHP):
        raise Exception("I can't find a shapefile {}. Make sure the file exists and is within the script's visible scope!")
    elif not XSECTION_SHP.endswith(".shp"):
        raise Exception("Specified file doesn't have the extension *.shp! It must be a shapefile!")
    else:
        xsections_shp_fields = gpd.read_file(XSECTION_SHP).columns.tolist()


    print("Selected XSECTION_PROFILE_ID_FIELD: {}\n".format(XSECTION_PROFILE_ID_FIELD))
    if XSECTION_PROFILE_ID_FIELD not in xsections_shp_fields:
        raise Exception("Specifed xsections shapefile doesn't have any column with a name {}. Pick one from the following:\n"
                    "{}".format(XSECTION_PROFILE_ID_FIELD,",".join(xsections_shp_fields)))


    print("Selected XSECTION_POINT_ID_FIELD: {}\n".format(XSECTION_POINT_ID_FIELD))
    if XSECTION_POINT_ID_FIELD not in xsections_shp_fields:
        if XSECTION_PROFILE_ID_FIELD not in xsections_shp_fields:
            raise Exception("Specifed xsections shapefile doesn't have any column with a name {}. Pick one from the following:\n"
            "{}".format(XSECTION_PROFILE_ID_FIELD, ",".join(xsections_shp_fields)))


    print("Selected Z_FIELD: {}\n".format(Z_FIELD))
    if Z_FIELD not in xsections_shp_fields:
        if Z_FIELD not in xsections_shp_fields:
            raise Exception("Specifed xsections shapefile doesn't have any column with a name {}. Pick one from the following:\n"
            "{}".format(Z_FIELD, ",".join(xsections_shp_fields)))


elif CREATION_METHOD == "lines":
    print("Selected XSECTION_SHP: {}\n".format(XSECTION_SHP))
    if not os.path.isfile(XSECTION_SHP):
        raise Exception(
            "I can't find a shapefile {}. Make sure the file exists and is within the script's visible scope!".format(XSECTION_SHP))
    elif not XSECTION_SHP.endswith(".shp"):
        raise Exception("Specified file doesn't have the extension *.shp! It must be a shapefile!")
    else:
        xsections_shp_fields = gpd.read_file(XSECTION_SHP).columns.tolist()


print("Selected XNS11_OUT file: {}\n".format(XNS11_OUT_TXT))
if not XNS11_OUT_TXT.lower().endswith("txt"):
    raise Exception("WARNING! Mike XNS11 output file must be a .txt file!")

print("Selected XSECTION_POINTS_OUT_SHP file: {}\n".format(XSECTION_POINTS_OUT_SHP))
if XSECTION_POINTS_OUT_SHP:
    if not XSECTION_POINTS_OUT_SHP.lower().endswith("shp"):
        raise Exception("WARNING! Points out file must be an ESRI .shp file!")

print("Selected XSECTION_LINES_OUT_SHP file: {}\n".format(XSECTION_LINES_OUT_SHP))
if XSECTION_LINES_OUT_SHP:
    if not XSECTION_LINES_OUT_SHP.lower().endswith("shp"):
        raise Exception("WARNING! Lines output file must be a ESRI .shp file!")

print("Selected EMBANKMENTS_POINT_OUT_SHP file: {}\n".format(EMBANKMENTS_POINT_OUT_SHP))
if EMBANKMENTS_POINT_OUT_SHP:
    if not EMBANKMENTS_POINT_OUT_SHP.lower().endswith("shp"):
        raise Exception("WARNING! Embankments output file must be a ESRI .shp file!")

print("Selected RIVER_POINT_OUT_SHP file: {}\n".format(RIVER_POINT_OUT_SHP))
if RIVER_POINT_OUT_SHP:
    if not RIVER_POINT_OUT_SHP.lower().endswith("shp"):
        raise Exception("WARNING! River point output file must be a ESRI .shp file!")



print("###########################################################################")
print("######### All input parameters are set! Performing a calculation... #######")
print("###########################################################################")

