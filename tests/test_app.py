import pytest
from flask import Flask, request,render_template
from app import *
from flask_mysqldb import MySQL
from unittest.mock import patch, MagicMock
from behave import given, when, then

# For local testing, have app.py running and run this from root: python -m pytest -v tests/test_app.py

def test_dummy():
    pass

def test_dummy_func():
    assert dummy_func(1) == 1

"""
# --- Testing for successful db init ----------------------------------------
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'cse'
    app.config['MYSQL_PASSWORD'] = 'cse'
    app.config['MYSQL_DB'] = 'cse'
    app.mysql = MySQL(app) 
    app.before_first_request(create_db)
    return app
    

def test_db_initialization(app):
    with app.test_request_context():
        create_db()

    # Checking if the tables exist in the db
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



def test_fetch_and_store_aapl_data_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {'example_key': 'example_value'}

    with patch('requests.get', return_value=mock_response):
        fetch_and_store_aapl_data()

    # Asserting that the global variables are updated
    assert 'latest_data' in globals()
    assert 'last_updated' in globals()

def test_fetch_and_store_aapl_data_failure():

    with patch('requests.get', side_effect=requests.exceptions.RequestException('Mocked error')):
        fetch_and_store_aapl_data()

    # Asserting that the global variables remain unchanged
    assert latest_data is None
    assert last_updated is None


# Testing data fetch
def test_fetch_and_store_aapl_data_success():
    url = "http://localhost:5000/aapl_data"
    response = requests.get(url)
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert response.json()["data"] is not None


# TODO: Update, when related function finished
# Transaction success is false and data is stored, since no
# data in tables and no functionality yet created for matching offers and bids

def test_bid_with_valid_values():
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=175.26&quantity=500&user_id=1"
    response = requests.post(url)
    assert response.status_code == 200
    assert response.json()["success"] is False

# TODO: Update, when related function finished
# Transaction success is false and data is not stored

def test_bid_with_valid_values():
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=100.55&quantity=500&user_id=1"
    response = requests.post(url)
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid price or quantity, no action taken"
"""
