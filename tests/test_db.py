import pytest
from flask import Flask, request,render_template
from app import *
from flask_mysqldb import MySQL
from unittest.mock import patch, MagicMock
#from behave import given, when, then

# For local testing, have app.py running and run this from root: python -m pytest -v tests/test_app.py

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
    print(app)
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

def remove_rows(app):
    with app.app_context():
        cur = app.mysql.connection.cursor()
        cur.execute("DELETE FROM bids;")
        cur.execute("DELETE FROM offers;")
        cur.execute("DELETE FROM trades;")
        mysql.connection.commit()
        cur.close()

# Testing first bid
def test_bid_with_valid_values(app):
    remove_rows(app)
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=175.26&quantity=500&user_id=1"
    response = requests.post(url)

    with app.app_context():
        cur = app.mysql.connection.cursor()
        cur.execute("SELECT user_id, bid_quantity, bid_price FROM bids;")
        bid = cur.fetchone()
        user_id = bid[0]
        bid_quantity = bid[1]
        bid_price = bid[2]
        cur.close()
    assert 1 == user_id
    assert 500 == bid_quantity
    assert 175.26 == bid_price
    assert response.status_code == 200
    assert response.json()["success"] is False

def test_offer_with_matching_bid(app):
    remove_rows(app)
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=175.00&quantity=500&user_id=1"
    requests.post(url)
    url = "http://localhost:5000/bid_or_offer?action_type=offer&price=170.00&quantity=500&user_id=2"
    requests.post(url)
    with app.app_context():
        cur = app.mysql.connection.cursor()
        cur.execute("SELECT * FROM bids;")
        bid = cur.fetchone()
        cur.execute("SELECT * FROM offers;")
        offer = cur.fetchone()
        cur.execute("SELECT trade_price, trade_quantity FROM trades;")
        trade = cur.fetchone()
        cur.close()
    assert bid == None
    assert offer == None
    assert 175.00 == trade[0]
    assert 500 == trade[1]
    
def test_offer_with_not_matching_bid(app):
    remove_rows(app)
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=170.00&quantity=500&user_id=1"
    requests.post(url)
    url = "http://localhost:5000/bid_or_offer?action_type=offer&price=175.00&quantity=500&user_id=2"
    requests.post(url)
    with app.app_context():
        cur = app.mysql.connection.cursor()
        cur.execute("SELECT bid_price FROM bids;")
        bid = cur.fetchone()
        cur.execute("SELECT offer_price FROM offers;")
        offer = cur.fetchone()
        cur.execute("SELECT * FROM trades;")
        trade = cur.fetchone()
        cur.close()
    assert bid[0] == 170.00
    assert offer[0] == 175.00
    assert trade == None

def test_scenario1(app):
    """
    Based on E2E scenario 1. from the project details.
    a. Fetch current market last trade price of AAPL - example M1
    b. Verify Bid order at Price M1 x 1.08 is accepted
    c. Verify Offer order at Price M1 x 0.90 is accepted
    d. Verify Bid order at Price M1 x 1.11 is rejected
    e. Verify Offer order at Price M1 x -1.01 is rejected
    f. Verify no trades have happened
    """
    remove_rows(app)

    M1 = 170        
    try:
        response = requests.get("http://localhost:5000/aapl_data")
        data = response.json()
        # Lets use ask for last traded price, should not matter for testing.
        M1 = data["data"]["ask"][0]
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M1*1.08}&quantity={1}&user_id={1}")
    assert response.status_code == 200
    
    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M1*0.9}&quantity={1}&user_id={1}")
    assert response.status_code == 200
    
    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M1*1.11}&quantity={1}&user_id={1}")
    assert response.status_code == 400
    
    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M1*-1.01}&quantity={1}&user_id={1}")
    assert response.status_code == 400
    
    try:
        response = requests.get("http://localhost:5000/trades")
        data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    trades_length = len(data["data"])
    
    assert trades_length == 0 


def test_scenario2(app):
    """
    Based on E2E scenario 2. from the project details.
    a. Fetch current market last trade price of AAPL - M2
    b. Bid order at Price M2, Qty 0 is rejected
    c. Bid order at Price M2, Qty 10.1 is rejected
    d. Offer order at Price M2, Qty -100 is rejected
    e. Verify no trades have happened
    """
    remove_rows(app)

    M2 = 170        
    try:
        response = requests.get("http://localhost:5000/aapl_data")
        data = response.json()
        # Lets use ask for last traded price, should not matter for testing.
        M2 = data["data"]["ask"][0]
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M2}&quantity={0}&user_id={1}")
    assert response.status_code == 400
    
    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M2}&quantity={10.1}&user_id={1}")
    assert response.status_code == 400
    
    response = requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M2}&quantity={-100}&user_id={1}")
    assert response.status_code == 400
    
    try:
        response = requests.get("http://localhost:5000/trades")
        data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    trades_length = len(data["data"])
    
    assert trades_length == 0 

def test_scenario3(app):
    """
    Based on E2E scenario 3. from the project details.
    a. Fetch current market last trade price of AAPL - M3
    b. Ord 1 - Bid Price: M3, Qty: 100
    c. Ord 2 - Offer, Price: M3 x 0.8, Qty: 200
    d. Ord 3 - Bid Price: M3 x 1.01, Qty: 200
    e. Ord 4 - Bid Price: M3 x 0.95, Qty: 50
    f. Ord 5 - Bid Price: M3, Qty: 30
    g. Ord 6 - Offer, Price: M3, Qty 250 - T1
    h. Fetch trades
        i. Expected:
            Trades
            Time    Price       Quantity
            T1      M3 x 1.01   200
            T1      M3          50
    """
    remove_rows(app)

    M3 = 170        
    try:
        response = requests.get("http://localhost:5000/aapl_data")
        data = response.json()
        # Lets use ask for last traded price, should not matter for testing.
        M3 = data["data"]["ask"][0]
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M3}&quantity={100}&user_id={1}")
    requests.post(f"http://localhost:5000/bid_or_offer?action_type=offer&price={M3*0.8}&quantity={200}&user_id={2}")
    requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M3*1.01}&quantity={200}&user_id={1}")
    requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M3*0.95}&quantity={50}&user_id={1}")
    requests.post(f"http://localhost:5000/bid_or_offer?action_type=bid&price={M3}&quantity={30}&user_id={1}")
    requests.post(f"http://localhost:5000/bid_or_offer?action_type=offer&price={M3}&quantity={250}&user_id={2}")
    
    try:
        response = requests.get("http://localhost:5000/trades")
        data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

    trade0 = data["data"][0]
    trade1 = data["data"][1]
    
    assert trade0["price"] == round(M3*1.01, 2)
    assert trade0["quantity"] == 200
    assert trade1["price"] == M3
    assert trade1["quantity"] == 50


def test_bid_with_not_valid_values():
    url = "http://localhost:5000/bid_or_offer?action_type=bid&price=100.55&quantity=500&user_id=1"
    response = requests.post(url)
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid price or quantity, no action taken"