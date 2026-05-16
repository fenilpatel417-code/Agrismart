from google import genai
from google.genai import types
import PIL.Image
import io
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

PROMPTS = {
    "disease": """You are Dr. PlantAI, an expert plant pathologist. Analyze this crop image carefully.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [name]
🦠 DISEASE STATUS: [Healthy OR specific disease name]
⚠️ SEVERITY: [None / Mild / Moderate / Severe / Critical]
📊 CONFIDENCE: [e.g. 92%]

📋 SYMPTOMS OBSERVED:
• [symptom 1]
• [symptom 2]

🔬 ROOT CAUSE:
[1-2 sentences]

💊 TREATMENT PLAN:
Chemical: [options]
Organic: [options]

🛡️ PREVENTION:
• [tip 1]
• [tip 2]

⏰ URGENCY: [Act Now / Monitor Weekly / No Action Needed]

If not a plant image: "❌ No plant detected. Please upload a clear crop photo." """,

    "identify": """You are AgriExpert, a master botanist. Identify this plant/crop.

Respond in this EXACT format:

🌿 CROP NAME: [Common name (Scientific name)]
🌍 ORIGIN: [where it's from]
📦 CATEGORY: [Vegetable / Fruit / Grain / Herb / Flower / Tree]

📋 DESCRIPTION:
[2-3 sentences]

🌱 GROWING CONDITIONS:
• Soil: [type and pH]
• Temperature: [range]
• Sunlight: [requirements]
• Water: [frequency]

📅 GROWING TIMELINE:
• Best planting time: [season]
• Days to germination: [X days]
• Days to harvest: [X days]

💰 ECONOMIC VALUE:
[Brief note]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "growth": """You are a master agricultural advisor. Analyze this crop and give growth optimization tips.

Respond in this EXACT format:

🌿 CROP IDENTIFIED: [name]
📈 CURRENT HEALTH STATUS: [Excellent / Good / Fair / Poor]

🚀 TOP 5 TIPS TO GROW FASTER:
1. [tip]
2. [tip]
3. [tip]
4. [tip]
5. [tip]

🧪 FERTILIZER RECOMMENDATIONS:
• NPK Ratio: [e.g. 10-10-10]
• Organic option: [e.g. compost, manure]
• Application: [how often]

💧 WATER & IRRIGATION:
[Specific advice]

☀️ SUNLIGHT & SPACING:
[Specific advice]

📅 HARVEST OPTIMIZATION:
• Expected harvest: [timeframe]
• Signs of readiness: [what to look for]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "treatment": """You are a plant treatment specialist. Provide a complete treatment plan.

Respond in this EXACT format:

🌿 PLANT: [name]
🦠 CONDITION: [healthy or problem detected]

💊 IMMEDIATE TREATMENT STEPS:
Step 1: [action]
Step 2: [action]
Step 3: [action]

🧴 CHEMICAL TREATMENTS:
• Product: [name] — Dosage: [amount] — Frequency: [how often]

🌿 ORGANIC/NATURAL TREATMENTS:
• [remedy 1]
• [remedy 2]

⚠️ SAFETY PRECAUTIONS:
• [precaution 1]
• [precaution 2]

📅 RECOVERY TIMELINE: [Expected recovery time]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "fertilizer": """You are a soil and fertilizer expert. Recommend the best fertilizer plan for this crop.

Respond in this EXACT format:

🌿 CROP: [name]
🌱 GROWTH STAGE (estimated): [Seedling / Vegetative / Flowering / Fruiting / Mature]

🧪 RECOMMENDED FERTILIZERS:
Primary NPK:
• Ratio: [e.g. 20-10-10]
• Best products: [names]
• Application rate: [amount per area]

Micronutrients needed:
• [nutrient]: [why and how]

📅 FERTILIZER SCHEDULE:
• Week 1-2: [what to apply]
• Week 3-4: [what to apply]
• Monthly: [maintenance]

🌿 ORGANIC ALTERNATIVES:
• [option 1]
• [option 2]

⚠️ WHAT TO AVOID:
• [common mistake 1]

💡 PRO TIP: [One expert tip]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """
}

ANALYSIS_LABELS = {
    "disease": "Disease Detection",
    "identify": "Crop Identification",
    "growth": "Growth Tips",
    "treatment": "Treatment Plan",
    "fertilizer": "Fertilizer Guide",
}

CHATBOT_SYSTEM = """You are AgriBot 🌱, a friendly AI agricultural assistant by AgriSmart.
Help farmers with: crop disease diagnosis, growing tips, fertilizer advice, irrigation, pest control, seasonal planting, post-harvest care.
Be friendly, practical, use simple language. Keep responses under 200 words. Use emojis occasionally.
If asked about non-agricultural topics, politely redirect to farming/plant topics."""


def _analyze_sync(image_bytes: bytes, analysis_type: str) -> dict:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return {
            "success": False,
            "error": "⚙️ Gemini API key not configured. Please add your free API key to the .env file. Get one at https://aistudio.google.com"
        }
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        image = PIL.Image.open(io.BytesIO(image_bytes))
        prompt = PROMPTS.get(analysis_type, PROMPTS["disease"])

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt, image]
        )
        result_text = response.text

        crop_name = _extract_field(result_text, ["PLANT IDENTIFIED", "CROP IDENTIFIED", "CROP", "PLANT"])
        disease = _extract_field(result_text, ["DISEASE STATUS", "CONDITION"])
        severity = _extract_field(result_text, ["SEVERITY"])
        summary = result_text[:400].replace("\n", " ").strip()

        return {
            "success": True,
            "result": result_text,
            "analysis_type": analysis_type,
            "analysis_label": ANALYSIS_LABELS.get(analysis_type, analysis_type),
            "crop_name": crop_name,
            "disease_name": disease,
            "severity": severity,
            "summary": summary,
        }
    except Exception as e:
        return {"success": False, "error": f"AI analysis failed: {str(e)}"}


def _extract_field(text: str, keys: list) -> str:
    for key in keys:
        for line in text.split("\n"):
            if key in line and ":" in line:
                val = line.split(":", 1)[-1].strip()
                val = val.replace("*", "").replace("[", "").replace("]", "").strip()
                if val and len(val) > 1:
                    return val[:200]
    return "Unknown"


async def analyze_image(image_bytes: bytes, analysis_type: str) -> dict:
    return await asyncio.to_thread(_analyze_sync, image_bytes, analysis_type)


def _chat_sync(message: str, history: list) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return "⚙️ AgriBot needs a Gemini API key to work. Please add it to your .env file. Get a free key at https://aistudio.google.com"
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        chat_history = []
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        chat = client.chats.create(
            model="models/gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=CHATBOT_SYSTEM),
            history=chat_history
        )
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


async def chat_with_agribot(message: str, history: list) -> str:
    return await asyncio.to_thread(_chat_sync, message, history)
