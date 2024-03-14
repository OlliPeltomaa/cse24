from flask import Flask, jsonify, request,render_template
import requests
from flask_cors import CORS
import datetime
import mysql.connector

# For local testing, have mysql db running, with database named 'cse' and user 'cse' created:
"""
  sudo mysql -u root -p

  CREATE DATABASE cse;
  CREATE USER 'cse'@'localhost' IDENTIFIED BY 'cse';
  GRANT ALL PRIVILEGES ON cse.* TO 'cse'@'localhost';
  FLUSH PRIVILEGES;

  EXIT;
  
"""

# Note: Avoid possible compability issues with
"""
Python 3.10.12
Flask 2.1.3
Werkzeug 1.0.1
"""

app = Flask(__name__)
# Enabling CORS for all routes
CORS(app)

latest_data = None
last_updated = None
reasonable_limit = 10000


db = mysql.connector.connect(
  host="localhost",
  user="cse",
  password="cse",
  database="cse"
)

# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'cse'
# app.config['MYSQL_PASSWORD'] = 'cse'
# app.config['MYSQL_DB'] = 'cse'
# mysql = MySQL(app)

def return_app():
    return app

def valid_price(price, reference):
    # Is the price within 10 percent margin from the reference?
    margin = 0.1 * reference
    return (reference - margin) <= price <= (reference + margin)

# is the quantity of bid or offer valid
def valid_quantity(quantity):
    # floating quantity not accepted
    if isinstance(quantity, float):
        return False
    # quantity has to be larger than 0
    if quantity <= 0:
        return False

    return True

# Can be locally tested with such approach for example
#curl -X POST "http://localhost:5000/bid_or_offer?action_type=bid&price=175.26&quantity=500&user_id=1"
@app.route('/bid_or_offer', methods=['POST'])
def bid_or_offer():
    try:
        action_type = request.args.get('action_type', type=str)
        price = request.args.get('price', type=float)
        quantity = request.args.get('quantity', type=int)
        user_id = request.args.get('user_id', type=int)       
        reference = None
        
        if latest_data == None:
            fetch_and_store_aapl_data()
        
        print("T1: ", latest_data)

        if action_type.lower() == "bid":
            print("T2: ", latest_data['bid'][0])
            reference = latest_data['bid'][0]        
        elif action_type.lower() == "offer":
            reference = latest_data['ask'][0]
        if not (isinstance(price, float) or not valid_price(price, reference) or not valid_quantity(quantity)):
            return jsonify({"error": "Invalid price or quantity, no action taken"}), 400

        if action_type.lower() == "bid":
            #------------------ Db-matching and functionalities ------------------
            cur = db.cursor()
            # Offers that match the bid amount
            # lowest offer first, same price orders ordered by timestamp, oldest first.
            cur.execute(f"SELECT offer_order_id, user_id, offer_price, offer_quantity FROM offers WHERE offer_price <= {price} ORDER BY offer_price ASC, offer_timestamp ASC")
            result = cur.fetchall()
            has_instances = len(result) > 0
            if has_instances:
                print("T3")
                offers_to_be_removed, offers_to_be_updated, trades_to_be_created, quantities_left = match_bid_to_offers(quantity,result)         

                for (id,q) in offers_to_be_updated:
                    cur.execute(f"UPDATE offers SET offer_quantity = {q} WHERE offer_order_id = {id}")
                
                for o in offers_to_be_removed:
                    cur.execute(f"DELETE FROM offers WHERE offer_order_id = {o}")
                
                for (o,p,q) in trades_to_be_created:
                    cur.execute("INSERT INTO trades (bidder_id, offerer_id, trade_price, trade_quantity) VALUES (%s, %s, %s, %s)",
                                                                                                                (user_id, o, p, q))
                # create bid if there is quantities left
                if (quantities_left > 0):
                    cur.execute("INSERT INTO bids (user_id, bid_price, bid_quantity) VALUES (%s, %s, %s)", 
                                                                                                (user_id, price, quantities_left)) 
                db.commit()
                cur.close()
                return jsonify({"success": True, "message": f"Suitable offers for your bid was found - quantities left after trade(s): {quantities_left} -> trade stored into system"}), 200
            
            else:
                # Store only to bids, no trade
                cur.execute(
                "INSERT INTO bids (user_id, bid_price, bid_quantity) VALUES (%s, %s, %s)",
                (user_id, price, quantity)
                )
                db.commit()
                cur.close()
                return jsonify({"success": False, "message": f"No, suitable offers for your bid - price: {price}, quantity: {quantity} -> bid stored into system"}), 200
            
            #------------------ Db-matching and functionalities ------------------
        
        
        elif action_type.lower() == "offer":
        
            #------------------ Db-matching and functionalities ------------------
            cur = db.cursor()

            # Bids that match the offer amount
            # highest bids first, same price orders ordered by timestamp, oldest first.
            cur.execute(f"SELECT bid_id, user_id, bid_price, bid_quantity FROM bids WHERE bid_price >= {price} ORDER BY bid_price DESC, bid_timestamp ASC")
            result = cur.fetchall()
            has_instances = len(result) > 0
            if has_instances:
                print("T3")
                bids_to_be_removed, bids_to_be_updated, trades_to_be_created, quantities_left = match_offer_to_bids(quantity,result)            

                for (id,q) in bids_to_be_updated:
                    cur.execute(f"UPDATE bids SET bid_quantity = {q} WHERE bid_id = {id}")
                
                for b in bids_to_be_removed:
                    cur.execute(f"DELETE FROM bids WHERE bid_id = {b}")
                
                for (b,p,q) in trades_to_be_created:
                    cur.execute("INSERT INTO trades (bidder_id, offerer_id, trade_price, trade_quantity) VALUES (%s, %s, %s, %s)",
                                                                                                                (b, user_id, p, q))
                # create offer if there is quantities left
                if (quantities_left > 0):
                    cur.execute("INSERT INTO offers (user_id, offer_price, offer_quantity) VALUES (%s, %s, %s)", 
                                                                                                (user_id, price, quantities_left)) 
                db.commit()
                cur.close()
                return jsonify({"success": True, "message": f"Suitable bids for your offer was found - quantities left after trade(s): {quantities_left} -> trade stored into system"}), 200
            else:
                # Store only to offers, no trade
                cur.execute(
                "INSERT INTO offers (user_id, offer_price, offer_quantity) VALUES (%s, %s, %s)",
                (user_id, price, quantity)
                )
                db.commit()
                cur.close()
                return jsonify({"success": False, "message": f"No, suitable bids for your offer - price: {price}, quantity: {quantity} -> offer stored into system"}), 200
            #------------------ Db-matching and functionalities ------------------
        else:
            return jsonify({"error": "Invalid transaction-type, no action taken"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def match_bid_to_offers(quantity,offers):
    return trade(quantity,offers)

def match_offer_to_bids(quantity,bids):
    return trade(quantity,bids) 

def trade(quantity,orders):
    """
    Returns information about how given orders should be changed 
    if matching order is placed with given quantity.

    Args:
        quantity (int): How many offers or bids is to be matched.
        orders (list of tuples): List of bids or offers. One order is tuple: (id,orderer_id,price,quantity)
 
    Returns:
        orders_to_be_removed: list of order id:s, bids or offers with corresponding id should be removed
        orders_to_be_updated: list of tuples, where tuple=(order_id,new_price), these orders should be updated to new price
        trades_to_be_created: list of tuples where (orderer_id,trade_price,trade_quantity), these trades should be created
        quantities_left:      int of how many orders left unmatched.
    """
    trade_quantity = 0
    trade_price = 0
    quantities_left = quantity
    i = 0
    orders_to_be_removed = []
    orders_to_be_updated = []
    trades_to_be_created = []
    while (i < len(orders) and 0 < quantities_left):
        best_order = orders[i]
        order_id = best_order[0]
        orderer_id = best_order[1]
        trade_price = best_order[2]
        order_quantity = best_order[3]
        trade_quantity = order_quantity
        if (quantities_left < order_quantity):
            orders_left = order_quantity-quantities_left
            orders_to_be_updated.append((order_id,orders_left))
            trade_quantity = quantities_left
            quantities_left = 0
        else:
            orders_to_be_removed.append(order_id)
            quantities_left-=order_quantity
        trades_to_be_created.append((orderer_id,trade_price,trade_quantity))
        i+=1
    return orders_to_be_removed, orders_to_be_updated, trades_to_be_created, quantities_left

def fetch_and_store_aapl_data():
    global latest_data
    global last_updated

    api_url = 'https://api.marketdata.app/v1/stocks/quotes/AAPL/'

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        latest_data = data
        last_updated = datetime.datetime.now()
        
    except requests.exceptions.RequestException as e:
        print("Error when fetching: " + str(e))

@app.route('/aapl_data', methods=['GET'])
def get_aapl_data():
    global latest_data
    global last_updated
    
    # If none or more than 1h passed from the latest retrieval
    if latest_data is None or last_updated is None or (datetime.datetime.now() - last_updated).seconds > 3600:
        fetch_and_store_aapl_data()
        
    return jsonify({"success": True, "data": latest_data}), 200

@app.route('/trades', methods=['GET'])
def get_trades():
    cur = db.cursor()
    cur.execute(f"SELECT trade_timestamp, trade_price, trade_quantity  FROM trades")
    result = cur.fetchall()
    trades = []
    for (ts, p, q) in result:
        trades.append({"timestamp": ts, "price":p,"quantity":q})
    return jsonify({"success": True, "data": trades}), 200

@app.before_first_request
def create_db():
    try:
        cur = db.cursor()

        query_users = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT PRIMARY KEY
        );
        """

        bids = """
        CREATE TABLE IF NOT EXISTS bids (
            bid_id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            bid_price FLOAT(10, 2) NOT NULL,
            bid_quantity INT NOT NULL,
            bid_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        offers = """
        CREATE TABLE IF NOT EXISTS offers (
            offer_order_id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            offer_price FLOAT(10, 2) NOT NULL,
            offer_quantity INT NOT NULL,
            offer_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        trades = """
        CREATE TABLE IF NOT EXISTS trades (
            trade_order_id INT PRIMARY KEY AUTO_INCREMENT,
            offerer_id INT,
            bidder_id INT,
            trade_price FLOAT(10, 2) NOT NULL,
            trade_quantity INT NOT NULL,
            trade_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cur.execute(query_users)
        cur.execute(bids)
        cur.execute(offers)
        cur.execute(trades)

        db.commit()
        cur.close()
        
    except Exception as e:
        print("Error in db init: " + str(e))


if __name__ == '__main__':
    app.run(debug=True)

