import glob
import os
from fnmatch import fnmatch

import gdal
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats
from tqdm import tqdm_notebook as tqdm


def Process_imagery(Path_dir, zonalpoly, NoDataValue, mask_value, maskit=True):
    print(zonalpoly)
    gdf = gpd.read_file(zonalpoly)
    if maskit:
        mask_value = mask_value.split(",")
    # Get the zonal stats
    NoDataValue = int(NoDataValue)
    gdf2 = Do_Zonal_Stats(Path_dir, gdf, NoDataValue, mask_value, maskit)
    # os.chdir(Path_dir)

    # Get number of observations
    gdf3 = Get_Num_Obs(Path_dir, gdf, NoDataValue, mask_value, maskit)
    for date in gdf2.iterrows():
        if 'median' in gdf3.columns:
            gdf2['observations'] = gdf3['median']

    # Save CSV
    print("Producing csv output...")
    z_simple = zonalpoly.split('/')
    z_simple = z_simple[-1].split('.')
    z_simple = z_simple[0]
    Path_out = os.path.dirname(os.path.abspath(Path_dir))

    output = os.path.join(Path_out, z_simple + '_FullStats.csv')
    print("CSV statistics saved here: ", output)
    gdf2.to_csv(output)
    for item in gdf2['ID'].unique():
        gdf3 = gdf2[(gdf2.ID == item)]
        output = os.path.join(Path_out, z_simple +
                              '_Stats_ID_' + str(item)+'.csv')
        gdf3.to_csv(output)

    return gdf2

# Mask your data


def Mask_it(rasterin, mask, geom, NoDataValue, mask_value):
    geom = geom.bounds
    geom = [geom[0], geom[3], geom[2], geom[1]]
    MRO = gdal.Translate("temp1.vrt", rasterin, projWin=geom).ReadAsArray()
    MR2 = gdal.Translate("temp2.vrt", mask, projWin=geom).ReadAsArray()
    r = rasterio.open("temp1.vrt")
    affineO = r.transform
    del r
    for item in mask_value:
        MRO[np.where(MR2 == int(item))] = NoDataValue
    return MRO, affineO


def Do_Zonal_Stats(Path_dir, gdf, NoDataValue, mask_value, maskit=True):
    data = pd.read_csv(Path_dir)
    data = data.sort_values(['date'])
    zonelist = []
    stats_str = "min max median mean std percentile_25 percentile_75 count"

    print("Processing...")
    for idx, row in tqdm(data.iterrows(), total=data.shape[0]):
        if row['TS_Data'] == 1:
            raster = row['File']
            count = 0
            date = row['date']
            for idx, feature in gdf.iterrows():
                count += 1
                if maskit:
                    MR, affine = Mask_it(raster,
                                         row['Mask'],
                                         feature['geometry'],
                                         NoDataValue,
                                         mask_value)
                    statout = zonal_stats(feature["geometry"],
                                          MR,
                                          stats=stats_str,
                                          nodata=NoDataValue,
                                          affine=affine)
                if not maskit:
                    statout = zonal_stats(feature["geometry"],
                                          raster,
                                          stats=stats_str,
                                          nodata=NoDataValue)

                statout[0]['geometry'] = feature['geometry']
                statout[0]['ID'] = count
                statout[0]['date'] = pd.to_datetime(
                    date, infer_datetime_format=True)
                statout[0]['image'] = raster
                zonelist.append(statout[0])
    gdf2 = gpd.GeoDataFrame(zonelist)
    return gdf2


def Get_Num_Obs(Path_dir, gdf, NoDataValue, mask_value, maskit=True):
    data = pd.read_csv(Path_dir)
    data = data.sort_values(['date'])
    zonelist = []
    print("Getting number of observations...")
    for idx, row in tqdm(data.iterrows(), total=data.shape[0]):
        if row['obs'] == 1:
            raster = row['File']
            count = 0
            date = row['date']
            for idx, feature in gdf.iterrows():
                count += 1
                MR = raster
                if maskit:
                    MR, affine = Mask_it(raster,
                                         row['Mask'],
                                         feature['geometry'],
                                         NoDataValue,
                                         mask_value)
                    statout = zonal_stats(feature["geometry"],
                                          MR,
                                          stats="median",
                                          nodata=NoDataValue,
                                          affine=affine)

                if not maskit:
                    statout = zonal_stats(feature["geometry"],
                                          raster,
                                          stats="median",
                                          nodata=NoDataValue)

                # statout=zonal_stats(feature["geometry"],MR,stats="median")
                statout[0]['ID'] = count
                statout[0]['date'] = pd.to_datetime(
                    date, infer_datetime_format=True)
                zonelist.append(statout[0])

    gdf3 = gpd.GeoDataFrame(zonelist)
    return gdf3


def CSV_It(input_dir="", TSdata="S*rade9.tif",
           Observations="", Mask="", DateLoc="10:18", BandNum=""):
    # Ensuring the user entered everything properly
    input_dir = input_dir.strip()
    TSdata = TSdata.strip()
    Observations = Observations.strip()
    Mask = Mask.strip()
    DateLoc = DateLoc.strip()
    BandNum = BandNum.strip()

    assert len(TSdata) > 0, 'Error, no file list pattern defined. Exiting...'
    print("Pattern: {}".format(TSdata))

    assert len(
        Observations) > 0, 'Error, no Observations pattern entered. Exiting...'
    print("#Obs Pattern: {}".format(Observations))

    assert len(DateLoc) > 0, 'Error, no date pattern entered. Exiting...'
    print("Date location in filename: {}".format(DateLoc))

    band_mess = "Band location in filename: {}".format(BandNum) \
        if len(BandNum) > 0 else "No band number location entered"
    print(band_mess)

    mask_mess = "Mask band pattern: {}".format(Mask) \
        if len(Mask) > 0 else "No mask band entered"
    print(mask_mess)

    os.chdir(input_dir)
    # Identify all subdirs that contain our raster data
    input_subdirs = glob.glob('*/')
    print(len(input_subdirs))

    rasterList = []
    DateLoc = DateLoc.split(":")
    for directory in tqdm(input_subdirs):
        os.chdir(directory)
        # Find our primary rasters of interest
        FilePattern = glob.glob(TSdata)
        if len(Observations) > 0:
            Observations = [Observations]
            FilePattern = [x for x in FilePattern if not any(
                fnmatch(x, TSdata) for TSdata in Observations)]
            Observations = Observations[0]
        for raster in FilePattern:
            statout = [{}]
            statout[0]['File'] = input_dir+'/'+directory+'/'+raster
            rasterExtent = get_extent(raster)
            statout[0]['extent'] = rasterExtent
            date = raster[int(DateLoc[0]):int(DateLoc[1])]
            statout[0]['date'] = pd.to_datetime(
                date, infer_datetime_format=True)
            statout[0]['obs'] = 0
            statout[0]['TS_Data'] = 1
            # MAJOR ISSUE HERE, what is variable 'b'? #################
            if len(BandNum) > 0:
                BandNum = raster[int(BandNum[0]):int(BandNum[1])]
                # statout[0]['band_num'] = b
            if len(Mask) > 0:
                mask = glob.glob(Mask)[0]
                statout[0]['Mask'] = input_dir+'/'+directory+'/'+mask
            rasterList.append(statout[0])

        if len(Observations) > 0:
            FilePattern = glob.glob(Observations)
            for raster in FilePattern:
                statout = [{}]
                statout[0]['File'] = input_dir+'/'+directory+'/'+raster
                rasterExtent = get_extent(raster)
                statout[0]['extent'] = rasterExtent
                date = raster[int(DateLoc[0]):int(DateLoc[1])]
                statout[0]['date'] = pd.to_datetime(
                    date, infer_datetime_format=True)
                statout[0]['obs'] = 1
                statout[0]['TS_Data'] = 0
                if len(BandNum) > 0:
                    statout[0]['band_num'] = 0
                if len(Mask) > 0:
                    mask = glob.glob(Mask)[0]
                    statout[0]['Mask'] = input_dir+'/'+directory+'/'+mask
                rasterList.append(statout[0])

        os.chdir(input_dir)

    gdf = gpd.GeoDataFrame(rasterList)
    return gdf


LS_TSDATA_LISTS = {
    "coastal": ["LC08*band1.tif"],
    "blue": ['LE07*band1.tif', 'LT05*band1.tif', 'LC08*band2.tif'],
    "green": ['LE07*band2.tif', 'LT05*band2.tif', 'LC08*band3.tif'],
    "red": ['LE07*band3.tif', 'LT05*band3.tif', 'LC08*band4.tif'],
    "nir": ['LE07*band4.tif', 'LT05*band4.tif', 'LC08*band5.tif'],
    "swir1": ['LE07*band5.tif', 'LT05*band5.tif', 'LC08*band6.tif'],
    "swir2": ['LE07*band7.tif', 'LT05*band7.tif', 'LC08*band7.tif']
}


def get_ls_band(name=""):
    """
    Convenience function for retreiving predefined LandSat bands

    Parameters
    ----------
    name : {'coastal', 'blue', 'green', 'red', 'nir', 'swir1', swir2'}
        Name of band

    Returns
    -------
    list : list
        Predefined list of strings handles specific to band
    """
    name = name.lower()
    if name in LS_TSDATA_LISTS:
        tsdata = LS_TSDATA_LISTS[name]
        return tsdata
    else:
        raise ValueError('Unrecognized LandSat band {}.'
                         '\nLandSat band options are: {}'
                         .format(name, LS_TSDATA_LISTS.keys()))


def LS_CSV_It(input_dir="", TSdata="L*.tif",
              Mask="", DateLoc="10:18", Band="BLUE"):
    # Ensuring the user entered everything properly
    input_dir = input_dir.strip()
    TSdata = TSdata.strip()
    Mask = Mask.strip()
    DateLoc = DateLoc.strip()
    Band = Band.strip()

    assert len(TSdata) > 0, 'Error, no file list pattern defined. Exiting...'
    print("Pattern: {}".format(TSdata))

    assert len(DateLoc) > 0, 'Error, no date pattern entered. Exiting...'
    print("Date location in filename: {}".format(DateLoc))

    if len(Band) > 0:
        print("Band of interest:", Band)
        TSdata = get_ls_band(Band)
    else:
        print('No band entered, this is recommended for Landsat,'
              'unless you are working with an index like NDVI.')
        print('Options are: '.format(LS_TSDATA_LISTS.keys()))
        TSdata = [TSdata]

    mask_mess = "Mask band pattern: {}".format(Mask) \
        if len(Mask) > 0 else "No mask band entered"
    print(mask_mess)

    os.chdir(input_dir)
    # Identify all subdirs that contain our raster data
    input_subdirs = glob.glob('*/')
    print(len(input_subdirs))

    rasterList = []
    DateLoc = DateLoc.split(":")

    for directory in tqdm(input_subdirs):
        os.chdir(directory)
        # Find our primary rasters of interest
        FilePattern = []
        for item in TSdata:
            FilePattern.extend(glob.glob(item))
        for raster in FilePattern:
            statout = [{}]
            statout[0]['File'] = input_dir+'/'+directory+'/'+raster
            rasterExtent = get_extent(raster)
            statout[0]['extent'] = rasterExtent
            date = raster[int(DateLoc[0]):int(DateLoc[1])]
            statout[0]['date'] = pd.to_datetime(
                date, infer_datetime_format=True)
            statout[0]['obs'] = 0
            statout[0]['TS_Data'] = 1
            if len(Mask) > 0:
                mask = glob.glob(Mask)[0]
                statout[0]['Mask'] = input_dir+'/'+directory+'/'+mask
            rasterList.append(statout[0])

        os.chdir(input_dir)

    gdf = gpd.GeoDataFrame(rasterList)
    return gdf


def get_extent(raster):
    raster = gdal.Open(raster)
    rastergeo = raster.GetGeoTransform()
    minx = rastergeo[0]
    maxy = rastergeo[3]
    maxx = minx + rastergeo[1] * raster.RasterXSize
    miny = maxy + rastergeo[5] * raster.RasterYSize
    rasterExtent = [minx, maxy, maxx, miny]
    return rasterExtent
