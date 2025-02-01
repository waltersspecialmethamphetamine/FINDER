from flask import Flask, request
import requests
import os

app = Flask(__name__)

API_KEY = os.getenv("IPINFO_API_KEY")  # Secure API key storage
users = {}

@app.route("/", methods=["GET"])
def capture_ip():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    username = request.args.get("user")

    if username:
        location_data = requests.get(f"https://ipinfo.io/{user_ip}/json?token={API_KEY}").json()
        users[username] = location_data  

    return "Tracking active."

@app.route("/find", methods=["GET"])
def find_user():
    username = request.args.get("user")
    if username in users:
        return users[username]
    return {"error": "User not found."}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
