#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask,jsonify, render_template, request
import psycopg2, json
import multiprocessing
#from celery import Celery
from celery import Celery

app = Flask(__name__)

def make_celery(flask_app):
    celery = Celery(
        flask_app.import_name,
        backend=flask_app.config['CELERY_RESULT_BACKEND'],
        broker=flask_app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(flask_app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)
celery = make_celery(app)

def init_db(db_user,db_pass,database):
	conn = psycopg2.connect("dbname={0} user={1} password={2} host=localhost port=5432".format(database,db_user,db_pass))
	cur = conn.cursor()
	return cur

@celery.task()
def add_together(a,b):
        return a + b

@app.route('/add/<int:x>/<int:y>')
def calculate(x, y):
	from cpheo import add_together
	job = add_together.delay(1, 2)
	job.wait()
	return "Hello"

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
	cur.execute("SELECT index,cloudcoverpercentage,ingestiondate,thumb_loc,endposition from satellit.{0} order by ingestiondate desc".format(table))
	my_metadata = cur.fetchall()
	# Lige nu faar man al data i metadatatabellen
	return render_template('metadata_show.html', metadata=my_metadata)


@app.route("/download/<image_id>")
def download_image(image_id):
	from download_sentinel import download_file
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
    app.run(host='0.0.0.0')
