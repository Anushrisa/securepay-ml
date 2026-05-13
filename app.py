import os
import random
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from sklearn.ensemble import RandomForestClassifier, IsolationForest

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'securepay-secret-key-2024')

# ========== ML MODEL 1: Risk Score - RandomForest ==========
def train_risk_model():
    data = {
        'amount': [100, 5000, 50000, 100000, 500, 2000, 75000],
        'lat': [28.6, 19.0, 12.9, 28.6, 22.5, 13.0, 28.6],
        'lon': [77.2, 72.8, 77.5, 77.2, 88.3, 80.2, 77.2],
        'is_approved': [1, 1, 0, 0, 1, 1, 0],
        'risk': [5, 10, 70, 90, 8, 12, 85]
    }
    df = pd.DataFrame(data)
    X = df[['amount', 'lat', 'lon', 'is_approved']]
    y = df['risk']
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    return model

# ========== ML MODEL 2: Anomaly Detection - IsolationForest ==========
def train_anomaly_model():
    data = {
        'amount': [100, 200, 300, 150, 250, 100000, 80, 120],
        'hour': [10, 14, 18, 11, 15, 3, 9, 16],
        'day': [1, 2, 3, 1, 2, 7, 1, 4]
    }
    df = pd.DataFrame(data)
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(df)
    return model

RISK_MODEL = train_risk_model()
ANOMALY_MODEL = train_anomaly_model()

RBI_APPROVED_DOMAINS = [
    'amazon.in', 'flipkart.com', 'myntra.com', 'paytm.com',
    'phonepe.com', 'googlepay.in', 'razorpay.com', 'billdesk.com'
]

# ========== HELPER FUNCTIONS ==========
def extract_domain(user_input):
    if not user_input:
        return ""
    clean_input = str(user_input).strip().lower()
    clean_input = clean_input.replace("https://", "").replace("http://", "")
    clean_input = clean_input.split('/')[0].split(':')[0]
    return clean_input

def get_location():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=3)
        data = response.json()
        if data.get('status') == 'success':
            return data['city'], round(data['lat'], 4), round(data['lon'], 4)
    except:
        pass
    return "Delhi", 28.6139, 77.2090

def is_rbi_approved_merchant(merchant_input):
    merchant_domain = extract_domain(merchant_input)
    if not merchant_domain:
        return False, "", 0, "Invalid"
    is_approved = merchant_domain in RBI_APPROVED_DOMAINS
    return is_approved, merchant_domain, 0, "RBI-Check"

def predict_risk_score(amount, lat, lon, is_approved):
    try:
        features = np.array([[float(amount), float(lat), float(lon), int(is_approved)]])
        risk = RISK_MODEL.predict(features)
        if hasattr(risk, '__len__'):
            risk = risk[0]
        return int(risk)
    except:
        return 25

def predict_anomaly_score(amount):
    try:
        hour = datetime.now().hour
        day = datetime.now().weekday()
        features = np.array([[float(amount), hour, day]])
        anomaly = ANOMALY_MODEL.decision_function(features)
        if hasattr(anomaly, '__len__'):
            anomaly = anomaly[0]
        score = int((1 - anomaly) * 50)
        return max(0, min(100, score))
    except:
        return 15

def run_ml_analysis(amount, lat, lon, is_approved):
    # ML 1: Risk Score
    risk_score = predict_risk_score(amount, lat, lon, is_approved)

    # ML 2: Anomaly Score
    anomaly_score = predict_anomaly_score(amount)

    # Final Combined Risk
    final_risk = int((risk_score + anomaly_score) / 2)

    model_name = "RandomForest+Anomaly"
    if is_approved and amount < 50000:
        model_name = f"Whitelist+{model_name}"
        final_risk = int(final_risk * 0.5) # Whitelist pe risk aadha

    return final_risk, model_name, risk_score, anomaly_score

def send_otp_email(email, otp):
    print(f"[OTP] Sent to {email}: {otp}") # Console me dikhega
    return True

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    if not email:
        return render_template('login.html', error="Email required")
    session['user'] = email
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')

@app.route('/check_site', methods=['POST'])
def check_site():
    if 'user' not in session:
        return redirect('/')

    merchant_input = request.form.get('merchant', '').strip()
    try:
        amount = float(request.form.get('amount', 0))
    except:
        amount = 0

    if not merchant_input:
        return render_template('result.html', result="ERROR", final_msg="Merchant name cannot be empty")
    if amount <= 0:
        return render_template('result.html', result="ERROR", final_msg="Amount must be greater than 0")

    is_approved, merchant_domain, _, _ = is_rbi_approved_merchant(merchant_input)
    city, lat, lon = get_location()

    # 👇 2 ML Model + Risk Score yahi nikal raha
    final_risk, ml_model_name, risk_score, anomaly_score = run_ml_analysis(amount, lat, lon, is_approved)

    session['txn_details'] = {
        'merchant': merchant_input, 'merchant_domain': merchant_domain,
        'amount': amount, 'is_approved': is_approved,
        'final_risk': final_risk, 'risk_score': risk_score,
        'anomaly_score': anomaly_score, 'ml_model_name': ml_model_name,
        'city': city, 'lat': lat, 'lon': lon
    }

    # 👇 Approve page pe Risk Score bhej diya
    return render_template('approve.html',
                           amount=amount, merchant=merchant_input,
                           verified_as=merchant_domain, check_method=ml_model_name,
                           is_approved=is_approved, city=city, lat=lat, lon=lon,
                           final_risk=final_risk, risk_score=risk_score,
                           anomaly_score=anomaly_score)

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    send_otp_email(session['user'], otp)
    return render_template('otp.html', email=session['user'])

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')
    user_otp = request.form.get('otp', '').strip()
    if user_otp == session.get('otp'):
        txn = session['txn_details']
        session.pop('otp', None)
        session.pop('txn_details', None)
        return render_template('success.html',
                               amount=txn['amount'], merchant=txn['merchant_domain'],
                               city=txn['city'], risk=txn['final_risk'])
    else:
        return render_template('otp.html', error="Invalid OTP", email=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
