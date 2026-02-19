from flask import Flask, request, jsonify
import requests
import json
import os
from groq import Groq

app = Flask(__name__)

# ─── API Clients ──────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ─── Environment Variables ────────────────────────────────────────────────────
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "sofarepair123")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a friendly WhatsApp customer support bot for "Sofa Repair Siliguri".

BUSINESS DETAILS:
- Business Name: Sofa Repair Siliguri
- Owner: Anand
- Phone/WhatsApp: +91 99073 92443
- Website: https://sofarepairsiliguri.shop
- Instagram: https://instagram.com/sofarepairsiliguri
- Facebook: https://facebook.com/sofarepairsiliguri
- Service Type: Doorstep Sofa Repair & Customization
- Service Area: Siliguri & Nearby Areas
- Experience: 10+ Years

SERVICES:
1. Sofa Repair — torn sofa, broken frame, loose springs, damaged armrest, wood polish, structure repair
2. Cushion/Foam Replacement — high density foam, soft foam, re-bonded foam, custom cushion filling
3. Sofa Fabric Change / Reupholstery — Velvet, Leatherette, Suede, Printed, Designer Fabric (100+ options)

PRICING:
- Minor Repair: Starting ₹800
- Foam Replacement: Starting ₹1,500
- Full Reupholstery: Starting ₹4,000
- Exact price depends on: sofa size, type of work, fabric choice, foam quality

FAQS:
- Home service: Yes ✅ Doorstep service in Siliguri
- Payment: 50% advance, 50% after work completion
- Repair time: Minor repair same day | Full reupholstery 3–5 days
- Warranty: Yes ✅ Foam & stitching warranty (depends on work type)
- Pickup/drop: Yes ✅ Available if needed
- Recliner repair: Yes ✅ (after inspection)
- Custom design: Yes ✅ Can change fabric, color & design completely

BOOKING FLOW — collect from customer:
1. Customer Name
2. Full Address in Siliguri
3. Sofa Photos (ask them to send)
4. Preferred Date & Time

LEAD QUALIFICATION — before giving price, ALWAYS ask:
1. How many seater sofa? (1/2/3/5 seater)
2. What problem are you facing?
3. Budget range?
4. When do you want the work done?

MENU — show when customer says hi, hello, or sends "menu" or "0":
1️⃣ Sofa Repair
2️⃣ Cushion / Foam Problem
3️⃣ Change Sofa Fabric
4️⃣ Price Inquiry
5️⃣ Book Inspection
6️⃣ Talk to Human

IMPORTANT RULES:
- Reply in the same language customer uses (Hindi or English)
- Keep replies short & conversational like real WhatsApp chat
- Use emojis naturally 🛋️✨
- If customer says "talk to human" or picks option 6:
  Say: "Sure! Please call or WhatsApp Anand directly 📞 +91 99073 92443"
- If customer sends "BOOK" — start booking flow immediately
- Never guess prices — always qualify first
- Be warm, friendly and helpful at all times
"""

# ─── Conversation Memory ──────────────────────────────────────────────────────
conversations = {}

# ─── Send WhatsApp Message via Meta API ───────────────────────────────────────
def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# ─── Get AI Reply from Groq ───────────────────────────────────────────────────
def get_ai_reply(sender, user_message):
    if sender not in conversations:
        conversations[sender] = []

    conversations[sender].append({
        "role": "user",
        "content": user_message
    })

    # Keep last 10 messages to save tokens
    history = conversations[sender][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + history,
            max_tokens=500,
            temperature=0.7
        )
        reply = response.choices[0].message.content

    except Exception as e:
        reply = "Sorry, something went wrong 😔 Please call us directly at +91 99073 92443"

    conversations[sender].append({
        "role": "assistant",
        "content": reply
    })

    return reply

# ─── Webhook Verification (Meta requires this) ────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verified!")
        return challenge, 200
    else:
        return "Forbidden", 403

# ─── Receive & Reply to Messages ─────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Only process actual messages (ignore status updates)
        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        message = value["messages"][0]
        sender = message["from"]
        msg_type = message["type"]

        # Handle text messages
        if msg_type == "text":
            user_text = message["text"]["body"]
        else:
            # For images, audio, etc.
            user_text = "[Customer sent a media file]"

        print(f"📩 Message from {sender}: {user_text}")

        # Get AI reply
        reply = get_ai_reply(sender, user_text)

        # Send reply back
        send_whatsapp_message(sender, reply)
        print(f"✅ Replied to {sender}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return jsonify({"status": "ok"}), 200

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return "✅ Sofa Repair Siliguri WhatsApp Bot is Running! 🛋️"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
