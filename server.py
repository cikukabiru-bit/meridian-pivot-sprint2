from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)

SECRET = "northstar-shared-secret-9f3k2m8x"

@app.route("/")
def home():
    return "server is alive"

@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data()

    claimed_signature = request.headers.get("X-Northstar-Signature")
    if claimed_signature is None:
        print("REJECTED - no signature header")
        return "missing signature", 401

    expected_signature = hmac.new(SECRET.encode(), raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, claimed_signature):
        print("REJECTED - signature mismatch")
        print("   expected:", expected_signature)
        print("   claimed :", claimed_signature)
        return "invalid signature", 401

    print("ACCEPTED -", raw_body)
    return "received", 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)