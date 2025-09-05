from flask import Flask, request

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    json_data = request.get_json()
    print(json_data)
    return 'OK', 200

def main():
    app.run(port=5000)

if __name__ == '__main__':
    main()