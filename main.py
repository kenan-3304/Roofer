from fastapi import FastAPI, Request
import resend # pip install resend
import os
import uvicorn
import re

app = FastAPI()

# Set your API Key
resend.api_key = os.getenv("RESEND_API_KEY")

# Company Directory: Map Vapi Assistant IDs to Business Owner SMS Gateways
COMPANY_DIRECTORY = {
    # Replace these with your actual Vapi Assistant IDs
    # using mms.att.net for AT&T to handle longer messages better than txt.att.net
    "vapi-assistant-id-1": "7037760484@mms.att.net", 
    "vapi-assistant-id-2": "another.owner@example.com",
}
ADMIN_EMAIL = "kenan.seremet04@gmail.com" # Internal verification copy

# Helper to clean "null" strings from AI
def sanitize_input(value):
    if not value:
        return None
    if isinstance(value, str):
        # normalize
        cleaned = value.strip()
        if cleaned.lower() in ["null", "n/a", "none", "unknown", "undefined"]:
            return None
        return cleaned
    return value



@app.post("/webhook")
async def handle_vapi_webhook(request: Request):
    data = await request.json()
    #print(data)
    
    # We only care when the call is finished
    if data.get("message", {}).get("type") == "end-of-call-report":
        message_data = data["message"]
        call_data = message_data.get("call", {})
        assistant_id = call_data.get("assistantId")
        
        # 1. Determine Recipients
        recipients = [ADMIN_EMAIL]
        owner_gateway = COMPANY_DIRECTORY.get(assistant_id)
        if owner_gateway:
            recipients.append(owner_gateway)
        
        # 2. Extract Fields & Sanitize
        structured_data = {}
        
        artifact = message_data.get("artifact", {})
        structured_outputs = artifact.get("structuredOutputs", {})
        
        # Iterate to find the result. 
        for output in structured_outputs.values():
            if output.get("name") == "emergency_dossier" or "result" in output:
                structured_data = output.get("result", {})
                break
        
        # Fallback
        if not structured_data:
             structured_data = message_data.get("analysis", {}).get("structuredData", {})
             
        # Extract & Sanitize specific fields
        address = sanitize_input(structured_data.get('address'))
        severity = sanitize_input(structured_data.get('severity'))
        source_of_loss = sanitize_input(structured_data.get('source_of_loss'))
        water_still_flowing = structured_data.get('water_still_flowing') # boolean (keep as is)
        
        owner = structured_data.get('owner') # boolean
        caller_name = sanitize_input(structured_data.get('caller_name'))
        site_access = sanitize_input(structured_data.get('site_access'))
        is_power_off = structured_data.get('is_power_off') # boolean
        
        # Smart Phone Number Logic
        extracted_phone = sanitize_input(structured_data.get('phone_number'))
        caller_id = sanitize_input(call_data.get('customer', {}).get('number'))
        
        # Decision: If extracted_phone looks like a real number, use it.
        # Otherwise, default to the Caller ID.
        if extracted_phone and re.search(r'\d{7,}', str(extracted_phone)):
            phone_number = extracted_phone
        else:
            phone_number = caller_id or extracted_phone
            
        insurance_status = sanitize_input(structured_data.get('insurance_status'))
        affected_surfaces = sanitize_input(structured_data.get('affected_surfaces'))

        # Extract Summary
        transcript_summary = message_data.get("analysis", {}).get("summary")
        if not transcript_summary:
             transcript_summary = message_data.get("transcript", "No transcript available.")

        # 3. Validation Logic (Ghost Prevention)
        # Rule: Must have EITHER an Address OR a Phone Number.
        # If both are missing, it's a "Ghost Call" (hung up immediately/web call with no input).
        if not address and not phone_number:
            print(f"Skipping Ghost Dossier: No Address AND No Phone. (CallerID: {caller_id})")
            return {"status": "skipped", "reason": "ghost_call_no_contact_info"}
        
        # Build the Dossier Email
        subject = f"🚨 EMERGENCY LEAD: {address or 'No Address Provided'}"
        body = f"""
        NEW EMERGENCY WATER DAMAGE DOSSIER
        ----------------------------------
        Caller Name: {caller_name or 'Unknown'}
        Phone: {phone_number or 'N/A'}
        Address: {address or 'N/A (See Phone)'}
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
        
        TRANSCRIPT:
        {transcript_summary}
        """
        
        # Send the Email
        print(f"Sending email to recipients: {recipients}")
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": recipients,
            "subject": subject,
            "text": body
        })
        
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)