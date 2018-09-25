from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
from sqlalchemy import create_engine
from zipfile import ZipFile
import os

def init_db(user,password,database):
	engine = create_engine('postgresql://{0}:{1}@localhost:5432/{2}'.format(user,password,database))
	return engine

def get_api(user,password):
	api = SentinelAPI(user,password, 'https://scihub.copernicus.eu/dhus')
	return api

def critical_test():
	# Vi skal huske at spørge om man faktisk vil downloade alle billeder"
	pass

def db_get_filenames(db_user,db_pass,id, schema, table_name, database):
	engine = init_db(db_user,db_pass,database)
	if isinstance(id, list):
		id = tuple(id)
		my_query = engine.execute("SELECT identifier from {1}.{0} where index in {2}".format(schema, table_name, id)).fetchall()
	elif isinstance(id,str):
		my_query = engine.execute("SELECT identifier from {1}.{0} where index in ('{2}')".format(schema, table_name, id)).fetchall()
	else:
		print("Der er noget galt med det ID der bruges ... Det skal være enten String eller en liste")
	return my_query

def download_metadata(db_user,db_pass,api_user,api_pass,table_name='metadata',schema='satellit',database='afstand',platformname='Sentinel-2',aoi='aoi_4326.geojson'):
	api = get_api(api_user,api_pass)
	engine = init_db(db_user,db_pass,database)
	footprint = geojson_to_wkt(read_geojson(aoi))
	products = api.query(footprint,
			     date=('20150623', 'NOW'),
			     platformname=platformname,
			     cloudcoverpercentage=(0,100))
	products_df = api.to_dataframe(products)
	products_df.to_sql(table_name, engine, schema=schema,if_exists='replace')
	print("Metadata updated in database")


def download_file(db_user,db_pass,api_user,api_pass,id,table_name='metadata', schema='satellit', database='afstand'):
	api = get_api(api_user,api_pass)
	if isinstance(id,list):
	#query = db_get_filenames(db_user,db_pass,id, table_name, schema, database)
		#api.download_all(id,'data')
		unzip_file(id,db_user,db_pass,table_name,schema,database,list=True)
	else:
		#api.download(id)
		unzip_file(id,db_user,db_pass,table_name,schema,database,list=False)

def unzip_file(id, db_user,db_pass,table_name,schema,database,list,folder='data'):
	query = db_get_filenames(db_user,db_pass,id,table_name,schema,database)
	my_list = [element[0] for element in query]
	for element in my_list:
		file_name = folder + '/' + element + '.zip'
		with ZipFile(file_name, 'r') as zip_ref:
			zip_ref.extractall(folder)
			zip_ref.close()

def delete_zips(folder='data',id=None):
	my_zips = os.listdir(folder)
	for file in my_zips:
		if file.endswith('.zip'):
			os.remove(folder + "/" + file)

def download_thumbnails(db_user,db_pass,folder='data',id=None,database='afstand'):
	engine = init_db(db_user,db_pass,database)
	if id is None:
		my_files = os.listdir(folder)
		query = engine.execute('select * from satellit.metadata where filename in {0}'.format(tuple(my_files))).fetchall()
		print(query)
#download_metadata('emil','12345','hy42','PqwurxnX1','metadata')
#download_file('emil','12345','hy42','PqwurxnX1','026b9f03-3d50-43b3-bec5-8204e8c8a442')
#download_file('emil','12345','hy42','PqwurxnX1',['026b9f03-3d50-43b3-bec5-8204e8c8a442','0026c920-f7dc-466b-90fa-e0cb4d79818e'])
download_thumbnails('emil','12345')
