import os
import random
import numpy as np
import pandas as pd
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, session, redirect, url_for
from sklearn.ensemble import RandomForestClassifier, IsolationForest

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'securepay-secret-key-2024')

# ========== SMTP CONFIG - MAIL OTP KE LIYE ==========
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-app-password')
# ===================================================

# ========== ML MODEL 1: Risk Score ==========
def train_model():
    global ml_model
    data = {
        'amount': [100, 5000, 50000, 100000, 500, 2000, 75000, 1000, 25000, 150000],
        'lat': [28.6, 19.0, 12.9, 28.6, 22.5, 13.0, 28.6, 17.4, 23.0, 28.6],
        'lon': [77.2, 72.8, 77.5, 77.2, 88.3, 80.2, 77.2, 78.4, 72.5, 77.2],
        'is_approved': [1, 1, 0, 0, 1, 1, 0, 1, 0, 0],
        'card_valid': [1, 1, 1, 0, 1, 1, 0, 1, 1, 0],
        'risk': [5, 10, 70, 95, 8, 12, 85, 15, 60, 98]
    }
    df = pd.DataFrame(data)
    X = df[['amount', 'lat', 'lon', 'is_approved', 'card_valid']]
    y = df['risk']
    ml_model = RandomForestClassifier(n_estimators=10, random_state=42)
    ml_model.fit(X, y)
    print("✅ Risk Model Trained")

# ========== ML MODEL 2: Anomaly Detection ==========
def train_url_model():
    global url_model
    data = {
        'amount': [100, 200, 300, 150, 250, 100000, 80, 120, 90000, 200000],
        'hour': [10, 14, 18, 11, 15, 3, 9, 16, 2, 1],
        'day': [1, 2, 3, 1, 2, 7, 1, 4, 6, 7],
        'pin_attempts': [1, 1, 2, 1, 1, 5, 1, 1, 4, 6]
    }
    df = pd.DataFrame(data)
    url_model = IsolationForest(contamination=0.1, random_state=42)
    url_model.fit(df)
    print("✅ Anomaly Model Trained")

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

def validate_card(card, pin):
    card_clean = card.replace(" ", "")
    if len(card_clean)!= 16 or not card_clean.isdigit():
        return False, "Invalid Card Number"
    if len(pin)!= 4 or not pin.isdigit():
        return False, "Invalid PIN"
    return True, "Valid"

def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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
        return False, ""
    is_approved = merchant_domain in RBI_APPROVED_DOMAINS
    return is_approved, merchant_domain

def predict_risk_score(amount, lat, lon, is_approved, card_valid):
    try:
        features = np.array([[float(amount), float(lat), float(lon), int(is_approved), int(card_valid)]])
        risk = ml_model.predict(features)
        if hasattr(risk, '__len__'):
            risk = risk[0]
        return int(risk)
    except:
        return 25

def predict_anomaly_score(amount, pin_attempts=1):
    try:
        hour = datetime.now().hour
        day = datetime.now().weekday()
        features = np.array([[float(amount), hour, day, pin_attempts]])
        anomaly = url_model.decision_function(features)
        if hasattr(anomaly, '__len__'):
            anomaly = anomaly[0]
        score = int((1 - anomaly) * 50)
        return max(0, min(100, score))
    except:
        return 15

def run_ml_analysis(amount, lat, lon, is_approved, card_valid):
    risk_score = predict_risk_score(amount, lat, lon, is_approved, card_valid)
    anomaly_score = predict_anomaly_score(amount)
    final_risk = int((risk_score + anomaly_score) / 2)

    model_name = "RandomForest+IsolationForest"
    fraud_detected = False

    if final_risk > 70 or (not is_approved and amount > 10000):
        fraud_detected = True
        model_name = "FRAUD_DETECTED+" + model_name
    elif is_approved and amount < 50000 and card_valid:
        model_name = f"Whitelist+{model_name}"
        final_risk = int(final_risk * 0.5)

    return final_risk, model_name, risk_score, anomaly_score, fraud_detected

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    if not validate_email(email):
        return render_template('login.html', error="Valid Email ID required")
    session['user'] = email
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html', user=session['user'])

@app.route('/check_site', methods=['POST'])
def check_site():
    if 'user' not in session:
        return redirect('/')

    card = request.form.get('card', '').strip()
    pin = request.form.get('pin', '').strip()
    merchant_input = request.form.get('merchant_url', '').strip()

    try:
        amount = float(request.form.get('amount', 0))
    except:
        amount = 0

    try:
        lat = float(request.form.get('lat', 0))
        lon = float(request.form.get('lon', 0))
        if lat == 0 or lon == 0:
            city, lat, lon = get_location()
        else:
            city = "User Location"
    except:
        city, lat, lon = get_location()

    card_valid, card_msg = validate_card(card, pin)
    if not merchant_input:
        return render_template('result.html', result="ERROR", final_msg="Merchant URL cannot be empty")
    if amount <= 0:
        return render_template('result.html', result="ERROR", final_msg="Amount must be greater than 0")
    if not card_valid:
        return render_template('result.html', result="ERROR", final_msg=card_msg)

    is_approved, merchant_domain = is_rbi_approved_merchant(merchant_input)

    final_risk, ml_model_name, risk_score, anomaly_score, fraud_detected = run_ml_analysis(
        amount, lat, lon, is_approved, 1 if card_valid else 0
    )

    masked_card = "**** **** **** " + card.replace(" ", "")[-4:]
    txn_id = f"TXN{random.randint(10000000, 99999999)}"

    if fraud_detected:
        return render_template('result.html',
                               result="FRAUD DETECTED",
                               final_msg=f"Transaction Blocked by AI. Risk Score: {final_risk}/100. Reason: Suspicious Activity Detected.",
                               risk=final_risk)

    session['txn_details'] = {
        'merchant': merchant_input, 'merchant_domain': merchant_domain,
        'amount': amount, 'is_approved': is_approved,
        'final_risk': final_risk, 'risk_score': risk_score,
        'anomaly_score': anomaly_score, 'ml_model_name': ml_model_name,
        'city': city, 'lat': lat, 'lon': lon, 'masked_card': masked_card,
        'user_email': session['user'], 'txn_id': txn_id
    }

    return render_template('approve.html',
                           amount=amount, merchant=merchant_input,
                           verified_as=merchant_domain, check_method=ml_model_name,
                           is_approved=is_approved, city=city, lat=lat, lon=lon,
                           final_risk=final_risk, risk_score=risk_score,
                           anomaly_score=anomaly_score, masked_card=masked_card)

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')

    action = request.form.get('action', '')
    if action == 'block':
        txn = session['txn_details']
        session.pop('txn_details', None)
        return render_template('result.html', result="BLOCKED", final_msg="Transaction Cancelled by User")

    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    txn = session['txn_details']

    # ========== MAIL OTP SEND ==========
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = session['user']
        msg['Subject'] = "SecurePay - Transaction OTP"

        body = f"""
        <html><body style="font-family: Arial;">
            <h2 style="color: #1e3c72;">🏦 SecurePay Bank</h2>
            <p>Your OTP for transaction verification:</p>
            <h1 style="color:#1e3c72; letter-spacing: 5px; background: #f0f0f0; padding: 15px; text-align: center;">{otp}</h1>
            <table style="margin-top: 20px;">
                <tr><td><b>Amount:</b></td><td>₹{txn['amount']:,.2f}</td></tr>
                <tr><td><b>Merchant:</b></td><td>{txn['merchant_domain']}</td></tr>
                <tr><td><b>Valid for:</b></td><td>5 minutes</td></tr>
            </table>
            <p style="color:red; margin-top: 20px;">⚠️ Never share this OTP with anyone.</p>
        </body></html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ OTP sent to {session['user']}")
    except Exception as e:
        print(f"❌ OTP Error: {e}")
        print(f"[DEMO OTP] {session['user']}: {otp}")
    # ===================================

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
                               city=txn['city'], risk=txn['final_risk'],
                               txn_id=txn['txn_id'], masked_card=txn['masked_card'])
    else:
        return render_template('otp.html', error="Invalid OTP", email=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==================== RAILWAY KE LIYE ====================
if __name__ == "__main__":
    print("🚀 Starting SecurePay ML Training...")
    train_model()
    train_url_model()
    print("✅ Models Trained Successfully!")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
