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
app.secret_key = os.environ.get('SECRET_KEY', 'securepay-secret-2024')

# ========== SMTP CONFIG ==========
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'Vanshikauser65@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'gahcyhlytluunzlz')

# ========== GLOBAL ==========
ml_model = None
url_model = None

# ========== DEMO USERS ==========
DEMO_USERS = {
    'admin@securepay.com': 'admin123',
    'user@securepay.com': 'user123' ,
    'Vanshikauser65@gmail.com': 'user123'
}

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

RBI_APPROVED_DOMAINS = ['amazon.in', 'flipkart.com', 'myntra.com', 'paytm.com', 'phonepe.com']

# ========== HELPER FUNCTIONS ==========
def extract_domain(user_input):
    if not user_input: return ""
    clean_input = str(user_input).strip().lower()
    clean_input = clean_input.replace("https://", "").replace("http://", "")
    clean_input = clean_input.split('/')[0].split(':')[0]
    return clean_input

def validate_card(card, pin):
    card_clean = card.replace(" ", "")
    if len(card_clean)!= 16 or not card_clean.isdigit(): return False, "Invalid Card Number"
    if len(pin)!= 4 or not pin.isdigit(): return False, "Invalid PIN"
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
    except: pass
    return "Delhi", 28.6139, 77.2090

def is_rbi_approved_merchant(merchant_input):
    merchant_domain = extract_domain(merchant_input)
    if not merchant_domain: return False, ""
    return merchant_domain in RBI_APPROVED_DOMAINS, merchant_domain

def run_ml_analysis(amount, lat, lon, is_approved, card_valid):
    try:
        features = np.array([[float(amount), float(lat), float(lon), int(is_approved), int(card_valid)]])
        risk_score = int(ml_model.predict(features)[0])
        hour = datetime.now().hour
        day = datetime.now().weekday()
        features2 = np.array([[float(amount), hour, day, 1]])
        anomaly = url_model.decision_function(features2)[0]
        anomaly_score = max(0, min(100, int((1 - anomaly) * 50)))
        final_risk = int((risk_score + anomaly_score) / 2)
        fraud_detected = final_risk > 70 or (not is_approved and amount > 10000)
        if is_approved and amount < 50000: final_risk = int(final_risk * 0.5)
        return final_risk, "RandomForest+IsolationForest", risk_score, anomaly_score, fraud_detected
    except Exception as e:
        print(f"ML Error: {e}")
        return 25, "Default", 25, 25, False

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    print(f"LOGIN TRY: {email} | {password}")

    if not validate_email(email):
        return render_template('login.html', error="Valid Email ID required")

    if email in DEMO_USERS and DEMO_USERS[email] == password:
        session['user'] = email
        return redirect('/dashboard')
    else:
        return render_template('login.html', error="Invalid Email or Password")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template('dashboard.html', user=session['user'])

@app.route('/check_site', methods=['POST'])
def check_site():
    if 'user' not in session: return redirect('/')

    try:
        card = request.form.get('card', '').strip()
        pin = request.form.get('pin', '').strip()
        merchant_input = request.form.get('merchant_url', '').strip()
        amount = float(request.form.get('amount', 0))
        lat = float(request.form.get('lat', 0))
        lon = float(request.form.get('lon', 0))

        if lat == 0 or lon == 0: city, lat, lon = get_location()
        else: city = "User Location"

        card_valid, card_msg = validate_card(card, pin)
        if not merchant_input: return render_template('result.html', result="ERROR", final_msg="Merchant URL required")
        if amount <= 0: return render_template('result.html', result="ERROR", final_msg="Amount must be > 0")
        if not card_valid: return render_template('result.html', result="ERROR", final_msg=card_msg)

        is_approved, merchant_domain = is_rbi_approved_merchant(merchant_input)
        final_risk, ml_model_name, risk_score, anomaly_score, fraud_detected = run_ml_analysis(amount, lat, lon, is_approved, 1)

        if fraud_detected:
            return render_template('result.html', result="FRAUD DETECTED",
                                   final_msg=f"Transaction Blocked. Risk: {final_risk}/100", risk=final_risk)

        session['txn_details'] = {
            'merchant': merchant_input, 'merchant_domain': merchant_domain, 'amount': amount,
            'final_risk': final_risk, 'risk_score': risk_score, 'anomaly_score': anomaly_score,
            'ml_model_name': ml_model_name, 'city': city, 'lat': lat, 'lon': lon,
            'masked_card': "**** **** **** " + card.replace(" ", "")[-4:],
            'txn_id': f"TXN{random.randint(10000000, 99999999)}", 'is_approved': is_approved
        }

        return render_template('approve.html', amount=amount, merchant=merchant_input,
                               verified_as=merchant_domain, check_method=ml_model_name,
                               final_risk=final_risk, risk_score=risk_score, anomaly_score=anomaly_score,
                               masked_card=session['txn_details']['masked_card'],
                               city=city, lat=lat, lon=lon, is_approved=is_approved)

    except Exception as e:
        print(f"Check Site Error: {e}")
        return render_template('result.html', result="ERROR", final_msg="Something went wrong. Try again.")

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')

    action = request.form.get('action', '')
    if action == 'cancel':
        session.pop('txn_details', None)
        return render_template('result.html', result="BLOCKED", final_msg="Transaction Cancelled")

    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    txn = session['txn_details']

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = session['user']
        msg['Subject'] = f"SecurePay OTP: {otp}"

        body = f"""
        <html><body>
        <h2>🏦 SecurePay</h2>
        <h1 style="color:#1e3c72;">Your OTP: {otp}</h1>
        <p><b>Amount:</b> ₹{txn['amount']}</p>
        <p><b>Merchant:</b> {txn['merchant_domain']}</p>
        <p><b>Txn ID:</b> {txn['txn_id']}</p>
        <p style="color:red;">Valid for 10 minutes. Do not share with anyone.</p>
        </body></html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ OTP {otp} sent to {session['user']}")

    except Exception as e:
        print(f"❌ OTP Error: {e}")
        # 👇 FIX: amount add kiya taaki otp.html crash na ho
        return render_template('otp.html', error=f"OTP failed: {str(e)}", email=session['user'], amount=txn['amount'])

    # 👇 FIX: amount add kiya taaki otp.html crash na ho
    return render_template('otp.html', email=session['user'], amount=txn['amount'])

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    if 'user' not in session or 'txn_details' not in session: return redirect('/')
    user_otp = request.form.get('otp', '').strip()
    if user_otp == session.get('otp'):
        txn = session['txn_details']
        session.pop('otp', None)
        session.pop('txn_details', None)
        return render_template('success.html', amount=txn['amount'],
                               merchant=txn['merchant_domain'], city=txn['city'],
                               risk=txn['final_risk'], txn_id=txn['txn_id'],
                               masked_card=txn['masked_card'])
    else:
        txn = session['txn_details']
        return render_template('otp.html', error="Invalid OTP", email=session['user'], amount=txn['amount'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    train_model()
    train_url_model()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
