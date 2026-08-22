import requests
import hmac
import hashlib

SECRET = "northstar-shared-secret-9f3k2m8x"
URL = "http://127.0.0.1:5000/webhook"

MODE = "nosig"          # later: "tampered", "wrongsig", "nosig"

body = '{"sku": "NS-AIRMAX-42", "qty": 8}'

signature = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

body_to_send = body
headers = {
    "Content-Type": "application/json",
    "X-Northstar-Signature": signature,
}

if MODE == "tampered":
    body_to_send = '{"sku": "NS-AIRMAX-42", "qty": 800}'
elif MODE == "wrongsig":
    headers["X-Northstar-Signature"] = "0" * 64
elif MODE == "nosig":
    del headers["X-Northstar-Signature"]

response = requests.post(URL, data=body_to_send, headers=headers)

print("MODE:", MODE)
print("status:", response.status_code)
print("reply:", response.text)