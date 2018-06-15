from lib import geo, utils
from _check_inputs import *


#Create logger (outputs to console and to log.txt in
logger = utils.create_logger()


# Create a Rivers object and set a river direction
rivers = geo.Rivers(df=RIVER_SHP, name_f=RIVERNAME_FIELD)
rivers.set_river_direction(dem_file=DEM_FILE, direction=CHAINAGING_DIRECTION)
rivers.df.to_file(RIVER_SHP)
# geo.Shp.save_to_shapefile_with_prj(geo_df=rivers.df,file_out=RIVER_SHP,epsg=3794)

if EMBANKMENTS_SHP:
    embankments = geo.Rivers(df=EMBANKMENTS_SHP,name_f=EMBANKMENTS_NAME_FIELD)
    embankments.set_river_direction(dem_file=DEM_FILE,direction=CHAINAGING_DIRECTION)


# Create a XSections Object (You need to specify what rivers will it lay on and which properties will it have
xsections = geo.Cross_sections(df_r=rivers,
                               profile_orientation=XSECTION_ORIENTATION,
                               chainaging_direction=CHAINAGING_DIRECTION,
                               naming_direction=CHAINAGING_DIRECTION)

if CREATION_METHOD == "auto":
    # Autocreate profiles based on specified settings
    xsections.populate_automatically(profile_density=PROFILE_DENSITY,
                                     profile_width=PROFILE_WIDTH,
                                     dem_file=DEM_FILE,
                                     interpolation_density=SAMPLING_DENSITY)

elif CREATION_METHOD == "measurements":
        # Populate xs data from line_shp (it will perform all calculations while initializing already...)
        xsections.populate_from_point_shp(df=XSECTION_SHP,
                                          profile_id_f=XSECTION_PROFILE_ID_FIELD,
                                          z_f=Z_FIELD,
                                          point_id_f=XSECTION_POINT_ID_FIELD)


elif CREATION_METHOD == "lines":
        # Populate xs data from line_shp (it will perform all calculations while initializing already...)
        xsections.populate_from_line_shp(df_l=XSECTION_SHP, profile_id_f=XSECTION_PROFILE_ID_FIELD,dem_file=DEM_FILE)


xsections.df.to_file(XSECTION_POINTS_OUT_SHP)



# Calculate internal xz chainages per profile (for xns11_file)
xsections.calculate_internal_xz_chainages_and_sort(from_centre=False)

#Calculate internal xz chainage per profile from centre
xsections.calculate_internal_xz_chainages_and_sort(from_centre=True)


###########
# RESULTS #
###########



if XNS11_OUT_TXT:
    # Export a XNS_file
    xsections.export_to_xns11_file(xns11_file=XNS11_OUT_TXT)

if XSECTION_POINTS_OUT_SHP:
    logger.debug("Saving a dataframe to {}".format(XSECTION_POINTS_OUT_SHP))
    # Export Points to a shapefile
    xsections.df.to_file(XSECTION_POINTS_OUT_SHP)
    # geo.Shp.save_to_shapefile_with_prj(geo_df=xsections.df, file_out=POINTS_OUT_SHP, epsg=3794)

if XSECTION_LINES_OUT_SHP:
    logger.debug("Saving a dataframe to {}".format(XSECTION_LINES_OUT_SHP))
    # Export XS Lines to a shapefile
    xsections.df_l.to_file(XSECTION_LINES_OUT_SHP)
    # geo.Shp.save_to_shapefile_with_prj(geo_df=xsections.df_l, file_out=LINES_OUT_SHP, epsg=3794)


if RIVER_POINT_OUT_SHP:
    rivers.point_sample_line(interpolation_density=SAMPLING_DENSITY,dem_file=DEM_FILE)
    rivers.df_p.to_file(RIVER_POINT_OUT_SHP)


if EMBANKMENTS_SHP:
    if EMBANKMENTS_POINT_OUT_SHP:
        embankments.point_sample_line(interpolation_density=SAMPLING_DENSITY,dem_file=DEM_FILE)
        embankments.df_p.to_file(EMBANKMENTS_POINT_OUT_SHP)

if PROFILES_DXF:
    xsections.export_profiles_to_dxf(PROFILES_DXF, "Icmank")

print("")
print("###########################################################################")
print("######### Xsection has finished sucessfully! Generated results are:")
for i in [XNS11_OUT_TXT,RIVER_POINT_OUT_SHP,XSECTION_POINTS_OUT_SHP,XSECTION_LINES_OUT_SHP,EMBANKMENTS_POINT_OUT_SHP]:
    if i:
        print(i)
print("###########################################################################")
print("")
