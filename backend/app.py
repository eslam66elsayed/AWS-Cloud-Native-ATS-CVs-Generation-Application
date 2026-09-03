#import os, requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
API = os.environ.get("API_GATEWAY_URL", "")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/generate-cv", methods=["POST"])
def generate_cv():
    data = request.get_json()
    try:
        r = requests.post(f"{API}/generate", json=data, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/analyze-cv", methods=["POST"])
def analyze_cv():
    data = request.get_json()
    try:
        r = requests.post(f"{API}/analyze", json=data, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
