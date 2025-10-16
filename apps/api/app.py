from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/api/master")
def master():
    return jsonify({
        "clients": [{"id":1,"name":"Client A"}],
        "recipes": [{"id":1,"name":"M20"}],
        "vehicles": [{"id":1,"number":"TRK-001"}]
    })

@app.get("/api/orders")
def orders():
    return jsonify([{
        "id": 101, "client":"Client A", "recipe":"M20",
        "totalM3": 45, "mixerM3": 1, "status":"Planned",
        "createdAt":"2025-10-16T09:00:00Z"
    }])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
