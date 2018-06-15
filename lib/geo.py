from __future__ import print_function
from . import utils
import logging
import os
from datetime import datetime
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString
from osgeo import gdal, ogr, osr
from shapely.ops import linemerge
from scipy import stats, spatial
import math
from math import sin, cos, radians, pi
from dxfwrite import DXFEngine as dxf
from natsort import natsorted, index_natsorted, order_by_index

logger = logging.getLogger('root')  # default logger object to write all messages into


HOMEDIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

class Rivers():

    # Default attributes to be used when object is initialized from other sources
    z_f = "z" #kako bo ime fieldu z visino
    point_id_f = "point_id" #kako bo ime fieldu z tockami

    def __init__(self, df, name_f):
        if isinstance(df, str):
            self.df = gpd.read_file(df)
        else:
            self.df = df

        # Default is line, obviously
        self.df_p = None #Make version for points as well, for point sampling purposes...

        self.name_f = name_f
        self.direction = None

    def set_river_direction(self, direction="downstream", autoroute=False, dem_file="DEM.tif"):

        logger.debug("Setting rivers direction to {} by using dem {}...".format(direction, dem_file))

        direction = direction.lower()

        self.df["direction"] = None  # add direction column
        self.df["first"] = None
        self.df["last"] = None
        # find downstream lines (== having first point higher than the last)
        for river in self.df.index.tolist():
            river_geom = self.df.ix[river, "geometry"]
            if autoroute:
                logger.debug("Autorouting points for river {} ...".format(river))
                # Postroji tocke eno za drugo
                river_geom = LineString(
                    Points.autoroute_points(list(river_geom.coords), start=list(river_geom.coords)[0]))
                self.df.ix[river, "geometry"] = river_geom  # Dont forget to change geometry in dataframe!

            # upostevaj, da je reka lahko daljsa od spodaj lezecega rastra, zato poskusaj z vedno vecjimi indexi, dokler ne naletis na raster:
            first_height = None
            count = 0
            while first_height == None:
                try:
                    # po pet tock hodi naprej, dokler ne najdes dema pod tocko
                    first_height = Points.get_point_height(dem_file=dem_file, point=river_geom.coords[count * 5])
                except:
                    count += 1
                    pass

            last_height = None
            count = 0
            while last_height == None:
                try:
                    # po pet tock hodi nazaj, dokler ne najdes dema pod tocko
                    last_height = Points.get_point_height(dem_file=dem_file, point=river_geom.coords[-1 - count * 5])
                except:
                    count += 1
                    pass

            #logger.debug("River: {}, First point: {}m, Last point: {}m".format(river, round(first_height,2), round(last_height,2)))

            # assign direction value
            self.df.ix[river, "direction"] = "downstream" if first_height > last_height else "upstream"
            self.df.ix[river, "first"] = first_height
            self.df.ix[river, "last"] = last_height
        self.df["reverse_geometry"] = self.df["geometry"].apply(lambda x: LineString(x.coords[::-1]))
        self.df["correct_geometry"] = self.df["geometry"].where(self.df["direction"] == direction, self.df[
            "reverse_geometry"])  # kopiramo pravilno geometrijo glede na izbrane zelje

        del self.df["reverse_geometry"]
        del self.df["geometry"]
        del self.df["direction"]
        del self.df["first"]
        del self.df["last"]

        # Update df
        self.df = self.df.rename(columns={"correct_geometry": "geometry"}).set_geometry(
            "geometry")  # preimenujemo nazaj

        # Set direction, now that it is clear what is the direction
        self.direction = direction

    def point_sample_line(self, interpolation_density=1, dem_file=None):

        if dem_file == None:
            raise IOError(
                "If you want to perform point sample line shp, you have to provide a dem file of the area!")

        self.dem_file = dem_file
        self.interpolation_density = interpolation_density

        # Create point_shp from line_shp in
        self.df_p = Shp.lines_to_points(df_lines=self.df, interpolate=self.interpolation_density,
                                      point_id_f=self.point_id_f)

        # Sample dem raster file to pick up values!
        self.df_p = Shp.point_sampling_tool(df_points=self.df_p, src_raster=self.dem_file, dem_field=self.z_f,
                                          error_on_nan=False)


class Cross_sections():
    # Default attributes to be used when object is initialized from other sources
    z_f = "z"
    river_f = "river"
    point_id_f = "point_id"
    profile_id_f = "profile_id"
    xz_abs_chainage_f = "abs_profil"
    xz_central_chainage_f = "cen_profil"
    rel_z_f = "rel_z" #visina tock glede na najnizno tocko.
    chainage_f = "chainage"
    orientation_f = "orient"
    point_order_f = "point_ord"

    round_decimals = 2

    naming_number_of_digits = 3
    naming_starting_number = 1

    def __init__(self, df_r, profile_orientation="left", chainaging_direction="upstream", naming_direction="upstream"):

        # RABIS PRI INICIALIZACIJI:
        # NA KATERI REKI, KAKSNE BOJO LASTNOSTI DF_REKA,ZELJENE LASTNOSTI

        ### Minimal requirements for a creation of Cross_sections class is a point dataframe with a point_id, profile_id and z attributes.
        ### Other important values, such as naming direction, profile orientation and underlying river, can be calculated afterwards.

        self.df = None #point dataframe (default)
        self.df_l = None #line datafframe (default)

        # Obvezno rabis postiman river class, preden karkoli delas s cross sectioni!  Riverfield bos prevzel od river shp!
        self.df_r = df_r
        if self.df_r.direction is None:
            raise Exception(
                "Rivers class obviously hasn't been assigned and calculated a the proper orientation! Use a set_river_direction method!")

        # SETTINGS
        # INPUT ERROR CHECK
        self.chainaging_direction = chainaging_direction
        if self.chainaging_direction not in ["upstream", "downstream"]:
            raise Exception("Variable 'chainaging_direction' can only have value 'upstream' or 'downstram'!")

        self.profile_orientation = profile_orientation
        if self.profile_orientation not in ["left", "right"]:
            raise Exception("Variable 'xs_orientation' can only have value 'left' or 'right'!")

        self.naming_direction = naming_direction
        if self.naming_direction not in ["upstream", "downstream", None]:
            raise Exception("Variable 'naming_direction' can only have value 'upstream' or 'downstram'!")

    def populate_automatically(self,profile_density=500,profile_width=100,interpolation_density=1,dem_file=None):

        self.profile_density=profile_density
        self.profile_width = profile_width
        self.interpolation_density = interpolation_density
        self.dem_file = dem_file

        #Create dummy lines perpendicular to the river file
        self.df_l = Shp.create_lines_along_chainage(df_chainage=self.df_r.df,
                                                    profile_density=self.profile_density,
                                                    profile_width=self.profile_width)

        # doloci stacionazo, ime reke in orientacijo profila
        self.calculate_chainage_name_and_orientation()

        # Ce slucajno ni imel profil_id iz prve, preimenuj profile
        self.rename_xsection_ids()

        # Create point_shp from line_shp in
        self.df = Shp.lines_to_points(df_lines=self.df_l, interpolate=self.interpolation_density,
                                      point_id_f=self.point_id_f)

        # Sample dem raster file to pick up values!
        self.df = Shp.point_sampling_tool(df_points=self.df, src_raster=self.dem_file, dem_field=self.z_f,
                                          error_on_nan=False)


        self.set_profile_orientation()
        #AUTOGENERATE

    def populate_from_line_shp(self, df_l, profile_id_f=None, interpolation_density=1, dem_file=None):

        # Nujno rabis ime profila za narest. No ni nujno v bistvu. #TODO RENAME!

        if self.df_l is not None:
            raise IOError(
                "df_l attribute is not empty, so It seems that a Cross section class is already populated from line_shp")

        if dem_file == None:
            raise IOError(
                "If you want to create profile class from line shp, you have to provide a dem file of the area!")

        if isinstance(df_l, str):
            self.df_l = gpd.read_file(df_l)
        else:
            self.df_l = df_l

        if profile_id_f == None:
            self.df_l[self.profile_id_f] = self.df_l.index
            # Ce ostane none, se pravi nisi specificiral, potem naredi svoje poimenovanje z default nastavitvami.
            # V prvi iteraciji samo glupa imena
        else:
            self.profile_id_f = profile_id_f

        self.dem_file = dem_file
        self.interpolation_density = interpolation_density

        # doloci stacionazo, ime reke in orientacijo profila
        self.calculate_chainage_name_and_orientation()

        # Create point_shp from line_shp in
        self.df = Shp.lines_to_points(df_lines=self.df_l, interpolate=self.interpolation_density,
                                      point_id_f=self.point_id_f)

        # Sample dem raster file to pick up values!
        self.df = Shp.point_sampling_tool(df_points=self.df, src_raster=self.dem_file, dem_field=self.z_f,
                                          error_on_nan=False)


        # Ce slucajno ni imel profil_id iz prve, preimenuj profile
        if profile_id_f == None:
            self.rename_xsection_ids()

        self.set_profile_orientation()



    def populate_from_point_shp(self, df, profile_id_f, point_id_f, z_f):

        # metoda, ki naredi class iz point shapefila, zraven pa naredi še line shapefile. Nujni podatki. shapefile,

        if isinstance(self.df, pd.DataFrame):
            raise Exception(
                "df attribute is not empty, so It seems that a Cross section class is already populated from point_shp")

        # Shapefiles
        if isinstance(df, str):
            self.df = gpd.read_file(df)
        else:
            self.df = df

        #Ce point_id ni podan, ga naredi, pac randomly poimenuj tocke v profilu. Profile id pa mora bit!
        if point_id_f is None:
            self.df[self.point_id_f] = range(len(self.df.index))
        else:
            self.profile_id_f = profile_id_f

        self.z_f = z_f
        self.point_id_f = point_id_f

        self.straightify_measurements()

        # naredi df_lines iz df kar avtomatsko in takoj poracunaj lastnosti stacionazo,
        self.df_l = Shp.points_to_lines(df_points=self.df, groupby=self.profile_id_f)
        self.calculate_chainage_name_and_orientation()
        self.set_profile_orientation()


    def straightify_measurements(self):

        def points_into_straight_row(points_list):

            '''
            Funkcija vzame seznam tock, ki jih premakne tako, da se sestavijo v najbolj reprezerntativno linijo.
            Vzame listo list s tremi argumenti: easting,northing,id_tocke. Id tocke je nujen, da sploh ves, za katero tocko je
            slo v osnovi.
            :return:
            '''
            if isinstance(points_list,pd.Series):
                SERIES_INPUT = True
                points_list = points_list.values.tolist()
            else:
                SERIES_INPUT = False

            if isinstance(points_list[0], Point):
                points_list = [(i.x, i.y) for i in points_list]
                SHAPELY_INPUT = True
            else:
                SHAPELY_INPUT = False

            if len(points_list[0]) != 2:
                raise Exception("Vsak element lista (tocka) mora imeti tocno 2 elementa. easting,northin")


            points_we = sorted(points_list, key=lambda x: x[0])
            points_sn = sorted(points_list, key=lambda x: x[1])

            max_x = points_we[-1][0]-points_we[0][0]
            max_y = points_sn[-1][1]-points_sn[0][1]

            if max_x > max_y:
                points_list = points_we
            else:
                points_list = points_sn

            x_coords = [i[0] for i in points_list]
            y_coords = [i[1] for i in points_list]

            # izracunaj smerni koeficient najboljsega linearnega fita za dane tocke
            k, n, _, _, _ = stats.linregress(x_coords, y_coords)

            # razvrsti tocke po glede na x ali y koordinate


            dummy_first_point = [points_we[0][0] - 100, (points_we[0][0] - 100) * k + n]
            dummy_last_point = [points_we[-1][0] + 100, (points_we[-1][0] + 100) * k + n]

            dummy_line = LineString([dummy_first_point, dummy_last_point])

            # vsako tocko projeciraj na dummy linijo, zapisi njeno novo vrednost, ter izracunaj
            # vektor od zacetne lege, da bos vedu, kok popravit zacetni dummy_line

            linearized_points = []

            for point in points_list:
                new_point = dummy_line.interpolate(dummy_line.project(
                    Point(
                        point)))  # http://stackoverflow.com/questions/24415806/coordinate-of-the-closest-point-on-a-line
                linearized_points.append([new_point.x, new_point.y])

            if SHAPELY_INPUT:
                # vrni, kot si dobil
                return [Point(i) for i in linearized_points]

            elif SERIES_INPUT:
                return pd.Series([Point(i) for i in linearized_points])
            else:
                return linearized_points

        def points_series_into_straight_row(points_series,point_order_f):

            '''
            Funkcija vzame seznam tock, ki jih premakne tako, da se sestavijo v najbolj reprezerntativno linijo.
            Vzame listo list s tremi argumenti: easting,northing,id_tocke. Id tocke je nujen, da sploh ves, za katero tocko je
            slo v osnovi.
            :return:
            '''

            if not isinstance(points_series,pd.Series):
                raise Exception("Input mora biti series z indexom in Point točkami noter!")


            points_list = [(i,points_series[i].x, points_series[i].y) for i in points_series.index]

            points_we = sorted(points_list, key=lambda x: x[1])
            points_sn = sorted(points_list, key=lambda x: x[2])

            max_x = points_we[-1][1]-points_we[0][1]
            max_y = points_sn[-1][2]-points_sn[0][2]

            if max_x > max_y:
                points_list = points_we
            else:
                points_list = points_sn

            #Shrani vrstni red indexa
            old_index = [i[0] for i in points_list]

            #Spremeni nazaj v 2mestni list
            points_list = [i[1:] for i in points_list]

            x_coords = [i[0] for i in points_list]
            y_coords = [i[1] for i in points_list]


            # izracunaj smerni koeficient najboljsega linearnega fita za dane tocke
            k, n, _, _, _ = stats.linregress(x_coords, y_coords)
            # razvrsti tocke po glede na x ali y koordinate
            dummy_first_point = [points_we[0][1] - 100, (points_we[0][1] - 100) * k + n]
            dummy_last_point = [points_we[-1][1] + 100, (points_we[-1][1] + 100) * k + n]

            dummy_line = LineString([dummy_first_point, dummy_last_point])
            # vsako tocko projeciraj na dummy linijo, zapisi njeno novo vrednost, ter izracunaj
            # vektor od zacetne lege, da bos vedu, kok popravit zacetni dummy_line

            linearized_points = []


            for point in points_list:
                new_point = dummy_line.interpolate(dummy_line.project(Point(point)))  # http://stackoverflow.com/questions/24415806/coordinate-of-the-closest-point-on-a-line
                linearized_points += [new_point]

            straight_df = pd.DataFrame(index=old_index)
            straight_df["geometry"]=linearized_points
            straight_df[point_order_f]=range(len(old_index))

            return(straight_df)

        #NAPACNA, KER IZGUBI POVEZAVO Z OSTALIMI TOCKAMI!
        # self.df["geometry"] = self.df.groupby(self.profile_id_f)["geometry"].transform(lambda x: points_into_straight_row(x))
        # https://stackoverflow.com/questions/45100212/pandas-reverse-column-values-groupwise

        profiles = list(set(self.df[self.profile_id_f].values.tolist()))

        self.df[self.point_order_f]=None

        for profile in profiles:
            profile_points = self.df.loc[self.df[self.profile_id_f]==profile]["geometry"]
            straight_points = points_series_into_straight_row(profile_points,self.point_order_f)
            self.df.loc[straight_points.index,"geometry"]=straight_points["geometry"]
            self.df.loc[straight_points.index,self.point_order_f]=straight_points[self.point_order_f]


    def rename_xsection_ids(self, naming_prefix_length=4):

        # naming_prefix_length: If set to 0 or None, it will only name profiles by increasing int
        self.naming_prefix_length = naming_prefix_length

        # sort lib by river and chainage ascending (to normalize everything. You will still reverse numbering
        self.df_l = self.df_l.sort_values(by=[self.river_f, self.chainage_f])

        # preberi imena rek (vsaka reka je svoja zgodba
        rivers = list(set(self.df_l[self.river_f].values.tolist()))

        for river in rivers:

            # pripravi vse xs v eni reki
            df_xs_river = self.df_l.ix[self.df_l[self.river_f] == river].sort_values(by=self.chainage_f)

            id_list = range(self.naming_starting_number,
                            len(df_xs_river.index.tolist()) + self.naming_starting_number)

            if not self.naming_direction == self.chainaging_direction:
                id_list = id_list[::-1]

            if self.naming_prefix_length:
                id_list = ["{prefix}_{0:0{digits}}".format(i, prefix=river.replace(" ","").replace("_","").upper(),
                                                          digits=self.naming_number_of_digits) for i in id_list]

            self.df_l.ix[self.df_l[self.river_f] == river, self.profile_id_f] = id_list

        # Update point df too by merginf df_l and df
        if isinstance(self.df, pd.DataFrame):

            del self.df[self.profile_id_f]  # first delete old naming info
            self.df = pd.merge(self.df, self.df_l[[self.river_f, self.chainage_f, self.profile_id_f]],
                               on=[self.river_f, self.chainage_f])

    def calculate_chainage_name_and_orientation(self):

        # make aliases for easier to read indexing and populate river_f attirbute
        river_df = self.df_r.df
        self.river_f = self.df_r.name_f

        logger.info("Calculating chainage, orientation and underlying river of points and lines ...")

        self.df_l[self.chainage_f] = None  # dodaj polje stacionaza
        self.df_l[self.orientation_f] = None  # dodaj polje z orientacijo
        self.df_l[self.river_f] = None  # dodaj polje za poimenovanje profilov (kateri reki pripada)

        if self.profile_id_f not in self.df_l.columns.tolist():
            self.df_l[self.profile_id_f] = None  # dodaj id polje za poimenovanje posameznih profilov, ce ga ni

        # preberi imena rek RIVER_FILA (TO NA TEJ TOCKI MORE BIT POSTIMANO S PREJSNJIMI FUNKCIJAMI ZA PRIPRAVO REK!)
        rivers = list(set(river_df[self.river_f].values.tolist()))

        # vsak profil posebej sekat z vsako reko, dokler ne najdes matcha:
        number_of_rivers = len(rivers)

        for profile_index in self.df_l.index.tolist():  # loopaj vse profile
            no_common_point = True  # starting "while checking flag"
            current_river_index = 0  # starting river index
            xs_geom = self.df_l.ix[profile_index, "geometry"]
            breaked = False

            while no_common_point == True:
                if current_river_index > number_of_rivers - 1:
                    logger.warning(
                        "Profil number {} ne seka nicesar, zato ga ignoriram. Jebiga pac.".format(profile_index))
                    breaked = True
                    break

                river_geom = river_df.ix[current_river_index, "geometry"]
                common_point = xs_geom.intersection(river_geom)
                no_common_point = common_point.is_empty  # poglej, ce je ze common point (ce rata false = True)
                if no_common_point:
                    current_river_index += 1  # try next river
            if breaked:
                continue
            # ko si na tej tocki, ze ves katera reka je pod profilom. Zapisi v master self.df_l
            self.df_l.ix[profile_index, self.river_f] = river_df.ix[current_river_index, self.river_f]

        # tukaj pa morajo profili ze imet svoje pravo poimenovanje (tako rek, kot tudi IDjev)
        for river in rivers:
            # pripravi Linestring od reke
            riverline = river_df.ix[river_df[self.river_f] == river, "geometry"].values[0]

            # reverse river for chainaging purposes if riverline orientation and chainage orientation aren't the same
            if self.df_r.direction != self.chainaging_direction:
                riverline_chainage = LineString(riverline.coords[::-1])

            else:
                riverline_chainage = riverline

            # change river direction so it will flow down (so the left will be left!)
            if self.df_r.direction == "upstream":
                riverline_downstream = LineString(riverline.coords[::-1])
            else:
                riverline_downstream = riverline

            # print("River: {}, Orientation: {}, Chainaging_direction: {}, "
            #       "prva tocka: {}".format(river.encode("utf-8"),self.df_r.direction,self.chainaging_direction,riverline_chainage.coords[0]))

            # pripravi vse xs v eni reki
            df_xs_river = self.df_l.ix[self.df_l[self.river_f] == river]

            # loopaj vse xs v eni reki
            for i in df_xs_river.index:
                # 1. NAJDI STACIONAZO PROFILA
                # pripravi Linestring od XS
                xsline = df_xs_river.ix[i, "geometry"]

                # najdi vmesno tocko
                intersection = Lines.find_line_intersection(riverline_chainage, xsline)

                # izracunaj stacionazo
                xs_chainage = riverline_chainage.project(intersection)  # SHAPELY FTW!

                # dodaj section chainage
                self.df_l.ix[self.df_l["geometry"] == xsline, self.chainage_f] = xs_chainage
                # 2. UREDI ORIENTACIJO PROFILA!

                # Izracunaj azimut reke v tocki presecisca!
                xs_chainage_downstream = riverline_downstream.project(intersection)
                river_azimut =Lines.get_line_azimut_at_chainage(riverline_downstream,xs_chainage_downstream)

                xs_pointA, xs_pointB = list(xsline.coords)[0], list(xsline.coords)[-1]

                xs_azimut = Points.get_AB_azimut(xs_pointA, xs_pointB)  # smer profila

                # doloci relativni azimut #smer profila glede na reko
                relative_azimut = ((xs_azimut - river_azimut) + 360) % 360

                # calcualte orientation
                xs_orientation = "left" if 0 <= relative_azimut < 180 else "right"

                # assign recognized orientation value
                self.df_l.ix[self.df_l["geometry"] == xsline, self.orientation_f] = xs_orientation

                # ce relativna smer profila vecja kot 180 glede na smer reke, potem gre ocitno za profil v smeri right-to-left

        # round up chainage!
        self.df_l[self.chainage_f] = pd.to_numeric(self.df_l[self.chainage_f]).round(self.round_decimals)


        # apply those calculations (chainage, orientation and underlying river to the point_df too!
        if self.df is not None:
            self.df = pd.merge(self.df, self.df_l[[self.chainage_f, self.orientation_f, self.river_f, self.profile_id_f]],
                               on=[self.profile_id_f])

    def calculate_internal_xz_chainages_and_sort(self, from_centre=False):

        '''
        Funkcija vzame point shapefile s kategoriziranimi tockami, kjer vsaka pripada dolocenemu profilu (liniji) in dolocenemu obmocju (npr. Reki).
        Za vsako kombinacijo teh tock izracuna razdaljo med tocakmi in stacionaze. Oboje  zapise v podan field in izvrze nov fajl
        POMEMBNO: CE HOCES POINT SAMPLAT VZDOLZNO OS REK, MORAS DAT OBVEZNO ID_FIELD=NONE in from_centre = False. Najprej moras pognat abs, da jih lahko sorta!
        :param point_shp:
        :param group_field:
        :param id_field:
        :param relative_field:
        :param absolute_field:
        :return:
        '''

        logger.info("Calculating internal profile chainages  ...")

        #doloci, kako se bo imenoval field
        if from_centre:
            xz_f = self.xz_central_chainage_f
        else:
            xz_f = self.xz_abs_chainage_f

        # create new fields to fill them up
        self.df.loc[:, xz_f] = None

        # read point separetely groupwise
        for group in list(set(self.df[self.river_f].values.tolist())):  # unikatni
            df_group = self.df[self.df[self.river_f] == group]
            df_group.is_copy = False  # avoid SettingWithCopyWarning (http://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas)
            # Ce ni podan ID_FIELD, sklepas, da gre za vzdolzne profile, kjer grupiras samo po reki, ne pa tudi po profilih.
            if self.profile_id_f == None:
                self.df.ix[self.df[self.river_f] == group, xz_f] = Shp.calculate_chainages(df_group)

                self.df.ix[self.df[self.river_f]==group,self.rel_z_f] = df_group[self.z_f]-df_group[self.z_f].min()

            # Sicer pa loopas se po profilih (Id vsake reke)
            else:
                if from_centre:
                    #river_geom = self.df_r.df.loc[self.df_r.df[self.river_f] == group, "geometry"].values.tolist()[0]
                    #print(river_geom)
                    river_geom = self.df_r.df.loc[self.df_r.df[self.river_f] == group, "geometry"].iloc[0]
                else:
                    river_geom = None

                for id in list(set(df_group[self.profile_id_f].values.tolist())):  # unikatni id
                    #Izracunaj horizontalne visine
                    df_id = df_group.ix[df_group[self.profile_id_f] == id]
                    self.df.ix[(self.df[self.river_f] == group) & (
                    self.df[self.profile_id_f] == id), xz_f] = Shp.calculate_chainages(df_id,river_geom=river_geom,point_order_f=self.point_order_f)

                    #izracunaj relativno visino
                    self.df.ix[(self.df[self.river_f] == group) & (
                    self.df[self.profile_id_f] == id), self.rel_z_f] = df_id[self.z_f]-df_id[self.z_f].min()

        # zaokrozi izracunane fielde
        self.df.loc[:, xz_f] = pd.to_numeric(self.df[xz_f]).round(self.round_decimals)

        # Poskrbi, da bodo tocke sortirane po stacionazi in profilu!
        self.df = self.df.reindex(index=order_by_index(self.df.index, index_natsorted(zip(self.df[self.chainage_f],self.df[self.xz_abs_chainage_f]))))


    def set_profile_orientation(self):
        # Funkcija za podane.
        # FUNKCIJA POCNE ISTO KOT XS_LINES TO POINTS; SAMO DA INTERNO NAREDI LINIJE; SICER PA VSE DELA S TOCKAMI!
        # Funkcija za dolocanje stacionaze precnih profilov glede na podan vzdolzni profil. Podani xs_fajl mora bit Point file!
        # Imena rek se morajo tocno ujemat med xs_shapom in river_fajlom, ni pa treba, da se imena columnom obeh fajlov.

        logger.info("Setting correct profile orientation (to {}) ...".format(self.profile_orientation))

        # naredi nov output file za preurejene tocke
        df_new = gpd.GeoDataFrame(columns=self.df.columns,crs=self.df_r.df.crs)

        # SEDAJ IMAS ZRIHTANE DUMMY DF_XSECTIONS, ZATO LAHKO PREKOPIRAS LASTNOSTI V XS_POINTS TER OBRNES VSE TISTE, KI NISO V REDU
        for id in self.df_l.index:

            profile_id = self.df_l.ix[id, self.profile_id_f]
            orientation = self.df_l.ix[id, self.orientation_f]

            # vzami vhodne tocke s trenutnim id, da jih bos preminglal
            df_profil = self.df[self.df[self.profile_id_f] == profile_id]

            if orientation != self.profile_orientation:
                df_profil = df_profil.iloc[
                            ::-1]  # http://stackoverflow.com/questions/20444087/right-way-to-reverse-pandas-dataframe

                #Zamenjal si polozaj tock, sedaj pa se njihovo ime, da bo 0 tam, kjer hoces zacetek.
                df_profil[self.point_id_f] = list(range(len(df_profil.index)))

            # append profile to the master points df
            df_new = df_new.append(df_profil)

        del df_new[self.orientation_f]
        # Update stara, nepravilno obrnjena point_df(df) in line_df (df_l)
        self.df = df_new
        self.df_l = Shp.points_to_lines(self.df, groupby=self.profile_id_f)

    def export_profiles_to_dxf(self, dxf_file, river_name):

        logger.info("Generating AutoCAD style profile graphics... ")

        GLOBAL_X0 = 0
        GLOBAL_Z0 = 0
        DISTANCE_BETWEEN_PROFILES_Z = 10
        DISTANCE_BETWEEN_PROFILES_X = 10
        BOX_BUFFER = 5
        TEXTBOX_ROW_HEIGHT = 1.5
        MAX_NUMBER_OF_PROFILES_IN_LINE = 5
        PROFILE_Z_SHIFT = 2
        VZD_PROFILE_HEIGHT_FACTOR = 0.5
        PROFILE_HEIGHT_FACTOR = 1

        COLUMNS_TO_LABEL = ["z","abs_profil","cen_profil"]
        LABEL_NAMES = ["Teren [m.n.v]","Od prve tocke [m]","Od osi [m]"]
        TEXTBOX_HEIGHT = len(COLUMNS_TO_LABEL)*TEXTBOX_ROW_HEIGHT

        if not self.xz_abs_chainage_f in self.df.columns:
            raise IOError(
                "Cross section object doesn't have xz_abs_chainge field assigned yet. "
                "Make sure to run 'calculate_internal_chainages' method first!")

        if not self.xz_central_chainage_f in self.df.columns:
            raise IOError(
                "Cross section object doesn't have xz_cen_chainge field assigned yet. "
                "Make sure to run 'calculate_internal_chainages' method first with central = True!")

        x0 = GLOBAL_X0
        z0 = GLOBAL_Z0

        #Preberi geometry od reke
        river_geom = self.df_r.df.loc[self.df_r.df[self.river_f]==river_name,"geometry"].loc[0]

        #Doloci, koliko siroke profile bos delal.
        PROFILE_BOX_WIDTH = int(self.df[self.xz_abs_chainage_f].max()) + BOX_BUFFER
        PROFILE_BOX_HEIGHT = int(self.df[self.rel_z_f].max()) + BOX_BUFFER + PROFILE_Z_SHIFT + TEXTBOX_HEIGHT

        profile_in_line = 1

        #Ustvari dxf object
        drawing = dxf.drawing(dxf_file)
        drawing.add_layer('PROFILE', color=0)
        drawing.add_layer('PROFILE_VERT', color=180)
        drawing.add_layer('PROFILE_TEXT', color=0)
        drawing.add_layer('PROFILE_CHAINAGE', color=0)
        drawing.add_layer('OS', color=0)
        drawing.add_layer('BOX', color=30)
        drawing.add_layer('BOX_TEXT', color=20)

        #Uredi tocke po profilu in točkah

        vzdolzni_profil_points = []

        for group in self.df[self.profile_id_f].unique():
            #ponastavi stevce za novo vrstico
            if profile_in_line > MAX_NUMBER_OF_PROFILES_IN_LINE:
                profile_in_line = 1
                x0 = GLOBAL_X0
                z0 -= (PROFILE_BOX_HEIGHT + DISTANCE_BETWEEN_PROFILES_Z)

            df_id = self.df[self.df[self.profile_id_f] == group].reset_index()

            #Izracunaj, koliko moras dodat, da bo profil na sredini.
            profile_width = df_id[self.xz_abs_chainage_f].max() + 2*BOX_BUFFER

            # PROFIL
            x = df_id[self.xz_abs_chainage_f].values.tolist()
            z = df_id[self.rel_z_f].values.tolist()
            x = [x0 + BOX_BUFFER + i for i in x]
            z = [z0 + PROFILE_Z_SHIFT + TEXTBOX_HEIGHT + i*PROFILE_HEIGHT_FACTOR for i in z]
            profile = tuple(zip(x,z))
            drawing.add(dxf.polyline(profile,layer="PROFILE"))

            # PROFILE_VERT
            for point in profile:
                drawing.add(dxf.line(start=point,end=(point[0],z0+TEXTBOX_HEIGHT),layer="PROFILE_VERT"))

            #BOX
            for i,col in enumerate(COLUMNS_TO_LABEL):
                drawing.add(dxf.polyline([[x0, z0+i*TEXTBOX_ROW_HEIGHT],
                                          [x0+profile_width, z0+i*TEXTBOX_ROW_HEIGHT],
                                          [x0+profile_width, z0+(i+1)*TEXTBOX_ROW_HEIGHT],
                                          [x0, z0+(i+1)*TEXTBOX_ROW_HEIGHT],
                                          [x0, z0 + i * TEXTBOX_ROW_HEIGHT]],layer="BOX"))

                #Dodaj naslov
                drawing.add(dxf.text(LABEL_NAMES[i],insert=(x0+BOX_BUFFER/2,z0+(i+0.5)*TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))

                for j,x_pos in enumerate(x):
                    drawing.add(dxf.text(df_id.loc[j,col], insert=(x_pos, z0+(i+0.5)*TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))

            # OS IN OZNAKE OSI
            profil_tloris = LineString([df_id["geometry"].iloc[0],df_id["geometry"].iloc[-1]])
            presecisce_tloris = profil_tloris.intersection(river_geom)
            print(presecisce_tloris)
            xz_abs_chainage_os = round(df_id.loc[df_id[self.xz_abs_chainage_f]==0,"geometry"].loc[0].distance(presecisce_tloris),2)

            os_line = [[x0 + BOX_BUFFER + xz_abs_chainage_os, z0 + PROFILE_Z_SHIFT/2 + TEXTBOX_HEIGHT],
                       [x0 + BOX_BUFFER + xz_abs_chainage_os, z0 + PROFILE_Z_SHIFT + 2*TEXTBOX_HEIGHT + df_id[self.rel_z_f].max()]]

            presecisce_naris = list(LineString(profile).intersection(LineString(os_line)).coords)[0]

            z_os_real = round(df_id[self.z_f].min()+presecisce_naris[1]-(z0 + PROFILE_Z_SHIFT + TEXTBOX_HEIGHT),2)

            print(z_os_real)
            print(xz_abs_chainage_os)
            print()

            #Dodaj tocke za vzdolzni profil
            vzdolzni_profil_points.append([df_id.loc[0,self.chainage_f],z_os_real])

            #narisi os:
            drawing.add(dxf.line(start=os_line[0], end=os_line[-1], layer="OS"))

            #Dodaj text z visino osi
            drawing.add(dxf.text(z_os_real, insert=[presecisce_naris[0],z0 + TEXTBOX_ROW_HEIGHT/2], layer="BOX_TEXT")) #Teren
            drawing.add(dxf.text(xz_abs_chainage_os, insert=[presecisce_naris[0],z0 + 3*TEXTBOX_ROW_HEIGHT/2], layer="BOX_TEXT")) #Abs
            drawing.add(dxf.text("0", insert=[presecisce_naris[0],z0 + 5*TEXTBOX_ROW_HEIGHT/2], layer="BOX_TEXT")) #Cent


            # IME IN STACIONAŽA
            drawing.add(dxf.text("Profil " + str(df_id.loc[0,self.profile_id_f]),
                                 insert=(presecisce_naris[0],z0 + TEXTBOX_HEIGHT+PROFILE_Z_SHIFT/2),
                                 layer="PROFILE_TEXT"))

            drawing.add(dxf.text("0+{}m".format(df_id.loc[0,self.chainage_f]),
                                 insert=(presecisce_naris[0],z0 + TEXTBOX_HEIGHT+PROFILE_Z_SHIFT/4),
                                 layer="PROFILE_CHAINAGE"))

            #Premakni cager za naslednji profil
            profile_in_line += 1
            x0 += (PROFILE_BOX_WIDTH + DISTANCE_BETWEEN_PROFILES_X)



        ###############################
        ########  VZDOLZNA OZ  ########
        ###############################

        VZD_COLUMNS = ["Teren [m.n.v.]", "Stacionaza [m]", "Profil"]
        VZD_TEXTBOX_HEIGHT = len(VZD_COLUMNS)*TEXTBOX_ROW_HEIGHT


        vzd_profile_length = vzdolzni_profil_points[-1][0] + 2 * BOX_BUFFER


        #Doloci izhodisce
        x0_vzd = GLOBAL_X0 + (PROFILE_BOX_WIDTH+DISTANCE_BETWEEN_PROFILES_X)*MAX_NUMBER_OF_PROFILES_IN_LINE + DISTANCE_BETWEEN_PROFILES_X
        z0_vzd = GLOBAL_Z0

        x = [x0_vzd + BOX_BUFFER + i[0] for i in vzdolzni_profil_points]
        z = [z0_vzd + PROFILE_Z_SHIFT + TEXTBOX_HEIGHT + (i[1] - min([i[1] for i in vzdolzni_profil_points]))*VZD_PROFILE_HEIGHT_FACTOR for i in vzdolzni_profil_points]

        vzd_profile = tuple(zip(x,z))
        drawing.add(dxf.polyline(vzd_profile,layer="PROFILE"))


        # PROFILE_VERT
        for point in vzd_profile:
            drawing.add(dxf.line(start=point,end=(point[0],z0_vzd+VZD_TEXTBOX_HEIGHT),layer="PROFILE_VERT"))


        # BOX
        for i, col in enumerate(VZD_COLUMNS):
            drawing.add(dxf.polyline([[x0_vzd, z0_vzd + i * TEXTBOX_ROW_HEIGHT],
                                      [x0_vzd + vzd_profile_length, z0_vzd + i * TEXTBOX_ROW_HEIGHT],
                                      [x0_vzd + vzd_profile_length, z0_vzd + (i + 1) * TEXTBOX_ROW_HEIGHT],
                                      [x0_vzd, z0_vzd + (i + 1) * TEXTBOX_ROW_HEIGHT],
                                      [x0_vzd, z0_vzd + i * TEXTBOX_ROW_HEIGHT]], layer="BOX"))

            # Dodaj naslov
            drawing.add(dxf.text(VZD_COLUMNS[i], insert=(x0_vzd + BOX_BUFFER / 2, z0_vzd + (i + 0.5) * TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))

        profili_imena = natsorted(self.df[self.profile_id_f].unique())

        #Dodaj: PAZI! Hardcoded visine!
        for j,chainage in enumerate(vzdolzni_profil_points):
            drawing.add(dxf.text(chainage[1], insert=(x[j], z0_vzd + 0.5 * TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))
            drawing.add(dxf.text(chainage[0], insert=(x[j], z0_vzd + 1.5 * TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))
            drawing.add(dxf.text(profili_imena[j], insert=(x[j], z0_vzd + 2.5 * TEXTBOX_ROW_HEIGHT), layer='BOX_TEXT'))


        #Shrani
        drawing.save()



    def export_to_xns11_file(self, xns11_file):
        logger.info("Generating mike11 xns11 import file ...")

        if not self.chainage_f:
            raise IOError(
                "Cross section object doesn't have any chainage field assigned yet. Make sure to run 'calculate_chainage' method first!")

        MANNING = 25  # Default dummy resistance number to be put in a file

        txt = open(xns11_file, mode="w")

        rivers = list(set(self.df[self.river_f].values.tolist()))

        for river in rivers:

            # pripravi vse xs v eni reki
            df_xs_river = self.df.ix[self.df[self.river_f] == river]

            # naredi seznam vseh id v eni reki
            chainages = sorted(list(set(df_xs_river[self.chainage_f].values.tolist())))

            for chainage in chainages:
                # select only relevant points (tiste, ki imajo isti chainage - ne rabis vpletat ID, plus komplikacije pri vrstnem redu pridejo)
                df_profil = self.df.ix[(self.df[self.river_f] == river) & (self.df[self.chainage_f] == chainage)].reset_index()

                points_in_profile = df_profil.index.tolist()
                lowest_z = float(df_profil[self.z_f].min())  # you need it to assign value 2

                profile_id = df_profil[self.profile_id_f].values.tolist()[
                    0]  # kretenski nacin za dobit vrednost, ki je itak enaka posvod po izrezu
                special_point_already_used = False  # flag, da ne naredi vec kot ene tocke 2!

                first_coordinate = df_profil.loc[df_profil.first_valid_index(), "geometry"]
                last_coordinate = df_profil.loc[df_profil.last_valid_index(), "geometry"]

                txt.write("{}\n".format(river))  # NAME OF RIVER
                txt.write("{}\n".format(river))  # NAME OF RIVER SEGMENT (THE SAME!)
                txt.write("               {}\n".format(round(float(chainage), 2)))  # CHAINAGE ON RIVER IN METERS
                txt.write("COORDINATES\n")
                txt.write("    2 {} {} {} {}\n".format(first_coordinate.x, first_coordinate.y, last_coordinate.x,
                                                       last_coordinate.y))
                txt.write("FLOW DIRECTION\n    0\n")
                txt.write("PROTECT DATA\n    0\n")
                txt.write("DATUM\n    0\n")
                txt.write("RADIUS TYPE\n    0\n")
                txt.write("DIVIDE X-Section\n0\n")
                txt.write("SECTION ID\n    {}\n".format(profile_id))
                txt.write("INTERPOLATED\n    0\n")
                txt.write("ANGLE\n    0.00   0\n")
                txt.write("RESISTANCE NUMBERS\n   0  2    {}     1.000     1.000    1.000    1.000\n".format(MANNING))
                txt.write("PROFILE        {}\n".format(profile_id))

                for i, index in enumerate(points_in_profile):

                    x = df_profil.ix[index, self.xz_abs_chainage_f]
                    z = df_profil.ix[index, self.z_f]
                    special_point = 0

                    if i == 0:
                        special_point = 1  # prva tocka ima 1
                    if i == len(points_in_profile) - 1:
                        special_point = 3  # zadnja tocka ima 3

                    if z == lowest_z and special_point_already_used is False:

                        special_point_already_used = True
                        special_point = 2  # ce je najnizja, daj 0

                    txt.write(
                        "    {}     {}    {}     <#{}>     0     0.000     0\n".format(x, z, MANNING, special_point))

                txt.write("LEVEL PARAMS\n   1  0    0.000  0    0.000  20\n")
                txt.write("*******************************\n")

        txt.close()

        self.xns11_file = xns11_file

        return self.xns11_file


class Lines():
    @staticmethod
    def find_line_intersection(line1, line2):

        for line in [line1, line2]:
            if line.type not in ["LineString", "MultiLineString"]:
                raise Exception("Given line is not of type LineString or MultiLineString")

        return line1.intersection(line2)

    @staticmethod
    def get_line_azimut_at_chainage(line,chainage):
        if not isinstance(line,LineString):
            raise IOError("line can only be shapely.geom.LineString!")
        if chainage > line.length:
            raise IOError("You are asking for a azimuth of {} long line at chainage {}. Chainage too big!".format(line.length,chainage))
        river_pointA, river_pointB = line.interpolate(
            chainage - 0.0001), line.interpolate(chainage + 0.0001)
        return Points.get_AB_azimut(river_pointA, river_pointB)  # smer reke v okolici profila


class Points():
    @staticmethod
    def get_AB_azimut(pointA, pointB, round_decimals=2):

        '''
        Funkcija vzame dve tocki in izracuna azumut od prve do druge. Input je lahko tuple dveh tock ali pa shepely point object
        :param pointA:
        :param pointB:
        :return:
        '''

        if type(pointA) == tuple:
            pass
        else:
            try:
                pointA = pointA.coords[0]
            except:
                raise TypeError("Only tuples or Shapely POINT objects are supported as arguments")

        if type(pointB) == tuple:
            pass
        else:
            try:
                pointB = pointB.coords[0]
            except:
                raise TypeError("Only tuples or Shapely POINT objects are supported as arguments")

        deltay = pointB[1] - pointA[1]
        deltax = pointB[0] - pointA[0]

        alfa = math.degrees(math.atan2(deltay, deltax))
        azimut = (90 - alfa) % 360

        return round(azimut, round_decimals)

    @staticmethod
    def get_point_from_distance_and_angle(point, d, theta):
        if isinstance(point,list):
            try:
                point = Point(point)
            except:
                raise IOError("Point argument must be either [x,y] or Shapely.geom.Point object!")

        theta_rad = pi / 2 - radians(theta)
        return Point(round(point.x + d * cos(theta_rad), 5), round(point.y + d * sin(theta_rad), 5))

    @staticmethod
    def closest_point_to_given_points(points, reference_points):

        """
        Function, that returns a list of points from a reference points_list for a given list of points, for each one their
        closest neighbour

        https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
        :param points:
        :param df_reference_points:
        :return:
        """

        if isinstance(reference_points, gpd.GeoDataFrame):
            reference_points = [(p.x, p.y) for p in reference_points["geometry"].values.tolist()]

        reference_points = np.array(reference_points)

        results = []
        if not isinstance(points, list):
            points = [points]

        for point in points:
            results.append(reference_points[spatial.KDTree(reference_points).query(point)])

        return results

    @staticmethod
    def find_underlying_polygon(points, df_polygon, polygon_name_field):

        """
        Function returns array with the name of the underlying polygon for every given point in the list, and np.NaN for
        every mismatch
        :param points:
        :param df_polygon:
        :param polygon_name_field:
        :return:
        """

        results = []
        if not isinstance(points, list):
            points = [points]

        for point in points:

            # je gre za prazno tocko, vrni None
            if not isinstance(point, Point) and (not point[0] or not point[1]):
                results.append(np.NaN)
                continue

            p = Point(point) if not isinstance(point, Point) else point

            for i in df_polygon.index.tolist():

                polygon = df_polygon.ix[i, "geometry"]

                if p.within(polygon):
                    results.append(df_polygon.ix[i, polygon_name_field])
                    # print("nasel poligon", df_polygon.ix[i,polygon_name_field], df_polygon.ix[i,"RIVER"])
                    break

                elif i == df_polygon.index.tolist()[-1]:
                    # ce je prisel sem, pomeni, da ni nasel nic. Tocka je ocitno izven vseh polygonov. Zapisi none
                    results.append(np.NaN)
        if len(results) == 1:
            results = results[0]
        return results

    @staticmethod
    def closest_element_to_given_points_KDTree(points, df_reference_points, name_field):

        """
        Function,

        https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
        :param points:
        :param df_reference_points:
        :return:
        """

        # ce je shapefile argument kot string, potem gre za fajl, ki ga preberi
        if isinstance(df_reference_points, str):
            df_reference_points = gpd.read_file(df_reference_points)

        reference_points = np.array([(p.x, p.y) for p in df_reference_points["geometry"].values.tolist()])

        # create a KDTre object from a reference points
        KDTree_object = spatial.KDTree(reference_points)

        results = []

        if not isinstance(points, list):
            points = [points]

        if isinstance(points[0], Point):
            points = [(p.x, p.y) for p in points]

        for point in points:
            now = datetime.now()
            index_of_closest = KDTree_object.query(point)[1]
            value = df_reference_points.reset_index().ix[
                index_of_closest, name_field].values.tolist()
            # https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array

            results.append(value)

        if len(results) == 1:
            results = results[0]
        elif len(results) == 0:
            results = None
        return results

    @staticmethod
    def closest_element_to_given_points(points, shapefile, name_field):
        # ce je shapefile argument kot string, potem gre za fajl, ki ga preberi
        if isinstance(shapefile, str):
            shapefile = gpd.read_file(shapefile)

        results = []

        for point in points:

            # je gre za prazno tocko, vrni None
            if not isinstance(point, Point) and (not point[0] or not point[1]):
                results.append(np.NaN)
                continue

            p = Point(point) if not isinstance(point, Point) else point

            distance = 10000000000000
            nearest_name = None
            nearest_object = None

            for i in shapefile.index.tolist():

                ref_object = shapefile.ix[i, "geometry"]
                name = shapefile.ix[i, name_field]

                # ce gre za prazen objekt, vrni None
                if ref_object.is_empty:
                    results.append(np.NaN)
                    continue

                trenutna_razdalja = p.distance(ref_object)

                if trenutna_razdalja < distance:
                    distance = trenutna_razdalja
                    nearest_name = name
                    nearest_object = ref_object

            results.append(nearest_name)

        if len(results) == 1:
            results = results[0]
        elif len(results) == 0:
            results = None
        return results

    @staticmethod
    def reproject_point(x, y, inputEPSG=3912, outputEPSG=4326):

        '''
        USAGE EXAMPLE:
        # reproject ll point:
        minx,miny = gdal_reproject_point(minx,miny)
        DEFUAILT EPSG PAIR IS GK_SLO TO WGS84

        :param x:
        :param y:
        :return:
        '''
        x = float(x)
        y = float(y)

        # create coordinate transformation
        inSpatialRef = osr.SpatialReference()
        inSpatialRef.ImportFromEPSG(inputEPSG)
        outSpatialRef = osr.SpatialReference()
        outSpatialRef.ImportFromEPSG(outputEPSG)
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

        # create a ll_point:
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)

        # Transform ur_point
        point.Transform(coordTransform)
        x, y = point.GetX(), point.GetY()

        return x, y

    @staticmethod
    def get_point_height(point=None, dem_file=None):

        # print("SAMO OPOZORILO: V funkciji my_qgis.get_point_height mora bit tocka valda podana v istem koordinatnem sistemu kot je DEM file!")

        if isinstance(point, Point):
            point = point.coords

        gdata = gdal.Open(dem_file)
        gt = gdata.GetGeoTransform()
        data = gdata.ReadAsArray().astype(np.float)
        x = int((point[0] - gt[0]) / gt[1])
        y = int((point[1] - gt[3]) / gt[5])
        return data[y, x]

    @staticmethod
    def autoroute_points(points, start=None):

        """
        As solving the problem in the brute force way is too slow,
        this function implements a simple heuristic: always
        go to the nearest city.

        Even if this algoritmh is extremely simple, it works pretty well
        giving a solution only about 25% longer than the optimal one (cit. Wikipedia),
        and runs very fast in O(N^2) time complexity.
        """

        def distance(point1, point2):
            """
            Returns the Euclidean distance of two points in the Cartesian Plane.

            >>> distance([3,4],[0,0])
            5.0
            >>> distance([3,6],[10,6])
            7.0
            """
            return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5

        if start:
            must_visit = points
            path = [start]
            must_visit.remove(start)

        else:
            ####
            # DECIDE WHICH POINT TO START WITH - THE WESTMOST OR SOUTHMOST? (IT DEPENDS ON GENERAL DIRECTION OF ALL POINTS)
            ####
            x_coords = [i[0] for i in points]
            y_coords = [i[1] for i in points]

            # Calculate direction coeficient of linear representation of general direction
            k, n, _, _, _ = stats.linregress(x_coords, y_coords)

            if -1 < k < 1:
                # General direction is west-east, make the westmost point first, so you can start autorouting at right place
                points = sorted(points, key=lambda x: x[0])
            else:

                # general direction is south-north, make southmost point second, so you can start autorouting at right place
                points = sorted(points, key=lambda x: x[1])

            path = [points[0]]
            must_visit = points

        while must_visit:
            nearest = min(must_visit, key=lambda x: distance(path[-1], x))
            path.append(nearest)
            must_visit.remove(nearest)
        return path

    @staticmethod
    def points_into_straight_row(points_list):

        '''
        Funkcija vzame seznam tock, ki jih premakne tako, da se sestavijo v najbolj reprezerntativno linijo.
        Vzame listo list s tremi argumenti: easting,northing,id_tocke. Id tocke je nujen, da sploh ves, za katero tocko je
        slo v osnovi.
        :return:
        '''

        if len(points_list[0]) != 2:
            raise Exception("Vsak element lista (tocka) mora imeti tocno 2 elementa. easting,northin")

        x_coords = [i[0] for i in points_list]
        y_coords = [i[1] for i in points_list]

        # izracunaj smerni koeficient najboljsega linearnega fita za dane tocke
        k, n, _, _, _ = stats.linregress(x_coords, y_coords)

        # razvrsti tocke po glede na x ali y koordinate
        points_we = sorted(points_list, key=lambda x: x[0])

        dummy_first_point = [points_we[0][0] - 100, (points_we[0][0] - 100) * k + n]
        dummy_last_point = [points_we[-1][0] + 100, (points_we[-1][0] + 100) * k + n]

        dummy_line = LineString([dummy_first_point, dummy_last_point])

        # vsako tocko projeciraj na dummy linijo, zapisi njeno novo vrednost, ter izracunaj
        # vektor od zacetne lege, da bos vedu, kok popravit zacetni dummy_line

        linearized_points = []

        for point in points_list:
            new_point = dummy_line.interpolate(dummy_line.project(
                Point(point)))  # http://stackoverflow.com/questions/24415806/coordinate-of-the-closest-point-on-a-line
            linearized_points.append([new_point.x, new_point.y])

        return linearized_points

    @staticmethod
    def pts_triangle_transformation(points, df_parameters, KDTree_object=None):

        """
        Function,

        https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array
        :param points:
        :param df_reference_points:
        :return:
        """

        # Dovoli izracunat sele kasenje - optimization purposes
        if not KDTree_object:
            reference_points = np.array([(p.x, p.y) for p in df_parameters["geometry"].values.tolist()])

            # create a KDTre object from a reference points
            KDTree_object = spatial.KDTree(reference_points)

        TRANS_PARAMETERS = "a b c d e f"

        new_points = []

        if not isinstance(points, list):
            points = [points]

        if isinstance(points[0], Point):
            points = [(p.x, p.y) for p in points]

        for point in points:
            now = datetime.now()
            index_of_closest = KDTree_object.query(point)[1]
            [a, b, c, d, e, f] = df_parameters.reset_index().ix[
                index_of_closest, TRANS_PARAMETERS.split(" ")].values.tolist()
            # https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array

            # calculate new points
            x_new = a * point[0] + b * point[1] + c
            y_new = d * point[0] + e * point[1] + f

            new_points.append(Point(x_new, y_new))

        if len(new_points) == 1:
            return new_points[0]

        return new_points


class Shp():
    "Static methods that operate on a geodataframe level"

    @staticmethod
    def dataframe_to_geodataframe(df, x_col, y_col,epsg=None):
        # vrne dodaten column z imenom geometry iz podanih fieldov. Zaenkrat bolj point

        df["geometry"] = [Point(x, y) for x, y in zip(df[x_col], df[y_col])]
        del df[x_col]
        del df[y_col]
        return gpd.GeoDataFrame(df,crs="+init=epsg:{}".format(epsg))

    @staticmethod
    def calculate_chainages(df, point_order_f = None, river_geom=None):
        "Calculates cumsum distance between the points in a given dataframe. No grouping by default, has to be done before calling a function"
        "Ce podas geometrijo reke, bo sklepal, da hoces razdaljo od sredine, sicer pa samo interni izracun narediš."

        if point_order_f:
            df = df.sort_values(by=point_order_f)

        if river_geom == None:
            # caluclate distance to the previous point
            df.loc[:, "_x"] = df.geometry.apply(lambda p: p.x)
            df.loc[:, "_y"] = df.geometry.apply(lambda p: p.y)
            df.loc[:, "x2+y2"] = (df["_x"].diff() ** 2 + df["_y"].diff() ** 2)
            df.loc[:, "x2+y2"] = df["x2+y2"].fillna(0)
            df.loc[:, "_ch_rel"] = df["x2+y2"].apply(lambda x: math.sqrt(x))  # calculate relative distance between points
            df.loc[:, "_ch_rel"].fillna(0, inplace=True)  # zamenjaj nan z 0

            # calculate cumulative summary (stacionaza)
            df.loc[:, "_ch_abs"] = df["_ch_rel"].cumsum()

            return df["_ch_abs"]

        else:
            df["_ch_abs"]=None
            profile_geom = LineString(df["geometry"].values.tolist())
            middle_point = profile_geom.intersection(river_geom)
            print(df)
            print(middle_point)
            print(profile_geom)
            print(df.reset_index().loc[0,"geometry"].distance(middle_point))
            print()
            for i in df.index:
                df.loc[i,"_ch_abs"]=df.loc[i,"geometry"].distance(middle_point)
                print(df.loc[i,"_ch_abs"])

            print()
            print()
            return df["_ch_abs"]

    @staticmethod
    def save_to_shapefile_with_prj(geo_df, file_out, epsg, encoding="utf-8"):

        prj_file = os.path.splitext(os.path.abspath(file_out))[0] + ".prj"

        prj_dict = {
            3912: 'PROJCS["MGI / Slovene National Grid",GEOGCS["MGI",DATUM["D_MGI",SPHEROID["Bessel_1841",6377397.155,299.1528128]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",15],PARAMETER["scale_factor",0.9999],PARAMETER["false_easting",500000],PARAMETER["false_northing",-5000000],UNIT["Meter",1]]',
            3794: 'PROJCS["Slovenia 1996 / Slovene National Grid",GEOGCS["Slovenia 1996",DATUM["D_Slovenia_Geodetic_Datum_1996",SPHEROID["GRS_1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",15],PARAMETER["scale_factor",0.9999],PARAMETER["false_easting",500000],PARAMETER["false_northing",-5000000],UNIT["Meter",1]]',
            4326: 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]',
            3857: 'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["Popular Visualisation CRS",DATUM["D_Popular_Visualisation_Datum",SPHEROID["Popular_Visualisation_Sphere",6378137,0]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Mercator"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["Meter",1]]',
            31258: 'PROJCS["MGI_Austria_GK_M31",GEOGCS["GCS_MGI",DATUM["D_MGI",SPHEROID["Bessel_1841",6377397.155,299.1528128]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",450000.0],PARAMETER["False_Northing",-5000000.0],PARAMETER["Central_Meridian",13.33333333333333],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'}

        if epsg not in prj_dict.keys():
            raise Exception("EPSG {} is not in the epsg:wkt_prj dictionary. Add it!".format(epsg))

        with open(prj_file, "w") as f:
            f.write(prj_dict[epsg])

        # save file
        geo_df.to_file(filename=file_out, crs_wkt=prj_dict[epsg], encoding=encoding)

    @staticmethod
    def filter_shapefile_df(df_in, **fields_and_values_pairs):

        '''
        Funkcija, ki omogoca filtriranje shapefila po poljubnih vrednostih poljubnih polj. Ownic. Primer uporabe funkcije:

        shp = "/home/marjan/arso/lidar/shp_400_smp/mtb_merged_lines.shp"
        print(my_qgis.filter_shapefile(shp,id=["100","102","103"],time="2011-03-13"))

        '''

        for field in fields_and_values_pairs:
            values = fields_and_values_pairs[field]

            if isinstance(values, list):

                df_in = df_in[df_in[field].isin(values)]
            else:
                df_in = df_in[df_in[field] == values]

        return df_in

    @staticmethod
    def multiline_to_line(df_lines, river_field=None, preserve_fields=None):

        '''

        :param line_file:
        :param file_out:
        :param river_field:
        :param rename: Samo ce je noter samo reka!
        :return:
        '''

        logger.info("Merging multilines with the same rivername into a simple line")

        if df_lines["geometry"].values.tolist()[0].type == "MultiLineString":
            df_lines = df_lines.rename(columns={"geometry": "multigeometry"}).set_geometry("multigeometry")
            df_lines["geometry"] = df_lines["multigeometry"].apply(lambda x: linemerge(x))

            del df_lines["multigeometry"]
            df_lines = df_lines.set_geometry("geometry")

        if df_lines.ix[0, "geometry"].type == "LineString" and len(df_lines.index) > 1:

            columns = [river_field, "geometry"] if not preserve_fields else [river_field] + preserve_fields + [
                "geometry"]
            df_merged = gpd.GeoDataFrame(columns=columns,crs=df_lines.crs).set_geometry("geometry")

            for river, parts in df_lines.groupby(river_field):

                lines = parts["geometry"].values.tolist()
                # logger.debug("Zdruzujem dele reke {}".format(river))
                simple_lines = []

                for line in lines:
                    if line.type == "LineString":
                        simple_lines.append(line)
                    elif line.type == "MultiLineString":
                        for part in line.geoms:
                            simple_lines.append(part)

                merged = linemerge(simple_lines)

                if merged.type != "LineString":
                    raise Exception("Line {}  still consists of {} parts after linemerge operation, "
                                    "which indicates topological errors in dataset."
                                    "Check for the topologic clarity of the LineString by using QGIS or something.".format(
                        river, len(merged)))

                values = [river] + parts.reset_index().loc[0, preserve_fields].values.tolist() + [
                    merged] if preserve_fields else [river, merged]

                df_merged = df_merged.append(pd.DataFrame(data=[values], columns=columns), ignore_index=True)

            df_lines = df_merged

        return df_lines

    @staticmethod
    def lines_to_points(df_lines=None, interpolate=None, point_id_f="point_id"):

        # funkcija za pretvarjanje linijskih shapefilov v tockovne, po vseh vertexih.
        # Nastane point file z atributom ID, da pripadnost vsake tocke osnovni liniji.
        # Vhodni shapefile z linijami mora imeti id field (npr. ime profila) z unikatnim ID (ali imenom) posameznih linij
        # in group (npr. ime pripadajoce reke), da ostane tako tudi po convertu
        # Ce hoces, ti se interpolira z intervalom, podanim v metrih! Pazi! Interpolacija izbrise obstojece tocke!
        # stvar dela za epsg 3912 ali 3794 (metricne pravokotne k.s. v glavnem!)

        logger.info("Converting xs lines to points ...")
        columns = df_lines.columns.tolist()
        columns_no_geo = [i for i in columns if i != "geometry"]
        # ustvari koncno tabelo vseh tock
        master_df = pd.DataFrame(columns=columns)

        # poloopaj vsako geometrijo (linijo)
        for index in df_lines.index.tolist():
            line = df_lines.loc[index, "geometry"]
            old_info = df_lines.ix[index, columns_no_geo].values.tolist()

            # vsaka linija je mogoce sestavljena iz vec odsekov. Just because. Loci Line in Multiline koncept

            def _interpolate_line_and_add_to_master_df(line, master_df, interpolate):

                if interpolate:
                    # http://stackoverflow.com/questions/34906124/interpolating-every-x-distance-along-multiline-in-shapely
                    if not line.geom_type == 'LineString':
                        raise Exception("Nisi dal noter Shapely LineStringa! Napaka!")

                    num_vert = int(round(line.length / interpolate))
                    if num_vert == 0:
                        num_vert = 1
                    line = LineString(
                        [line.interpolate(float(n) / num_vert, normalized=True)
                         for n in range(num_vert + 1)])

                new_shp = gpd.GeoDataFrame(columns=columns_no_geo,crs=df_lines.crs)
                new_shp["geometry"] = line.coords
                new_shp[point_id_f] = list(range(0, len(line.coords)))
                for i, col in enumerate(columns_no_geo):
                    new_shp[col] = old_info[i]

                return pd.concat([master_df, new_shp], axis=0, ignore_index=True)

            # poskusi pretvorit multilinestring v linestring:
            if line.type == "MultiLineString":
                try:
                    line = linemerge(line)
                except:
                    pass

            if line.type == "LineString":
                master_df = _interpolate_line_and_add_to_master_df(line, master_df, interpolate)
            elif line.type == "MultiLineString":
                for part in line.geoms:
                    master_df = _interpolate_line_and_add_to_master_df(part, master_df, interpolate)

        # spremeni tocke v dejanske Point classe (obvezno za geodataframe
        master_df["geometry"] = master_df.apply(lambda x: Point((float(x.geometry[0]), float(x.geometry[1]))),
                                                axis=1)  # zakaj to dela!
        # spremeni dataframe v geodataframe
        master_df = gpd.GeoDataFrame(master_df, geometry="geometry",crs=df_lines.crs)
        master_df.crs = df_lines.crs  # copy crs information!

        return master_df

    @staticmethod
    def points_to_lines(df_points=None, groupby=None):

        logger.info("Converting xs lines to points ...")

        if isinstance(groupby, list):
            raise Exception("So far you can only group by one attribute")

        distinct_elements = list(set(df_points[groupby].values.tolist()))

        df_lines = gpd.GeoDataFrame(columns=df_points.columns,crs=df_points.crs)

        for i in distinct_elements:
            df_group = df_points[df_points[groupby] == i].reset_index()

            generic_cols = utils.find_uniform_df_cols(df_group)
            generic_values = df_group.ix[0, generic_cols].values.tolist()

            geometry = LineString(
                Points.autoroute_points(LineString(df_group.ix[:, "geometry"].values.tolist()).coords))

            group_cols = generic_cols + ["geometry"]
            group_values = generic_values + [geometry]
            df_lines.loc[len(df_lines), group_cols] = group_values

        return df_lines.dropna(axis=1, how="all").sort_values(by=groupby)

    @staticmethod
    def point_sampling_tool(src_raster=None, df_points=None, dem_field="DEM", error_on_nan=True, round_decimals=2):

        '''
        Funkcija vzame raster in point(!!!) shapefile ter vanj doda polje z izbranim imenov, v kateri so vrednosti pod izbranim DMR
        :return:
        '''

        logger.info("Point sampling DEM raster...")

        # since point_sampling tool only accepts files, it needs to be temporary
        if isinstance(df_points, gpd.GeoDataFrame):
            tmp_file = os.path.join(HOMEDIR, "_tmp", "_tmp.shp")
            df_points.to_file(tmp_file)
            df_points = tmp_file

        # read raster
        src_ds = gdal.Open(src_raster)
        gt = src_ds.GetGeoTransform()
        rb = src_ds.GetRasterBand(1)

        # read shapefile
        ds = ogr.Open(df_points)

        lyr = ds.GetLayer()
        dems = []  # prazen kontejner za tocke

        err = 0
        for feat in lyr:

            geom = feat.GetGeometryRef()
            mx, my = geom.GetX(), geom.GetY()  # coord in map units

            # Convert from map to pixel coordinates.
            # Only works for geotransforms with no rotation.
            px = int((mx - gt[0]) / gt[1])  # x pixel
            py = int((my - gt[3]) / gt[5])  # y pixel

            sample = rb.ReadAsArray(px, py, 1, 1)[0][0]

            if sample in [-99, -999, -9999, -9999, -99999]:
                err += 1
                msg = "Warning: While point sampling a point {},{}, a value {} (= NODATA) was found. " \
                      "Make sure the point really lies under the raster {}!".format(mx, my, sample, src_raster)

                if error_on_nan:
                    raise Exception(msg)

            dems.append(sample)  # intval is a numpy array, length=1 as we only asked for 1 pixel value

        if err > 0:
            logger.warning(
                "WARNING: NODATA raster values were found under {}/{} points. For better results, make sure that all points lay above the " \
                "specified raster {} with valid grid values." \
                    .format(err, len(lyr), src_raster))

        if isinstance(df_points, str):
            df_points = gpd.read_file(df_points)

        # pripni field z DEM vrednostmi
        df_points[dem_field] = dems
        df_points[dem_field] = df_points[dem_field].round(round_decimals)

        return df_points

    @staticmethod
    def point_shp_with_attributes_to_kml(points_gdf, gdf_epsg=3794, name_col=None, desc_col=None, data_cols=None,
                                         outfile="out.kml"):

        # Converts point shapefile into kml by keeping the desired attributes. If given name_col and/or desc_col, it puts
        # separately. If data_cols is None, it takes all the data as extended data

        points_gdf.columns = [i.lower() for i in points_gdf.columns]

        if data_cols is None:
            data_cols = points_gdf.columns  # change to lowercase
        else:
            data_cols = [i.lower() for i in data_cols]

        if name_col is not None:
            name_col = name_col.lower()
            if name_col in data_cols:
                try:
                    data_cols = data_cols - [name_col]
                except:
                    pass
        if desc_col is not None:
            desc_col = desc_col.lower()
            if desc_col in data_cols:
                try:
                    data_cols = data_cols - [desc_col]
                except:
                    pass

        with open(outfile, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
            f.write("<Document>\n")
            f.write("<name>{}</name>\n".format(os.path.splitext(os.path.basename(outfile))[0]))  # name of outfile as doc name
            # f.write("<Folder>\n")

            # NATO PROFILI
            if isinstance(points_gdf, str):
                points_gdf = gpd.read_file(points_gdf)

            # covert from local to wgs coord system (ohrani original za izracun razdalj in tega!)
            points_gdf.crs = {"init": "epsg:{}".format(gdf_epsg)}
            points_gdf = points_gdf.to_crs(epsg=4326)

            for p in points_gdf.index:
                f.write('<Placemark>\n')
                if name_col:
                    f.write("<name>{}</name>\n".format(points_gdf.ix[p, name_col]))

                if desc_col:
                    f.write("<description>{}</description>\n".format(points_gdf.ix[p, desc_col]))

                f.write("<ExtendedData>\n")
                for col in data_cols:
                    f.write('<Data name="{}">'.format(col))
                    f.write("<value>{}</value>\n".format(points_gdf.ix[p, col]))
                    f.write('</Data>'.format(col))
                f.write("</ExtendedData>\n")

                f.write('<Point>\n')
                f.write('<coordinates>\n')
                x = points_gdf.ix[p, "geometry"].x
                y = points_gdf.ix[p, "geometry"].y
                f.write("{},{}\n".format(x, y))
                f.write('</coordinates>\n')
                f.write('</Point>\n')
                f.write('</Placemark>\n')

            # f.write("</Folder>\n")
            f.write("</Document>\n")
            f.write('</kml>\n')
            f.close()

    @staticmethod
    def xs_to_3D_kml(points_gdf, z_col, xs_epsg=3794, profile_id_field="profile_id",
                     profile_chainage_field="chainage", extrude=0, outfile=None, false_height_m=30):

        with open(outfile, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
            f.write("<Document>\n")
            f.write("<Folder>\n")

            # NATO PROFILI

            if isinstance(points_gdf, str):
                points_gdf = gpd.read_file(points_gdf)

            # covert from local to wgs coord system (ohrani original za izracun razdalj in tega!)
            points_gdf.crs = {"init": "epsg:{}".format(xs_epsg)}
            points_gdf_orig = points_gdf.copy(deep=True)
            points_gdf = points_gdf.to_crs(epsg=4326)

            vse_stacionaze = natsorted(list(set(points_gdf[profile_chainage_field].values.tolist())))
            vse_stacionaze = [i for i in vse_stacionaze if i > 0]
            # naredi svoj zapis za vsak profil
            for chainage in vse_stacionaze:
                df_group = points_gdf[points_gdf[profile_chainage_field] == chainage]
                df_group = df_group.reset_index()
                df_group_orig = points_gdf_orig[points_gdf_orig[profile_chainage_field] == chainage]
                df_group_orig = df_group_orig.reset_index()

                middle_point = df_group.ix[len(df_group.index) / 2, :]
                first_point = df_group_orig.loc[0, "geometry"]
                last_point = df_group_orig.loc[len(df_group.index) - 1, "geometry"]
                x = middle_point["geometry"].x
                y = middle_point["geometry"].y
                z = middle_point[z_col] if not false_height_m else middle_point[z_col] + false_height_m
                heading = Points.get_AB_azimut(first_point, last_point) + 90  # pravokotno na profil!
                range = first_point.distance(last_point)

                f.write('<Placemark>\n')
                f.write('<name>Profil {}</name>\n'.format(df_group.ix[0, profile_id_field]))
                f.write('<description>Stacionaža: {} m</description>\n'.format(chainage))
                f.write('<LookAt>'
                        '<longitude>{}</longitude>'
                        '<latitude>{}</latitude>'
                        '<altitude>{}</altitude>'
                        '<heading>{}</heading>'
                        '<tilt>45</tilt>'
                        '<range>{}</range>'
                        '</LookAt>\n'.format(x, y, z, heading, range))

                # f.write('<styleUrl>#LINESTRING</styleUrl>\n')
                f.write('<LineString>\n')
                f.write('<extrude>{}</extrude>\n'.format(extrude))
                f.write('<altitudeMode>absolute</altitudeMode>\n')
                f.write('<coordinates>\n')
                for point in df_group.index:
                    x = df_group.loc[point, "geometry"].x
                    y = df_group.loc[point, "geometry"].y
                    z = df_group.loc[point, z_col] if not false_height_m else df_group.loc[
                                                                                  point, z_col] + false_height_m
                    f.write("{},{},{}\n".format(x, y, z))
                f.write('</coordinates>\n')
                f.write('</LineString>\n')
                f.write('</Placemark>\n')
            f.write("</Folder>\n")
            f.write("</Document>\n")
            f.write('</kml>\n')
            f.close()

    @staticmethod
    def autoroute_points_df(points_df, x_col="e", y_col="n"):

        '''
        # Funkcija, ki za nakljucno vrsto tock vrne tocke v takem vrstnem redu, da je povezava med njimi najkrajsa.
        Input je poljuben dataframe, ki ima x in y column locen. Zaenkrat.
        '''
        points_list = points_df[[x_col, y_col]].values.tolist()

        # razvrsti tocke po glede na x ali y koordinate
        points_we = sorted(points_list, key=lambda x: x[0])
        points_sn = sorted(points_list, key=lambda x: x[1])

        # izracunaj, ali je glavna smer profila SJ ali VZ
        westmost_point = points_we[0]
        eastmost_point = points_we[-1]

        azimut = Points.get_AB_azimut(Point(westmost_point), Point(eastmost_point))

        if (azimut > 45 and azimut < 135):
            points_list = points_we
        elif azimut > 180:
            raise Exception(
                "Napaka pri izracunu azimuta! Ne more bit vecji od 180, ker je prva tocka na zahodu,druga pa vzhodu!")
        else:
            points_list = points_sn

        # Naredi output, ordered df in ze kar daj noter prvega
        ordered_points_df = pd.DataFrame(columns=points_df.columns)
        ordered_points_df = ordered_points_df.append(
            points_df.ix[(points_df[x_col] == points_list[0][0]) & (points_df[y_col] == points_list[0][1])])

        for iteration in range(0, len(points_list) - 1):

            already_ordered = ordered_points_df[[x_col, y_col]].values.tolist()

            current_point = already_ordered[-1]  # trenutna tocka, ki ji isceno najblizjo naslednjo
            possible_candidates = [i for i in points_list if i not in already_ordered]  # seznam preostalih kandidatk

            distance = 10000000000000000000000
            best_candidate = None
            for candidate in possible_candidates:
                current_distance = Point(current_point).distance(Point(candidate))
                if current_distance < distance:
                    best_candidate = candidate
                    distance = current_distance

            ordered_points_df = ordered_points_df.append(
                points_df.ix[(points_df[x_col] == best_candidate[0]) & (points_df[y_col] == best_candidate[1])])

        return ordered_points_df

    @staticmethod
    def create_lines_along_chainage(df_chainage,profile_density,profile_width):

        df_lines = gpd.GeoDataFrame(columns=["geometry"],crs=df_chainage.crs)
        for line in df_chainage["geometry"].values.tolist():

            chainages = [0.1] + list(range(profile_density,int(line.length),int(profile_density))) + [line.length-0.1]

            half_profile = round(float(profile_width)/2,2)

            for ch in chainages:
                river_point = line.interpolate(ch)
                ch_azimuth = Lines.get_line_azimut_at_chainage(line,ch)
                profile_A = Points.get_point_from_distance_and_angle(river_point,half_profile,ch_azimuth+90)
                profile_B = Points.get_point_from_distance_and_angle(river_point,half_profile,ch_azimuth-90)

                df_lines.loc[len(df_lines.index),"geometry"]=LineString([profile_A,profile_B])

        return df_lines


    @staticmethod
    def convert_to_numeric(df):
        for i in df.columns:
            df[i] = pd.to_numeric(df[i], errors="ignore")

        return df
