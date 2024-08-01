from flask import Flask, jsonify, render_template
import requests
import threading
import time

app = Flask(__name__)

json_url = 'https://4642projectzzz.s3.ap-southeast-2.amazonaws.com/ovs_statistics_of_s0.json'
current_data = None
previous_data = None
rate_data = {}

def fetch_data():
    global current_data, previous_data, rate_data

    while True:
        response = requests.get(json_url)
        new_data = response.json()

        if current_data is not None:
            previous_data = current_data

        current_data = new_data

        if previous_data is not None:
            for port in current_data:
                if port in previous_data:
                    rate_data[port] = {
                        'RateRx': (current_data[port]['rx_bytes'] - previous_data[port]['rx_bytes']) * 8 / 10000000,
                        'RateTx': (current_data[port]['tx_bytes'] - previous_data[port]['tx_bytes']) * 8 / 10000000,
                    }
                else:
                    rate_data[port] = {
                        'RateRx': 0,
                        'RateTx': 0,
                    }

        time.sleep(10)

@app.route('/')
def index():
    return render_template('index.html', data=current_data, rate_data=rate_data)

if __name__ == '__main__':
    data_thread = threading.Thread(target=fetch_data)
    data_thread.start()
    app.run(debug=True)
