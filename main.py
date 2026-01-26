from fastapi import FastAPI, Request
import resend # pip install resend
import os
import uvicorn

app = FastAPI()

# Set your API Key
resend.api_key = os.getenv("RESEND_API_KEY")

# Company Directory: Map Vapi Assistant IDs to Business Owner Emails
COMPANY_DIRECTORY = {
    # Replace these with your actual Vapi Assistant IDs
    "vapi-assistant-id-1": "kenan.seremet04@gmail.com",
    "vapi-assistant-id-2": "another.owner@example.com",
}
DEFAULT_EMAIL = "kenan.seremet04@gmail.com" # Fallback email

@app.post("/webhook")
async def handle_vapi_webhook(request: Request):
    data = await request.json()
    print(data)
    
    # We only care when the call is finished
    if data.get("message", {}).get("type") == "end-of-call-report":
        message_data = data["message"]
        call_data = message_data.get("call", {})
        assistant_id = call_data.get("assistantId")
        
        # 1. Determine Recipient (Multi-tenancy)
        to_email = COMPANY_DIRECTORY.get(assistant_id, DEFAULT_EMAIL)
        
        # 2. Extract Fields
        # Strategy: Look for "structuredOutputs" in the artifact
        # The key is a dynamic UUID, so we need to find the one with 'stepName' or just take the first one.
        structured_data = {}
        
        artifact = message_data.get("artifact", {})
        structured_outputs = artifact.get("structuredOutputs", {})
        
        # Iterate to find the result. 
        # In the log provided, it looks like: {'uuid': {'name': 'emergency_dossier', 'result': {...}}}
        for output in structured_outputs.values():
            if output.get("name") == "emergency_dossier" or "result" in output:
                structured_data = output.get("result", {})
                break
        
        # Fallback: Check analysis.structuredData just in case it appears there in other contexts
        if not structured_data:
             structured_data = message_data.get("analysis", {}).get("structuredData", {})
             
        # Extract specific fields from the found data dictionary
        address = structured_data.get('address')
        severity = structured_data.get('severity')
        source_of_loss = structured_data.get('source_of_loss')
        water_still_flowing = structured_data.get('water_still_flowing') # boolean
        
        owner = structured_data.get('owner') # boolean
        caller_name = structured_data.get('caller_name')
        site_access = structured_data.get('site_access')
        is_power_off = structured_data.get('is_power_off') # boolean
        phone_number = structured_data.get('phone_number')
        insurance_status = structured_data.get('insurance_status')
        affected_surfaces = structured_data.get('affected_surfaces')

        # Extract Summary from transcript or analysis
        # In the log, 'transcript' is at message_data['transcript']
        transcript_summary = message_data.get("analysis", {}).get("summary")
        if not transcript_summary:
             # Fallback to just the raw transcript if summary is missing
             transcript_summary = message_data.get("transcript", "No transcript available.")

        # 3. Validation Logic
        # Rule 1: Must have an address
        if not address:
            print("Skipping email: No address provided.")
            return {"status": "skipped", "reason": "missing_address"}
        
        # Rule 2: Must have at least one significant detail (severity, source, or flowing status)
        # Note: We check if ALL are None. strict check.
        if severity is None and source_of_loss is None and water_still_flowing is None:
            print("Skipping email: No severity, source of loss, or water flow status detected.")
            return {"status": "skipped", "reason": "insufficient_data"}

        # Build the Dossier Email
        subject = f"🚨 EMERGENCY LEAD: {address}"
        body = f"""
        NEW EMERGENCY WATER DAMAGE DOSSIER
        ----------------------------------
        Caller Name: {caller_name or 'Unknown'}
        Phone: {phone_number or call_data.get('customer', {}).get('number', 'N/A')}
        Address: {address}
        Owner: {'Yes' if owner else 'No/Unknown'}
        
        CRITICAL DETAILS
        ----------------
        Water Still Flowing: {'YES' if water_still_flowing else 'No'}
        Power Off: {'Yes' if is_power_off else 'No'}
        Severity: {severity or 'N/A'}
        Source of Loss: {source_of_loss or 'N/A'}
        Affected Surfaces: {affected_surfaces or 'N/A'}
        
        LOGISTICS
        ---------
        Insurance: {insurance_status or 'Unknown'}
        Site Access: {site_access or 'N/A'}
        
        TRANSCRIPT SUMMARY:
        {transcript_summary}
        """
        
        # Send the Email
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": "kenan.seremet04@gmail.com",
            "subject": subject,
            "text": body
        })
        
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)