from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/vapi-webhook")
async def handle_vapi_call(request: Request):
    data = await request.json()
    
    # Check if the AI has triggered the tool
    if data["message"]["type"] == "tool-calls":
        args = data["message"]["toolCalls"][0]["function"]["arguments"]
        
        address = args.get("address")
        material = args.get("material")
        
        # This is where your logic lives
        print(f"DEBUG: Logic triggered for {address}")
        
        # Step 1: Validate with Google Maps (Coming in next step)
        # Step 2: Calculate Price
        # Step 3: Send SMS to Owner
        
        return {"results": [{"toolCallId": data["message"]["toolCalls"][0]["id"], "result": "Dossier generated."}]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)