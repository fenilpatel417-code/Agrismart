from google import genai
from google.genai import types
import PIL.Image
import io
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_CONTEXT = """You are an expert agricultural scientist specializing in crops grown in Gujarat, India. You have deep knowledge of:

KHARIF CROPS (June–October): Cotton, Groundnut, Bajra, Soybean, Castor, Tobacco, Rice, Maize, Moong, Tur Dal
RABI CROPS (October–March): Wheat, Cumin (Jeera), Garlic, Onion, Fennel (Saunf), Potato, Coriander, Mustard
ZAID CROPS (March–June): Watermelon, Cucumber, Moong, Vegetables

For each crop you know:
- Exact leaf shape, color, texture, stem structure
- How healthy vs diseased leaves look visually
- Gujarat-specific diseases, pests, and deficiencies
- Local climate (semi-arid, black cotton soil, sandy loam)
- Gujarati and Hindi names of crops and diseases

When analyzing an image:
1. First identify the crop species with confidence percentage
2. Check for ANY visible symptoms: spots, discoloration, wilting, holes, lesions, mold, pest damage, yellowing, curling
3. If disease found — name it scientifically AND in common Gujarati/Hindi
4. Give advice specific to Gujarat's climate and available local pesticides
"""

PROMPTS = {
    "disease": SYSTEM_CONTEXT + """
Examine the crop image carefully (entire image including leaf surface, edges, stem, color) to detect diseases.
Look specifically for: fungal spots, bacterial lesions, viral mosaic patterns, pest damage holes, nutrient deficiency yellowing/browning.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [name]
🦠 DISEASE STATUS: [Healthy OR specific disease name (Give name in: English + Scientific name + Gujarati/Hindi name)]
⚠️ SEVERITY: [Mild (0-30%) / Moderate (30-60%) / Severe (60-100%)]
📊 CONFIDENCE: [High (85-100%) / Medium (60-84%) / Low (below 60%)]

📋 SYMPTOMS OBSERVED:
• [symptom 1]
• [symptom 2]

🔬 ROOT CAUSE:
[1-2 sentences. Mention if it looks like a Gujarat-common disease for that crop based on soil and climate.]

💊 TREATMENT PLAN:
Chemical: [options available in Gujarat market]
Organic: [natural/organic remedy options]

🛡️ PREVENTION:
• [tip 1]
• [tip 2]

⏰ URGENCY: [Act Now / Monitor Weekly / No Action Needed]

Special Instruction: If healthy, say clearly "No disease detected, plant looks healthy" in DISEASE STATUS.
If not a plant image, output: "❌ No plant detected. Please upload a clear crop photo." """,

    "identify": SYSTEM_CONTEXT + """
Study the leaf shape, venation pattern, color, texture, stem, and any fruits/flowers to identify this plant/crop.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [Common name (Scientific name)]
🦠 DISEASE STATUS: [Healthy OR Any visible health issue]
⚠️ SEVERITY: [None / Mild / Moderate / Severe]
📊 CONFIDENCE: [High (85-100%) / Medium (60-84%) / Low (below 60%)]

📋 CROP DETAILS:
• Gujarati Name: [Name in Gujarati script and phonetic English]
• Main Growing Districts: [prominent Gujarat districts for this crop]
• Cultivation Season: [Kharif / Rabi / Zaid crop class]

📋 TOP 3 POSSIBLE MATCHES:
1. [Crop 1] - [Confidence %]
2. [Crop 2] - [Confidence %]
3. [Crop 3] - [Confidence %]

📋 DESCRIPTION:
[2-3 sentences overview]

🌱 GROWING CONDITIONS:
• Soil: [Gujarat suited soil like black cotton / sandy loam]
• Temperature: [Ideal range]
• Sunlight: [Requirements]
• Water: [Schedule and frequency]

📅 GROWING TIMELINE:
• Best planting time: [season / month]
• Days to germination: [X days]
• Days to harvest: [X days]

💰 ECONOMIC VALUE:
[Brief economic/agricultural value note in Gujarat context]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "growth": SYSTEM_CONTEXT + """
Analyze this crop image to assess its growth stage and health, and provide customized growth optimization tips.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [name]
🦠 DISEASE STATUS: [Healthy OR specific condition]
⚠️ SEVERITY: [None / Mild / Moderate / Severe]
📊 CONFIDENCE: [High (85-100%) / Medium (60-84%) / Low (below 60%)]

📈 CURRENT GROWTH STAGE & HEALTH:
• Estimated Stage: [Seedling / Vegetative / Flowering / Fruiting / Mature based on image]
• Health Status: [Excellent / Good / Fair / Poor]

🚀 TOP 5 TIPS TO GROW FASTER IN GUJARAT:
1. [Tip tailored to Gujarat soil like black cotton/sandy loam and local seasonal conditions]
2. [Tip]
3. [Tip]
4. [Tip]
5. [Tip]

🧪 FERTILIZER RECOMMENDATIONS:
• NPK Ratio: [crop-specific ratio]
• Local Brands: [brands available in Gujarat like IFFCO / KRIBHCO]
• Application: [how and when to apply]

💧 WATER & IRRIGATION:
[Watering schedule adjusted for Gujarat's semi-arid/hot climate and soil type]

☀️ SUNLIGHT & SPACING:
[Sunlight requirements and ideal spacing in fields]

📅 HARVEST OPTIMIZATION:
• Expected harvest: [timeframe]
• Signs of readiness: [what visual clues to look for]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "treatment": SYSTEM_CONTEXT + """
Analyze this crop image and provide a comprehensive, step-by-step treatment plan.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [name]
🦠 DISEASE STATUS: [Healthy OR specific disease/pest/deficiency detected]
⚠️ SEVERITY: [Mild (0-30%) / Moderate (30-60%) / Severe (60-100%)]
📊 CONFIDENCE: [High (85-100%) / Medium (60-84%) / Low (below 60%)]

💊 IMMEDIATE TREATMENT STEPS:
Step 1: [Action in simple, farmer-friendly language]
Step 2: [Action]
Step 3: [Action]

🧴 CHEMICAL TREATMENTS (GUJARAT MARKET):
• Product: [Pesticide/fungicide names available in Gujarat] — Dosage: [clear dosage] — Frequency: [frequency]

🌿 ORGANIC/NATURAL TREATMENTS:
• [Organic remedy 1]
• [Organic remedy 2]

⚠️ RECOVERY & TREATING STAGES:
• Recoverable: [Explain when this is still treatable]
• Too Late to Treat: [Explain when it is too far gone]

🛡️ SAFETY PRECAUTIONS:
• [safety precaution 1]
• [safety precaution 2]

📅 RECOVERY TIMELINE: [Expected days to recover]

If not a plant: "❌ No plant detected. Please upload a clear crop photo." """,

    "fertilizer": SYSTEM_CONTEXT + """
Analyze this crop and recommend a customized fertilizer plan.

Respond in this EXACT format:

🌿 PLANT IDENTIFIED: [name]
🦠 DISEASE STATUS: [Healthy OR Specific status]
⚠️ SEVERITY: [None / Mild / Moderate / Severe]
📊 CONFIDENCE: [High (85-100%) / Medium (60-84%) / Low (below 60%)]

🌱 ESTIMATED GROWTH STAGE: [Seedling / Vegetative / Flowering / Fruiting / Mature]

🧪 RECOMMENDED FERTILIZERS (NPK RATIO):
• Target NPK Ratio: [Specify target NPK ratio for this identified crop]
• Gujarat Available Products: [IFFCO NPK, DAP, Urea, KRIBHCO NPK, etc.]
• Application Rate: [dosage per acre or plant]

🧪 MICRONUTRIENT ADVICE:
• [Micronutrient, e.g., Zinc / Boron (deficiency highly common in Gujarat)] - [why and how to apply]

📅 FERTILIZER SCHEDULE:
• Days 1-15 (Sowing): [what to apply]
• Days 16-45: [what to apply]
• Flowering/Fruiting Stage: [what to apply]

💧 DRIP FERTIGATION SCHEDULE:
[Drip schedule if drip system is used, else standard scheduling]

⚠️ WHAT TO AVOID:
• [common over-fertilization mistake 1]
• [common mistake 2]

💡 PRO TIP: [One expert soil/nutrient tip for Gujarat soils]

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


def _precheck_image(client, image) -> dict:
    precheck_prompt = """Look at this image. Analyze its quality and subject. Respond in this EXACT format:
Q1: [yes/no]
Q2: [yes/no]
Q3: [leaf/stem/fruit/full plant/unclear]

Questions to answer:
1. Is this a clear photo of a plant/crop? (yes/no)
2. Is the image blurry or too dark to analyze? (yes/no)  
3. What part of the plant is visible? (leaf/stem/fruit/full plant/unclear)
"""
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[precheck_prompt, image]
        )
        text = response.text.lower()
        
        q1_answer = "yes"
        q2_answer = "no"
        
        for line in text.split("\n"):
            if "q1:" in line:
                if "no" in line:
                    q1_answer = "no"
            if "q2:" in line:
                if "yes" in line:
                    q2_answer = "yes"
        
        if q1_answer == "no":
            return {"success": False, "error": "Please upload a clear photo of a crop plant for accurate analysis."}
        if q2_answer == "yes":
            return {"success": False, "error": "Image is too blurry or dark. Please take a clearer photo in good lighting."}
            
        return {"success": True}
    except Exception as e:
        # If pre-check fails (e.g. rate limits), fail-open to let the main request attempt analysis
        return {"success": True}


def _analyze_sync(image_bytes: bytes, analysis_type: str, language: str = "en") -> dict:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return {
            "success": False,
            "error": "⚙️ Gemini API key not configured. Please add your free API key to the .env file. Get one at https://aistudio.google.com"
        }
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        image = PIL.Image.open(io.BytesIO(image_bytes))
        
        # ── Q1 & Q2 Image Quality Pre-check ──
        precheck = _precheck_image(client, image)
        if not precheck["success"]:
            return {
                "success": False,
                "error": precheck["error"]
            }

        prompt = PROMPTS.get(analysis_type, PROMPTS["disease"])

        # ── Language Specific Instructions ──
        if language == "gu":
            lang_instruction = """
CRITICAL LANGUAGE INSTRUCTION (IMPORTANT):
1. You MUST respond completely in the Gujarati language (ગુજરાતી) for all descriptive texts, symptoms, root causes, chemical/organic treatment details, prevention tips, growth recommendations, disclaimers, economic values, and warnings.
2. Even if the identified crop (e.g. grapes, etc.) is NOT on your primary list of crops grown in Gujarat, you MUST still provide all analyses, warnings, scientific names, details, and disclaimers in Gujarati (ગુજરાતી). Do NOT fall back to English under any circumstances.
3. The ONLY parts of the response that must remain in uppercase English are the exact headers/keys (e.g., 🌿 PLANT IDENTIFIED, 🦠 DISEASE STATUS, ⚠️ SEVERITY, 📊 CONFIDENCE, 📋 SYMPTOMS OBSERVED, 🔬 ROOT CAUSE, 💊 TREATMENT PLAN, 🛡️ PREVENTION, ⏰ URGENCY, 📋 CROP DETAILS, 📋 TOP 3 POSSIBLE MATCHES, 📋 DESCRIPTION, 🌱 GROWING CONDITIONS, 📅 GROWING TIMELINE, 💰 ECONOMIC VALUE, 📈 CURRENT GROWTH STAGE & HEALTH, 🚀 TOP 5 TIPS TO GROW FASTER IN GUJARAT, 🧪 FERTILIZER RECOMMENDATIONS, 💧 WATER & IRRIGATION, ☀️ SUNLIGHT & SPACING, 📅 HARVEST OPTIMIZATION, 🧴 CHEMICAL TREATMENTS (GUJARAT MARKET), 🌿 ORGANIC/NATURAL TREATMENTS, ⚠️ RECOVERY & TREATING STAGES, 📅 RECOVERY TIMELINE, 🌱 ESTIMATED GROWTH STAGE, 🧪 RECOMMENDED FERTILIZERS (NPK RATIO), 🧪 MICRONUTRIENT ADVICE, 📅 FERTILIZER SCHEDULE, 💧 DRIP FERTIGATION SCHEDULE, ⚠️ WHAT TO AVOID, 💡 PRO TIP) so that they can be matched and parsed properly by the system.
4. Translation rules:
   - "🌿 PLANT IDENTIFIED: Grape" -> "🌿 PLANT IDENTIFIED: દ્રાક્ષ (Grapes)" (Scientific name can be in parenthesis).
   - If a disease status, severity, or any detailed note is written, it must be translated entirely to Gujarati.
   - Any expert notice, warning, or crop compatibility notice must be written in Gujarati (e.g., instead of "grapes are not on the list...", write: "દ્રાક્ષ ગુજરાત માટેના મુખ્ય પાકની યાદીમાં નથી, પરંતુ તેનું વિશ્લેષણ નીચે મુજબ છે...").
   - If you need to mention chemical/pesticide/fungicide names, write them in Gujarati script or English in parentheses, but keep the surrounding instructions in Gujarati.

તમારે આ સૂચનાઓનું સખત પાલન કરવું જ પડશે. તમામ વિગતવાર વર્ણન, લક્ષણો, ઉપાયો, ખાતર વિગતો અને ટીપ્સ સંપૂર્ણપણે ગુજરાતી ભાષામાં જ હોવી જોઈએ.
"""
            prompt += "\n" + lang_instruction

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt, image]
        )
        result_text = response.text

        crop_name = _extract_field(result_text, ["PLANT IDENTIFIED", "CROP IDENTIFIED", "CROP", "PLANT"])
        disease = _extract_field(result_text, ["DISEASE STATUS", "CONDITION"])
        severity = _extract_field(result_text, ["SEVERITY"])
        summary = result_text[:400].replace("\n", " ").strip()
        
        # ── Parse Confidence Score ──
        confidence_raw = _extract_field(result_text, ["CONFIDENCE"])
        
        confidence_score = "High (85-100%)" # default
        if "medium" in confidence_raw.lower():
            confidence_score = "Medium (60-84%)"
        elif "low" in confidence_raw.lower():
            confidence_score = "Low (below 60%)"
        elif "high" in confidence_raw.lower():
            confidence_score = "High (85-100%)"

        confidence_warning = None
        if "low" in confidence_score.lower():
            confidence_warning = "Low confidence — please upload a clearer or closer photo of the affected area"

        return {
            "success": True,
            "result": result_text,
            "analysis_type": analysis_type,
            "analysis_label": ANALYSIS_LABELS.get(analysis_type, analysis_type),
            "crop_name": crop_name,
            "disease_name": disease,
            "severity": severity,
            "summary": summary,
            "confidence_score": confidence_score,
            "confidence_warning": confidence_warning
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


async def analyze_image(image_bytes: bytes, analysis_type: str, language: str = "en") -> dict:
    return await asyncio.to_thread(_analyze_sync, image_bytes, analysis_type, language)


def _chat_sync(message: str, history: list, language: str = "en") -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return "⚙️ AgriBot needs a Gemini API key to work. Please add it to your .env file. Get a free key at https://aistudio.google.com"
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        chat_history = []
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        system_instruction = CHATBOT_SYSTEM
        if language == "gu":
            system_instruction += "\nCRITICAL: You must answer the user entirely in the Gujarati language (ગુજરાતી) using natural, friendly conversational terms."

        chat = client.chats.create(
            model="models/gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system_instruction),
            history=chat_history
        )
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


async def chat_with_agribot(message: str, history: list, language: str = "en") -> str:
    return await asyncio.to_thread(_chat_sync, message, history, language)
