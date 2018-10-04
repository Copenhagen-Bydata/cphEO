#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask,jsonify
#from flask_sqlalchemy import SQLAlchemy
import psycopg2, json
import multiprocessing

def init_db(db_user,db_pass,database):
	conn = psycopg2.connect("dbname={0} user={1} password={2} host=localhost port=5432".format(database,db_user,db_pass))
	cur = conn.cursor()
	return cur

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{0}:{1}@localhost:5432/{2}'.format('emil','12345','afstand')
#db = SQLAlchemy(app)
#from models.models import S2_Metadata

@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/metadata/reset")
def reset_metadata():
	# Her skal man kunne initiere eller lave reset på metadata
	db_user, db_pass, api_user, api_pass = 'emil','12345','hy42','PqwurxnX1'
	from download_sentinel import download_metadata
	thread = multiprocessing.Process(target=download_metadata, args=(db_user, db_pass, api_user, api_pass))
	thread.start()
	return "Resetting"

@app.route("/metadata/<table>")
def metadata(table):
	cur = init_db('emil','12345','afstand')
	cur.execute("SELECT * from satellit.{0}".format(table))
	my_metadata = cur.fetchall()
	# Lige nu faar man al data i metadatatabellen
	return jsonify(my_metadata)

@app.route("/download/<image_id>")
def download_image(image_id):
	# Her kan man downloade et specifikt billede
	return "Hello"

@app.route("/download/all")
def download_all():
	# Her kan man downloade alle billeder
	return "Hello"

@app.route("/cleanup/all")
def cleanup_all():
	# Denne kommando skal slette alle zip filer for at rydde op paa serveren
	return "Hello"

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
