from flask import Flask, jsonify, request,render_template
import requests
from flask_cors import CORS
import datetime
from flask_mysqldb import MySQL

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

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'cse'
app.config['MYSQL_PASSWORD'] = 'cse'
app.config['MYSQL_DB'] = 'cse'
mysql = MySQL(app)

def return_app():
    return app

def dummy_func(x):
    return x

def validate_price(price, reference):
    # Is the price within 10 percent margin from the reference?
    margin = 0.1 * reference
    return (reference - margin) <= price <= (reference + margin)

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

        if action_type.lower() == "bid":
        
            if isinstance(price, float) and validate_price(price, reference) and quantity < reasonable_limit:
                #------------------ Db-matching and functionalities ------------------
                cur = mysql.connection.cursor()
                # Match against offers:
                
                # If any, even partially matching offer exists
                cur.execute(f"SELECT COUNT(*) FROM offers")
                result = cur.fetchone()
                has_instances = result[0] > 0
                if has_instances:
                   print("T3")
                   
                else:
                    # Store only to bids, no trade
                    cur.execute(
                    "INSERT INTO bids (user_id, bid_price, bid_quantity) VALUES (%s, %s, %s)",
                     (user_id, price, quantity)
                    )
                    mysql.connection.commit()
                    cur.close()
                    return jsonify({"success": False, "message": "No, suitable offers for your bid - price: {price}, quantity: {quantity} -> bid stored into system"}), 200
                
                #------------------ Db-matching and functionalities ------------------
            else:
                return jsonify({"error": "Invalid price or quantity, no action taken"}), 400

            
        elif action_type.lower() == "offer":
        
            if isinstance(price, float) and validate_price(price, reference) and quantity < reasonable_limit:
                #------------------ Db-matching and functionalities ------------------
                cur = mysql.connection.cursor()
                # Match against offers:
                
                # If any, even partially matching offer exists
                cur.execute(f"SELECT COUNT(*) FROM bids")
                result = cur.fetchone()
                has_instances = result[0] > 0
                if has_instances:
                   print("T3")
                else:
                    # Store only to offers, no trade
                    cur.execute(
                    "INSERT INTO offers (user_id, offer_price, offer_quantity) VALUES (%s, %s, %s)",
                     (user_id, price, quantity)
                    )
                    mysql.connection.commit()
                    cur.close()
                    return jsonify({"success": False, "message": "No, suitable bids for your offer - price: {price}, quantity: {quantity} -> offer stored into system"}), 200
                
                #------------------ Db-matching and functionalities ------------------
            else:
                return jsonify({"error": "Invalid price or quantity, no action taken"}), 400
        else:
            return jsonify({"error": "Invalid transaction-type, no action taken"}), 400


    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
    if latest_data is None or (datetime.datetime.now() - last_updated).seconds > 3600:
        fetch_and_store_aapl_data()
        
    return jsonify({"success": True, "data": latest_data}), 200


@app.before_first_request
def create_db():
    try:
        cur = mysql.connection.cursor()

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
            user_id INT,
            trade_price FLOAT(10, 2) NOT NULL,
            trade_quantity INT NOT NULL,
            trade_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cur.execute(query_users)
        cur.execute(bids)
        cur.execute(offers)
        cur.execute(trades)

        mysql.connection.commit()
        cur.close()
        
    except Exception as e:
        print("Error in db init: " + str(e))


if __name__ == '__main__':
    app.run(debug=True)

