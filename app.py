from flask import Flask, jsonify
import requests
from flask_cors import CORS
import datetime

app = Flask(__name__)
# Enabling CORS for all routes
CORS(app)

latest_data = None
last_updated = None

def dummy_func(x):
    return x

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
    
    # If none or more than 1h passed from latest retrieval
    if latest_data is None or (datetime.datetime.now() - last_updated).seconds > 3600:
        fetch_and_store_aapl_data()
        
    return jsonify({"success": True, "data": latest_data}), 200

if __name__ == '__main__':
    app.run(debug=True)
