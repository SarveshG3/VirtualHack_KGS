from flask import Flask, jsonify,  Response, send_file, request
import io
import json
import fetch_ClinicalTrials as ct

app = Flask(__name__)


@app.route('/')
def hello():
    ascii_banner = "Welcome to CODIV Coder's Zone"
    return ascii_banner


@app.route('/fetch_trials/', methods=['GET', 'POST'])
def fetch_trials():
    request_data = request.get_json(force=True)
    status = ct.handle_request(request_data)
    return json.dumps(status)


if __name__ == '__main__':
    app.run(debug=True)