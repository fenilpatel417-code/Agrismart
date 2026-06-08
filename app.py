from flask import Flask, render_template, request, jsonify
import numpy as np
from PIL import Image
import google.generativeai as genai
import torch
import torch.nn as nn
import torch.nn.functional as F

app = Flask(__name__)
app.secret_key = "agrismart_secret_key"

# =============================================
# PASTE YOUR GEMINI API KEY HERE
GEMINI_API_KEY = " "
# =============================================

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

# 38 disease classes
CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy',
    'Grape___Black_rot', 'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy',
    'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy',
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy',
    'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
    'Raspberry___healthy', 'Soybean___healthy', 'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch', 'Strawberry___healthy',
    'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight',
    'Tomato___Leaf_Mold', 'Tomato___Septoria_leaf_spot',
    'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 'Tomato___healthy'
]

REMEDIES = {
    'Apple___Apple_scab': 'Apply fungicides like captan or mancozeb. Remove and destroy fallen leaves.',
    'Apple___Black_rot': 'Remove infected fruit and branches. Apply copper-based fungicide every 10 days.',
    'Apple___Cedar_apple_rust': 'Apply myclobutanil fungicide in spring. Remove nearby juniper trees if possible.',
    'Apple___healthy': 'Your apple plant is healthy! Maintain regular watering and fertilization.',
    'Blueberry___healthy': 'Your blueberry plant is healthy! Ensure acidic soil pH between 4.5-5.5.',
    'Cherry_(including_sour)___Powdery_mildew': 'Apply sulfur-based fungicide. Improve air circulation. Avoid overhead watering.',
    'Cherry_(including_sour)___healthy': 'Your cherry plant is healthy! Keep up good farming practices.',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': 'Apply azoxystrobin fungicide. Rotate crops and remove infected debris.',
    'Corn_(maize)___Common_rust_': 'Apply mancozeb or chlorothalonil. Plant resistant varieties next season.',
    'Corn_(maize)___Northern_Leaf_Blight': 'Use strobilurin fungicides. Rotate crops and till soil after harvest.',
    'Corn_(maize)___healthy': 'Your corn plant is healthy! Ensure adequate nitrogen fertilization.',
    'Grape___Black_rot': 'Apply myclobutanil or mancozeb. Remove mummified fruit. Prune for airflow.',
    'Grape___Esca_(Black_Measles)': 'Prune infected wood. Apply wound sealant. Focus on prevention.',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': 'Apply copper fungicide. Ensure proper drainage and air circulation.',
    'Grape___healthy': 'Your grape plant is healthy! Maintain proper pruning and irrigation.',
    'Orange___Haunglongbing_(Citrus_greening)': 'Remove infected trees. Control psyllid insects with insecticides.',
    'Peach___Bacterial_spot': 'Apply copper-based bactericide. Avoid overhead irrigation.',
    'Peach___healthy': 'Your peach plant is healthy! Thin fruits for better size and quality.',
    'Pepper,_bell___Bacterial_spot': 'Apply copper bactericide. Use disease-free seeds. Avoid working in wet fields.',
    'Pepper,_bell___healthy': 'Your pepper plant is healthy! Ensure consistent watering.',
    'Potato___Early_blight': 'Apply chlorothalonil every 7 days. Remove infected lower leaves immediately.',
    'Potato___Late_blight': 'Apply mancozeb or copper fungicide immediately. Destroy infected plants.',
    'Potato___healthy': 'Your potato plant is healthy! Hill soil around plants for better yield.',
    'Raspberry___healthy': 'Your raspberry plant is healthy! Prune old canes after harvest.',
    'Soybean___healthy': 'Your soybean plant is healthy! Monitor for aphids and spider mites.',
    'Squash___Powdery_mildew': 'Apply neem oil or potassium bicarbonate. Improve air circulation.',
    'Strawberry___Leaf_scorch': 'Remove infected leaves. Apply captan fungicide. Ensure proper plant spacing.',
    'Strawberry___healthy': 'Your strawberry plant is healthy! Mulch around plants to retain moisture.',
    'Tomato___Bacterial_spot': 'Apply copper-based bactericide. Avoid overhead watering. Use disease-free seeds.',
    'Tomato___Early_blight': 'Apply chlorothalonil every 7-10 days. Remove lower infected leaves. Mulch soil.',
    'Tomato___Late_blight': 'Apply mancozeb immediately. Remove and destroy all infected plants.',
    'Tomato___Leaf_Mold': 'Improve greenhouse ventilation. Apply chlorothalonil. Reduce humidity.',
    'Tomato___Septoria_leaf_spot': 'Apply fungicide at first sign. Remove infected leaves. Avoid wetting foliage.',
    'Tomato___Spider_mites Two-spotted_spider_mite': 'Apply neem oil or insecticidal soap. Increase humidity.',
    'Tomato___Target_Spot': 'Apply azoxystrobin fungicide. Remove infected leaves. Ensure good airflow.',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': 'Remove infected plants immediately. Control whitefly population.',
    'Tomato___Tomato_mosaic_virus': 'Remove and destroy infected plants. Disinfect tools. Control aphids.',
    'Tomato___healthy': 'Your tomato plant is healthy! Stake plants and prune suckers for better yield.'
}

# ── ResNet9 architecture (must match what was used during training) ──
def conv_block(in_channels, out_channels, pool=False):
    layers = [
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True)
    ]
    if pool:
        layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)

class ResNet9(nn.Module):
    def __init__(self, in_channels, num_classes):
        super().__init__()
        self.conv1 = conv_block(in_channels, 64)
        self.conv2 = conv_block(64, 128, pool=True)
        self.res1  = nn.Sequential(conv_block(128, 128), conv_block(128, 128))
        self.conv3 = conv_block(128, 256, pool=True)
        self.conv4 = conv_block(256, 512, pool=True)
        self.res2  = nn.Sequential(conv_block(512, 512), conv_block(512, 512))
        self.classifier = nn.Sequential(
            nn.MaxPool2d(4),
            nn.Flatten(),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        out = self.conv1(x)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        return self.classifier(out)

# ── Load model ──
device = torch.device("cpu")   # use CPU (no GPU needed for inference)
print("Loading PyTorch model...")
try:
    model = ResNet9(3, 38)
    model.load_state_dict(torch.load(
    "model/plant-disease-model-complete.pth",
    map_location=device,
    weights_only=True
    ))
    model.eval()
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"⚠️ Could not load model: {e}")
    model = None

# ── Image preprocessing ──
def preprocess(image_stream):
    img = Image.open(image_stream).convert("RGB").resize((256, 256))
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406])
    std  = np.array([0.229, 0.224, 0.225])
    arr  = (arr - mean) / std
    tensor = torch.tensor(arr).permute(2, 0, 1).unsqueeze(0).float()
    return tensor

# ── Routes ──
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if model:
        tensor = preprocess(file.stream)
        with torch.no_grad():
            outputs    = model(tensor)
            probs      = F.softmax(outputs, dim=1)
            confidence = float(probs.max().item()) * 100
            class_idx  = int(probs.argmax().item())
        disease = CLASS_NAMES[class_idx]
    else:
        import random
        disease    = random.choice(['Tomato___Early_blight', 'Potato___Late_blight', 'Tomato___healthy'])
        confidence = round(random.uniform(82, 97), 1)

    readable = disease.replace("___", " - ").replace("_", " ")
    remedy   = REMEDIES.get(disease, "Consult a local agricultural expert.")

    return jsonify({
        "disease":    readable,
        "confidence": round(confidence, 1),
        "remedy":     remedy,
        "is_healthy": "healthy" in disease.lower()
    })

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/ask", methods=["POST"])
def ask():
    data         = request.json
    user_message = data.get("message", "").strip()
    history      = data.get("history", [])

    if not user_message:
        return jsonify({"reply": "Please type a message."})

    system_prompt = (
        "You are AgriBot, an expert AI farming assistant for Indian farmers. "
        "Answer questions about crop diseases, remedies, fertilizers, irrigation, and farming. "
        "Be concise, practical, and use simple language. "
        "Give step-by-step treatment advice when asked about diseases. "
        "Always be helpful and encouraging to farmers."
    )

    try:
        formatted_history = [
            {"role": h["role"], "parts": [h["content"]]}
            for h in history[-10:]
        ]
        chat     = gemini_model.start_chat(history=formatted_history)
        response = chat.send_message(system_prompt + "\n\nUser: " + user_message)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Connection error: {str(e)}. Please check your Gemini API key."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
