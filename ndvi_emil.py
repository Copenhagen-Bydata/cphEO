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
import os.path

# Set locations of files
#redImg = "SatImg_raadata/2015_B04_clip.tif"
#nirImg = "SatImg_raadata/2015_B08_clip.tif"
redImg = "data/S2A_MSIL1C_20171027T103131_N0206_R108_T33UUB_20171027T141000.SAFE/GRANULE/L1C_T33UUB_A012260_20171027T103128/IMG_DATA/T33UUB_20171027T103131_B04.jp2"
nirImg = "data/S2A_MSIL1C_20171027T103131_N0206_R108_T33UUB_20171027T141000.SAFE/GRANULE/L1C_T33UUB_A012260_20171027T103128/IMG_DATA/T33UUB_20171027T103131_B08.jp2"
NDVI = 'output/2017_NDVI.tif'
NDVI_GreenAreas_WGS84 = 'Outputs/NDVI/2015_NDVI_GroeneOmraader.tif'
NDVI_GreenAreas = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_reproj.tif'
outputNoBuild = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_UdenByg.tif'
outputPrivat = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_Privat.tif'
outputPublic = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_Offentlig.tif'
outputPublicKnown = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_Offentlig_Kendt.tif'
outputPublicNotKnown = 'Outputs/NDVI/2015_NDVI_GroeneOmraader_Offentlig_ikkeKendt.tif'
outputStatistics = 'Outputs/NDVI/2015_Statistics_NDVI.csv'
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
        outputPlace = os.path.dirname(nir_aoi) + "/" + name + "_NDVI.tif"
        io.imsave(outputPlace, ndvi)
        outputLoc = os.path.dirname(nir_aoi) + "/" + name + "_GREEN.tif"
        calculate_green(outputPlace,outputLoc=outputLoc)
    else:
        pass

# CALCULATE GREEN AREAS
def calculate_green(NDVI,outputLoc=NDVI_GreenAreas_WGS84):
    ndviOrg = io.imread(NDVI)
    ndviNew = ndviOrg.copy()
    for i in range(len(ndviNew)):
        for ii in range(len(ndviNew[i])):
            if ((ndviNew[i][ii] >= 0.2) & (ndviNew[i][ii] <= 0.9)) == True:
                ndviNew[i][ii] = 1
            elif ((ndviNew[i][ii] >= 0.2) & (ndviNew[i][ii] <= 0.9)) == False:
                ndviNew[i][ii] = 0
    io.imsave(outputLoc, ndviNew)

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

# Close open files
def cleanup():
    src = None
    dst_ds = None

def get_proj4(InputTIF):
    srs = osr.SpatialReference()
    src = gdal.Open(InputTIF)
    projsrc = src.GetProjection()
    srs.ImportFromWkt(projsrc)
    proj4 = srs.ExportToWkt()
    return proj4

def masker(InputTIF, OutputTIF='output/aoi', InputSHP='data/aux/klipper_32633.shp'):
    # CLIP IMAGE WITH SHAPEFILES
    base = os.path.basename(InputTIF)
    img_name = base.split("_")
    img_out_name = os.path.splitext(base)[0] + "_" + os.path.splitext(base)[1]
    print(img_out_name)
    out_path = OutputTIF + "/" + img_name[0]
    if os.path.exists(out_path):
        pass
    else:
        os.mkdir(out_path)
    proj4 = get_proj4(InputTIF)
    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    with rasterio.open(InputTIF) as src:
        out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform,
                 "crs": proj4})

    OutputTIF=out_path + "/" + name + ".tif"
    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)
    return OutputTIF, img_out_name

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

def publicGreen(InputTIF, OutputTIF, InputSHP):
    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    with rasterio.open(InputTIF) as src:
        out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()

    proj4 = get_proj4(InputTIF)

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform,
                 "crs": proj4})

    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)

def knownGreen(InputTIF, OutputTIF, InputSHP):
    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    with rasterio.open(InputTIF) as src:
        out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()
    proj4 = get_proj4(InputTIF)
    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform,
                 "crs": proj4})

    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)

def notKnownGreen(InputTIF, OutputTIF, InputSHP):
    with fiona.open(InputSHP, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    with rasterio.open(InputTIF) as src:
        out_image, out_transform = rasterio.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()

    proj4 = get_proj4(InputTIF)
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

overall_ndvi(redImg,nirImg)
