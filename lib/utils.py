# coding=utf-8
import pandas as pd

import os
import logging
from datetime import datetime
from osgeo import gdal, ogr, osr
from fiona.crs import from_epsg,from_string,to_string
import subprocess


HOMEDIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

logger = logging.getLogger('root')  # default logger object to write all messages into
pd.options.mode.chained_assignment = None  # disable annoying pandas warnings about chained pizdarija



def create_logger(name='root'):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    FORMAT = "%(levelname)-8s: %(message)-100s --- [%(asctime)s: %(module)s.%(funcName)s, line:%(lineno)s]"

    formatter = logging.Formatter(FORMAT, datefmt='%H:%M:%S')

    # HANDLER FOR FILE OUTPUT (WITH THE NAME OF THE CALLING TOPMOST SCRIPT
    logfile = os.path.join(HOMEDIR,"log.txt")
    fh = logging.FileHandler(logfile, mode='w')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    #HANDLER FOR CONSOLE OUTPUT
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

def roundTime(date=None, minutes=60):
    """Round a datetime object to a multiple of a timedelta
    dt : datetime.datetime object, default now.
    dateDelta : timedelta object, we round to a multiple of this, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
            Stijn Nevens 2014 - Changed to use only datetime objects as variables
    """

    if not isinstance(date,datetime):
        raise TypeError("Date mora bit podan v datetime formatu, ne pa v stringu! Posrkbi za pretvorbo prehodno!")

    return datetime(date.year, date.month, date.day, date.hour, minutes*(date.minute // minutes))

def print_full_df(x):
    pd.set_option('display.max_rows', len(x.index))
    pd.set_option('display.max_columns', len(x.columns))
    print(x)
    pd.reset_option('display.max_rows')
    pd.reset_option('display.max_columns')

def find_uniform_df_cols(df):

    #returns a lost of df columns that have all the same values in it.
    df_copy = df.copy(deep=True)
    if "geometry" in df_copy.columns:
        del df_copy["geometry"] #neki hashtable ga jebe, ce je geodataframe

    nunique = df_copy.apply(pd.Series.nunique)
    unique_cols = nunique[nunique > 1].index
    df_copy = df_copy.drop(unique_cols, axis=1)

    return df_copy.columns.tolist()

def check_epsg_equality(rasters=(),vectors=()):
    logger.info("Checking the coordinate system consistency of input data ...")

    epsgs = {}

    for raster in rasters:
        if raster is not None:
            epsgs[raster]=gdal_get_epsg(raster)

    for shp in vectors:
        if shp is not None:
            epsgs[shp] = ogr_get_epsg(shp)

    if not len(set(epsgs.values())) ==1 or None in epsgs.values():
        raise Exception("EPSG (e)quality check for the specified datasets failed. Below you can find the results:\n{}".format("\n".join(["{}: {}".format(k,v) for k,v in epsgs.items()]))
)
    else:
        return epsgs.values()[0]

def gdal_get_epsg(raster):
    #CESKA PARSING METODA FTW!
    a = str(subprocess.check_output("gdalinfo {}".format(raster),shell=True))
    a = a.split('AUTHORITY["EPSG","')[-1].split('"]]')[0]
    #STAR NACIN! (OBOJE GRDO ZA ZNORT...)
    # print(a)
    # a = a.split("\n")
    # a = [x for x in a if "AUTHORITY" in x][-1]
    # a = a.split('"')[-2]
    return int(a)

def ogr_get_epsg(shapefile):

    if isinstance(shapefile,str):
        prj_file = os.path.splitext(os.path.abspath(shapefile))[0]+".prj"
        if not os.path.isfile(prj_file):
            raise Exception("Given Shapefile {} has no prj file attached! Make sure have the georeferencing information attached to the shapefile!".format(shapefile))

        with open(prj_file,"r") as f:
            prj_txt = f.read()
            epsg = esri_to_epsg(prj_txt)

    else:
        # This means, the input is already inmemory (e.g. geodataframe). Extract it's proj4 information
        epsg = proj4_to_epsg(to_string(shapefile.crs))

    return epsg

def esri_to_epsg(wkt_txt):
    srs = osr.SpatialReference()
    srs.ImportFromESRI([wkt_txt])
    srs.AutoIdentifyEPSG()
    epsg = srs.GetAuthorityCode(None)

    if not epsg:  # try also with wkt web service recognition
            raise Exception("Couldn't find a epsg code for the prj string {}!".format(wkt_txt))

    return epsg

def proj4_to_epsg(prj_txt):
    #Code that checks prj txt file and returns epsg code

    srs = osr.SpatialReference()
    srs.ImportFromProj4(prj_txt)
    proj4_txt = srs.ExportToProj4().strip()  # Silly, but only for the sake of ordering projection

    #list of common proj4 files (to avoid using internet too much ---> slow!) Lahko dodas nove s pomocjo "gedit /usr/share/proj/epsg"

    #list of common
    proj4_dict = {
        "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9999 +x_0=500000 +y_0=-5000000 +ellps=bessel +towgs84=682,-203,480,0,0,0,0 +units=m +no_defs": 3912,
        "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9999 +x_0=500000 +y_0=-5000000 +ellps=bessel +units=m +no_defs": 3912,
        "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9999 +x_0=500000 +y_0=-5000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs": 3794,
        "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9999 +x_0=500000 +y_0=-5000000 +ellps=GRS80 +units=m +no_defs": 3794,
        "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs": 3857,
        "+proj=longlat +datum=WGS84 +no_defs": 4326}


    # First check if projection is in the common projections list
    if proj4_txt in proj4_dict.keys():
        epsg = proj4_dict[proj4_txt]

    else:
        # try to find its
        wkt_txt = srs.ExportToWkt()  # export to wkt format
        epsg = esri_to_epsg(wkt_txt)

    return epsg

def ogr2ogr(file_in=None,file_out=None,epsg_in=None,epsg_out=None):
    if not file_out:
        ime,ext = os.path.splitext(os.path.abspath(file_in))
        file_out = ime + "_{}".format(epsg_out)+ext

    cmd = 'ogr2ogr -f "ESRI Shapefile" -s_srs EPSG:{} -t_srs EPSG:{} {} {}'.format(epsg_in,epsg_out,file_in,file_out)
    subprocess.check_output(cmd, shell=True)

    return file_out

def gdalwarp(file_in=None,file_out=None,epsg_in=None,epsg_out=None):
    if not file_out:
        ime,ext = os.path.splitext(os.path.abspath(file_in))
        file_out = ime + "_{}".format(epsg_out)+ext

    cmd = "gdalwarp -s_srs EPSG:{} -t_srs EPSG:{} {} {}".format(epsg_in,epsg_out,file_in,file_out)
    subprocess.check_output(cmd, shell=True)

    return file_out










