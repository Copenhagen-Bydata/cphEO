#IMPORTS NDVI ONE-GO
import time

import numpy as np
import pandas as pd
from skimage import io
import gdal
from osgeo import osr
import fiona
import rasterio
import rasterio.mask
from pathlib import Path
import os, os.path
import shutil

# Set locations of files
#redImg = "SatImg_raadata/2015_B04_clip.tif"
#nirImg = "SatImg_raadata/2015_B08_clip.tif"

#S2B_MSIL2A_20180420T103019_N0207_R108_T33UUB_20180420T114307.SAFE
#data/S2A_MSIL1C_20180704T103021_N0206_R108_T33UUB_20180704T174024.SAFE/GRANULE/L1C_T33UUB_A015835_20180704T103023/IMG_DATA
redImg = "data/S2A_MSIL1C_20180704T103021_N0206_R108_T33UUB_20180704T174024.SAFE/GRANULE/L1C_T33UUB_A015835_20180704T103023/IMG_DATA/T33UUB_20180704T103021_B04.jp2"
nirImg = "data/S2A_MSIL1C_20180704T103021_N0206_R108_T33UUB_20180704T174024.SAFE/GRANULE/L1C_T33UUB_A015835_20180704T103023/IMG_DATA/T33UUB_20180704T103021_B08.jp2"
clipBuild = 'Shapefiles/NDVI/UdenBygninger.shp'
clipPrivat = 'Shapefiles/NDVI/Villaer.shp'
clipPublic = 'Shapefiles/NDVI/Offentlig.shp'
clipPublicKnown = 'Shapefiles/NDVI/KendtGroen.shp'
clipPublicNotKnown = 'Shapefiles/NDVI/IkkeKendtGroen.shp'

# CREATE OVERALL NDVI
def overall_ndvi(redImg,nirImg,aoi=True):
    if aoi==True:
        red_aoi, name = masker(redImg)
        nir_aoi, name = masker(nirImg)
        from skimage import io
        red = io.imread(red_aoi)
        nir = io.imread(nir_aoi)
        ndvi = (nir - red) / (nir + red)
        outputPlace = os.path.dirname(nir_aoi) + "/" + name.split("_")[0] + "_" +name.split("_")[1] + "_NDVI.tif"
        io.imsave(outputPlace, ndvi)
        rasterio_writer(red_aoi,outputPlace,ndvi)
        outputLoc = os.path.dirname(nir_aoi) + "/" + name.split("_")[0] + "_" + name.split("_")[1]  + "_GREEN.tif"
        return outputPlace,outputLoc
    else:
        pass


def rasterio_writer(InputTIF,OutputTIF,data = None):
    with rasterio.open(InputTIF) as src:
        out_meta = src.meta.copy()
        out_image = src.read(1)
    out_meta.update(dtype=data.dtype)
    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        if data.any() != None:
            dest.write(data,1)
        else:
            dest.write(out_image)

# CALCULATE GREEN AREAS
def calculate_green(NDVI,outputLoc=None):
    ndviOrg = io.imread(NDVI)
    ndviNew = ndviOrg.copy()
    for i in range(len(ndviNew)):
        for ii in range(len(ndviNew[i])):
            if ((ndviNew[i][ii] >= 0.2) & (ndviNew[i][ii] <= 0.9)) == True:
                ndviNew[i][ii] = 1
            elif ((ndviNew[i][ii] >= 0.2) & (ndviNew[i][ii] <= 0.9)) == False:
                ndviNew[i][ii] = 0
    rasterio_writer(NDVI,outputLoc, ndviNew)
    return outputLoc

# REPROJECT IMAGE
def reproject_image(redImg):
    # Get projection and transform data from file (has to have same rows,col and start coordinate)
    src = gdal.Open(redImg)
    proj = src.GetProjection()
    ulx, xres, xskew, uly, yskew, yres  = src.GetGeoTransform()
    lrx = ulx + (src.RasterXSize * xres)
    lry = uly + (src.RasterYSize * yres)

# load data and set output location
def load_numpy_data():
    array = np.asarray(io.imread(NDVI_GreenAreas_WGS84))
    outputLoc = NDVI_GreenAreas
    x = len(array[0])
    y = len(array)

# Create new tif-file, add projection/coordinates, add data
def create_new_tif():
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(outputLoc, x, y, 1)
    dst_ds.SetGeoTransform(src.GetGeoTransform())
    dst_ds.SetProjection(proj)
    ulx, xres, xskew, uly, yskew, yres  = dst_ds.GetGeoTransform()
    lrx = ulx + (dst_ds.RasterXSize * xres)
    lry = uly + (dst_ds.RasterYSize * yres)
    projNew = dst_ds.GetProjection()
    dst_ds.GetRasterBand(1).WriteArray(array)

def get_proj4(InputTIF):
    srs = osr.SpatialReference()
    src = gdal.Open(InputTIF)
    projsrc = src.GetProjection()
    srs.ImportFromWkt(projsrc)
    proj4 = srs.ExportToWkt()
    return proj4

def masker_iter(with_cleanup=False):
    from tasks.download_sentinel import init_db
    engine = init_db('emil','12345','afstand')
    #from ndvi_emil import masker
    for element in os.listdir("data"):
        if element.endswith(".SAFE"):
            granule = "data/" + element + "/GRANULE/"
            my_file = os.listdir(granule)
            file_dir = "data/" + element + "/GRANULE/" +  my_file[0] + "/IMG_DATA/"
            for file in os.listdir(file_dir):
                final_dir = file_dir + "/" + str(file)
                id = engine.execute("select index from satellit.s2_metadata where filename = '{0}'".format(element)).fetchone()
                masker(final_dir,id[0])
            if with_cleanup:
                shutil.rmtree("data/" + element)
            from download_sentinel import inventory_create
            inventory_create('emil','12345','afstand')

def masker(InputTIF, id, OutputTIF='output/aoi', name_add=None, InputSHP='data/aux/klipper_32633.shp', invert=False):
    # CLIP IMAGE WITH SHAPEFILES
    if name_add is None:
        name_add = ''
    print(InputTIF)
    base = os.path.basename(InputTIF)
    base = os.path.splitext(base)[0] + name_add
    img_name = base.split("_")
    out_path = OutputTIF + "/" + id
    if os.path.exists(out_path):
        pass
    else:
        os.makedirs(out_path, exist_ok=True)

    proj4 = get_proj4(InputTIF)

    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]
    with rasterio.open(InputTIF) as src:
        out_meta = src.meta.copy()
        if invert==False:
            out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        else:
            out_image, out_transform = rasterio.mask.mask(src, features, crop=False,invert=True, filled=False)
    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform,
                 "crs": proj4})

    OutputTIF=out_path + "/" + base + ".tif"
    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)
    return OutputTIF, base



def privatGreen(InputTIF, OutputTIF, InputSHP):
    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    with rasterio.open(InputTIF) as src:
        out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()
    proj4 = get_proj4(inputTIF)
    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform,
                 "crs": proj4})

    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)

# CALCULATE STATISTICS
def calculate_stats():
    outputs = [NDVI_GreenAreas, outputNoBuild, outputPrivat, outputPublic, outputPublicKnown, outputPublicNotKnown]
    statistics = []
    for i in range(len(outputs)):
        array = io.imread(outputs[i])
        unique, counts = np.unique(array, return_counts=True)
        totalPixels = len(array)*len(array[0])
        m2Total = totalPixels*100
        m2Green = counts[1]*100
        km2Total = round(m2Total / 1000000, 4)
        km2Green = round(m2Green / 1000000, 4)
        percentage = round((m2Green*100)/m2Total, 4)
        statistics.append([totalPixels, m2Total, m2Green, km2Total, km2Green, percentage])
    statisticsDF = pd.DataFrame(statistics, index='NDVI_GreenAreas, outputNoBuild, outputPrivat, outputPublic, outputPublicKnown, outputPublicNotKnown'.split(', '),
                                columns=(['total pixels', 'm2Total', 'm2Green', 'km2Total', 'km2Green', 'percGreen']))
    df = statisticsDF.copy()
    outputLoc = outputStatistics
    df.to_csv(outputLoc, index=True, index_label='Area Type')

#ndviLoc, greenLoc = overall_ndvi(redImg,nirImg)
#green_loc = calculate_green(ndviLoc,greenLoc)
# Subtract buildings
#masker(green_loc,name_add='_udenbyg',InputSHP='data/aux/BYGNING_EPSG32633_Clip_Dissolved.shp')
#masker(greenLoc,name_add='_privat',InputSHP='data/aux/kbh_u_byg_erase.shp')

