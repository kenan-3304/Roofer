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
                        "phone_number": "555-0199",
                        "service_category": "water_emergency"
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
        # Expecting a list of recipients: [Admin, Owner]
        assert "kenan.seremet04@gmail.com" in call_args["to"]
        assert "7037760484@mms.att.net" in call_args["to"] # Owner's AT&T gateway
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


def test_ghost_payload():
    """Test a payload where everything is 'null' or empty - like an immediate hangup."""
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                # No caller ID in some web calls, or empty
                "customer": {"number": ""}, 
                "analysis": {
                    "structuredData": {
                        "address": "null", # AI often returns this string
                        "phone_number": "N/A",
                        "severity": None,
                        "caller_name": "null"
                    },
                    "summary": "Caller hung up."
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        # Should be skipped because NO Address AND NO Phone
        assert response.json() == {"status": "skipped", "reason": "ghost_call_no_contact_info"}
        mock_send.assert_not_called()

def test_non_emergency_payload():
    """Test the Mold/Fire/Non-Emergency template."""
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                "customer": {"number": "+15551234567"},
                "analysis": {
                    "structuredData": {
                        "address": "456 Oak St",
                        "caller_name": "Jane Smith",
                        "phone_number": "+15551234567",
                        "service_category": "mold_fire_non_emergency",
                        "source_of_loss": "Mold in bathroom",
                        "owner": True
                    },
                    "summary": "Customer has mold issues."
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        client.post("/webhook", json=payload)
        call_args = mock_send.call_args[0][0]
        # Check specific subject and body content for non-emergency
        assert "⚠️ NEW LEAD" in call_args["subject"]
        assert "ISSUE DETAILS" in call_args["text"]
        assert "CRITICAL STATUS" not in call_args["text"] # Should NOT have water emergency fields

def test_general_inquiry_payload():
    """Test the General Inquiry template."""
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "assistantId": "vapi-assistant-id-1",
                "customer": {"number": "+15559876543"},
                "analysis": {
                    "structuredData": {
                        "address": "789 Pine Ln",
                        "caller_name": "Bob Builder",
                        "phone_number": "+15559876543",
                        "service_category": "general_inquiry"
                    },
                    "summary": "Asking about pricing."
                }
            }
        }
    }
    with patch("main.resend.Emails.send") as mock_send:
        client.post("/webhook", json=payload)
        call_args = mock_send.call_args[0][0]
        # Check specific subject and body content for inquiry
        assert "ℹ️ GENERAL INQUIRY" in call_args["subject"]
        assert "NEW GENERAL INQUIRY" in call_args["text"]
        assert "ISSUE DETAILS" not in call_args["text"]

if __name__ == "__main__":
    print("Running tests...")
    try:
        test_valid_payload()
        print("✅ test_valid_payload passed")
        test_missing_address()
        print("✅ test_missing_address passed")
        test_insufficient_data()
        print("✅ test_insufficient_data passed")
        test_ghost_payload()
        print("✅ test_ghost_payload passed")
        test_non_emergency_payload()
        print("✅ test_non_emergency_payload passed")
        test_general_inquiry_payload()
        print("✅ test_general_inquiry_payload passed")
        print("\nALL SYSTEM TESTS PASSED")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")
