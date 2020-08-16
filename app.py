from flask import Flask, jsonify,  Response, send_file, request
import io
import json

app = Flask(__name__)


@app.route('/')
def hello():
    ascii_banner = "Welcome to CODIV Coder's Zone"
    #ascii_banner = pyfiglet.figlet_format("Welcome to NooB Street !!")
    return ascii_banner

@app.route('/post_test', methods=['GET', 'POST'])
def post_test():
    request_data = request.get_json()
    #print("data posted successfully...")
    #print(request_data.items(0))
    return json.loads(request_data)


if __name__ == '__main__':
    app.run(debug=True)
#    print(hello())
