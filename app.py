from flask import Flask, jsonify
from prometheus_client import Counter, generate_latest

app = Flask(__name__)

# Define Prometheus metrics
app_requests_total = Counter('app_requests_total', 'Total number of requests to the app')


@app.route('/')
def hello():
    app_requests_total.inc()
    return 'Hello, Multi-Cloud DevOps!'


@app.route('/health')
def health():
    return jsonify({"status": "healthy"})


@app.route('/metrics')
def metrics():
    return generate_latest()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
