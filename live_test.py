from fastapi.testclient import TestClient
from main import app
import os
import sys

# Check for API Key
# if not os.getenv("RESEND_API_KEY"):
#     print("❌ ERROR: RESEND_API_KEY is not set.")
#     print("Please run this script with your API key:")
#     print("RESEND_API_KEY=re_123... python3 live_test.py")
#     sys.exit(1)

client = TestClient(app)

def run_live_test():
    print("🚀 Sending live test payload to webhook...")
    
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1", # Mapped to Kenan's AT&T Gateway
                "customer": {"number": "+15550109988"},
            },
            "artifact": {
                "structuredOutputs": {
                    "some-uuid": {
                        "name": "emergency_dossier",
                        "result": {
                            "address": "742 Evergreen Terrace, Springfield",
                            "severity": "Critical",
                            "source_of_loss": "Burst Pipe in Basement",
                            "water_still_flowing": True,
                            "owner": True,
                            "caller_name": "Homer Simpson",
                            "site_access": "Key under mat",
                            "is_power_off": False,
                            "phone_number": "+15550109988",
                            "insurance_status": "State Farm",
                            "affected_surfaces": "Hardwood floors, Drywall",
                            "service_category": "water_emergency"
                        }
                    }
                }
            },
            "transcript": "Customer reported burst pipe...",
            "analysis": {
                "summary": "Customer reported a burst pipe in the basement. Water is currently flowing. Key is under the mat."
            }
        }
    }

    try:
        response = client.post("/webhook", json=payload)
        
        if response.status_code == 200:
            print("✅ Webhook processed successfully!")
            print("Status:", response.json())
            print("Checking your email (kenan.seremet04@gmail.com) now...")
        else:
            print(f"❌ Failed: Status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    run_live_test()
