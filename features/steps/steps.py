import os
from flask import Flask
from app import *
from flask_mysqldb import MySQL
from behave import given, when, then

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def before_scenario(context, scenario):
    global app
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'cse'
    app.config['MYSQL_PASSWORD'] = 'cse'
    app.config['MYSQL_DB'] = 'cse'
    app.mysql = MySQL(app)
    app.before_first_request(create_db)

@given('The system is starting')
def step_system_starting(context):
    pass

@when('The application initializes')
def step_application_initializes(context):
    global app
    with app.app_context():
        create_db()

@then('Database tables should be created')
def step_tables_created(context):
    global app
    with app.app_context():
    
        cur = app.mysql.connection.cursor()
        cur.execute("SHOW TABLES LIKE 'users';")
        users_table = cur.fetchone() is not None
        cur.execute("SHOW TABLES LIKE 'bids';")
        bids_table = cur.fetchone() is not None
        cur.execute("SHOW TABLES LIKE 'offers';")
        offers_table = cur.fetchone() is not None
        cur.close()

        assert users_table, "The 'users' table should exist after the call of create_db"
        assert bids_table, "The 'bids' table should exist after the call of create_db"
        assert offers_table, "The 'offers' table should exist after the call of create_db"

