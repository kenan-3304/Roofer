from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch
import json

client = TestClient(app)

def test_valid_payload():
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                "customer": {"number": "+1234567890"},
                "analysis": {
                    "structuredData": {
                        "address": "123 Main St",
                        "severity": "High",
                        "owner": True,
                        "water_still_flowing": True,
                        "caller_name": "John Doe",
                        "phone_number": "555-0199"
                    },
                    "summary": "Test summary"
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        # Mock successful send
        mock_send.return_value = {"id": "test_id"}
        
        response = client.post("/webhook", json=payload)
        
        if response.status_code != 200:
            print(f"FAILED: Status {response.status_code}, Body: {response.text}")
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_send.assert_called_once()
        
        # Check if email arguments contain the right 'to' address
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == "kenan.seremet04@gmail.com"
        assert "John Doe" in call_args["text"]
        assert "YES" in call_args["text"] # Water Still Flowing check

def test_missing_address():
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                "analysis": {
                    "structuredData": {
                        # No address
                        "severity": "High"
                    }, 
                    "summary": "Test"
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "skipped", "reason": "missing_address"}
        mock_send.assert_not_called()

def test_insufficient_data():
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                "analysis": {
                    "structuredData": {
                        "address": "123 Main St",
                        "owner": True
                        # Missing severity, source_of_loss, water_still_flowing
                    },
                    "summary": "Test"
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "skipped", "reason": "insufficient_data"}
        mock_send.assert_not_called()

if __name__ == "__main__":
    print("Running tests...")
    try:
        test_valid_payload()
        print("✅ test_valid_payload passed")
        test_missing_address()
        print("✅ test_missing_address passed")
        test_insufficient_data()
        print("✅ test_insufficient_data passed")
        print("\nALL SYSTEM TESTS PASSED")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")
