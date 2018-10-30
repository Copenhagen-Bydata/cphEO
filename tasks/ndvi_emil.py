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

# Test datasets
redImg = "output/aoi/25b13005-f5ba-404b-9ae3-cbfd9525388e/T33UUB_20180704T103021_B04.tif"
nirImg = "output/aoi/25b13005-f5ba-404b-9ae3-cbfd9525388e/T33UUB_20180704T103021_B08.tif"

# CREATE OVERALL NDVI
def overall_ndvi(id,make_aoi=False):
    if make_aoi==True:
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
        location = "output/aoi/" + str(id)
        with rasterio.open(redImg) as red:
             red_meta = red.meta.copy()
             red_image = red.read(1)
        with rasterio.open(nirImg) as nir:
             nir_meta = nir.meta.copy()
             nir_image = nir.read(1)
        #print(nir_image, red_image)
        #from skimage import io
        #red_image = io.imread(redImg)
        #nir_image = io.imread(nirImg)
        np.seterr(divide='ignore', invalid='ignore')
        ndvi = np.divide((nir_image.astype(float) - red_image.astype(float)), (nir_image + red_image))
        outputPlace = "NDVI.tif"
        nir_meta.update(dtype=ndvi.dtype)
        #rasterio_writer(redImg, outputPlace, ndvi)
        #io.imsave(outputPlace, ndvi)
        with rasterio.open(outputPlace, "w", **nir_meta) as dest:
            dest.write(ndvi,1)

#overall_ndvi(redImg,nirImg,make_aoi=False)

def rasterio_reader(inputTIF):
	with rasterio.open(inputTIF) as src:
		image = src.read(1)
		image_meta = src.meta.copy()
	return image, image_meta

def rasterio_writer_2(outputLocation, data, metadata):
	with rasterio.open(outputLocation, 'w', **metadata) as dest:
		dest.write(data, 1)

def rasterio_writer(InputTIF,OutputTIF,data = None):
    with rasterio.open(InputTIF) as src:
        out_meta = src.meta.copy()
        out_image = src.read(1)
    out_meta.update(dtype=data.dtype)
    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        if data.any() != None:
            dest.write(data,1)
        else:
            pass

#CALCULATE GREEN AREAS
def calculate_green(NDVI,outputLoc=None):
    ndviOrg, meta = rasterio_reader(NDVI)
    #ndviNew = ndviOrg.copy()
    for i in range(len(ndviOrg)):
        for ii in range(len(ndviOrg[i])):
            if ((ndviOrg[i][ii] >= 0.2) & (ndviOrg[i][ii] <= 0.9)) == True:
                ndviOrg[i][ii] = 1
            elif ((ndviOrg[i][ii] >= 0.2) & (ndviOrg[i][ii] <= 0.9)) == False:
                ndviOrg[i][ii] = 0
    rasterio_writer_2("green.tif", ndviOrg, meta) 
    #rasterio_writer(NDVI,outputLoc, ndviNew)
    #return outputLoc

def get_proj4(InputTIF):
    srs = osr.SpatialReference()
    src = gdal.Open(InputTIF)
    projsrc = src.GetProjection()
    srs.ImportFromWkt(projsrc)
    proj4 = srs.ExportToWkt()
    return proj4

def masker_iter(with_cleanup=False):
    from tasks.download_sentinel import init_db
    from tasks.download_sentinel import inventory_create
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
            from tasks.download_sentinel import inventory_create
            inventory_create('emil','12345','afstand')

def masker(InputTIF, id, OutputTIF='output/aoi', name_add=None, InputSHP='data/aux/kbh_32633.shp', invert=False):
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
    name = os.path.basename(InputTIF)
    name = name.split("_")
    OutputTIF=out_path + "/" + name[2]
    with rasterio.open(OutputTIF, "w", **out_meta) as dest:
        dest.write(out_image)
    return OutputTIF, base



def groenneOmraader(InputTIF):
    os.path.basename(InputTIF)

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
def calculate_stats(inputTIF,outputLoc):
    statistics = []
    array, meta = rasterio_reader(inputTIF)
    unique, counts = np.unique(array, return_counts=True)
    totalPixels = len(array)*len(array[0])
    m2Total = totalPixels*100
    m2Green = counts[1]*100
    km2Total = round(m2Total / 1000000, 4)
    km2Green = round(m2Green / 1000000, 4)
    percentage = round((m2Green*100)/m2Total, 4)
    statistics.append([totalPixels, m2Total, m2Green, km2Total, km2Green, percentage])
    statisticsDF = pd.DataFrame(statistics,
                                columns=(['total pixels', 'm2Total', 'm2Green', 'km2Total', 'km2Green', 'percGreen']))
    df = statisticsDF.copy()
    df.to_csv(outputLoc, index=True, sep=";", index_label='Area Type')

#calculate_green("NDVI.tif")
#calculate_stats("green.tif","stats.csv")
#ndviLoc, greenLoc = overall_ndvi(redImg,nirImg)
#green_loc = calculate_green(ndviLoc,greenLoc)
# Subtract buildings
#masker(green_loc,name_add='_udenbyg',InputSHP='data/aux/BYGNING_EPSG32633_Clip_Dissolved.shp')
#masker(greenLoc,name_add='_privat',InputSHP='data/aux/kbh_u_byg_erase.shp')

