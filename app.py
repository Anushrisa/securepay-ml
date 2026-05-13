from flask import Flask, request, render_template, redirect, session
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== CONFIG ==========
SMTP_EMAIL = "Vanshikauser65@gmail.com"
SMTP_PASSWORD = "djdaihesjsddahzs" # Apna App Password daalo

# ========== DEMO USERS ==========
DEMO_USERS = {
    'admin@securepay.com': 'admin123',
    'user@securepay.com': 'user123',
    'Vanshikauser65@gmail.com': 'user123' # Apni ID
}

# ========== ML MODELS ==========
ml_model = None
url_model = None

def train_model():
    global ml_model
    data = {
        'amount': [500, 5000, 25000, 1000, 75000, 200, 15000, 45000, 8000, 120000],
        'hour': [10, 22, 3, 14, 1, 9, 23, 2, 16, 4],
        'location_risk': [1, 3, 8, 2, 9, 1, 7, 8, 3, 10],
        'frequency': [5, 2, 1, 4, 1, 6, 2, 1, 3, 1],
        'fraud': [0, 0, 1, 0, 1, 0, 1, 1, 0, 1]
    }
    df = pd.DataFrame(data)
    X = df[['amount', 'hour', 'location_risk', 'frequency']]
    y = df['fraud']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
    ml_model.fit(X_train, y_train)
    print("✅ ML Model Trained")

def train_url_model():
    global url_model
    data = {
        'has_https': [1, 0, 1, 0, 1, 0],
        'domain_length': [10, 25, 8, 30, 12, 35],
        'has_ip': [0, 1, 0, 1, 0, 1],
        'suspicious': [0, 1, 0, 1, 0, 1]
    }
    df = pd.DataFrame(data)
    X = df[['has_https', 'domain_length', 'has_ip']]
    y = df['suspicious']
    url_model = RandomForestClassifier(n_estimators=50, random_state=42)
    url_model.fit(X, y)
    print("✅ URL Model Trained")

def get_location_risk(lat, lon):
    safe_zones = [(28.6139, 77.2090), (19.0760, 72.8777), (12.9716, 77.5946)]
    for safe_lat, safe_lon in safe_zones:
        if abs(lat - safe_lat) < 1 and abs(lon - safe_lon) < 1:
            return 2
    return 8

def get_url_risk(domain):
    https = 1 if domain.startswith('https') else 0
    length = len(domain)
    has_ip = 1 if any(char.isdigit() for char in domain.split('.')[0]) else 0
    features = np.array([[https, length, has_ip]])
    risk = url_model.predict_proba(features)[0][1] * 100
    return int(risk)

# ========== ROUTES ==========
@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email'].lower()
    password = request.form['password']
    if DEMO_USERS.get(email) == password:
        session['user'] = email
        print(f"LOGIN TRY: {email} | {password}")
        return redirect('/dashboard')
    print(f"LOGIN TRY: {email} | {password}")
    return render_template('login.html', error="Invalid credentials")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/approve', methods=['POST'])
def approve():
    if 'user' not in session: return redirect('/')

    amount = float(request.form['amount'])
    merchant = request.form['merchant']
    card = request.form['card']
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])

    try:
        # ML Prediction
        hour = pd.Timestamp.now().hour
        loc_risk = get_location_risk(lat, lon)
        freq = 3 # dummy
        features = np.array([[amount, hour, loc_risk, freq]])
        risk_score = int(ml_model.predict_proba(features)[0][1] * 100)
        url_risk = get_url_risk(merchant)
        final_risk = int((risk_score + url_risk) / 2)

    except Exception as e:
        print(f"ML Error: {e}")
        final_risk = 50 # fallback

    txn_details = {
        'amount': amount,
        'merchant_domain': merchant,
        'card': card,
        'lat': lat,
        'lon': lon,
        'risk_score': final_risk,
        'rbi_status': '✅ RBI APPROVED' if final_risk < 60 else '❌ RBI FLAGGED'
    }
    session['txn_details'] = txn_details
    return render_template('approve.html', txn=txn_details)

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'user' not in session or 'txn_details' not in session: return redirect('/')

    action = request.form.get('action', '')
    if action == 'cancel':
        session.pop('txn_details', None)
        return render_template('result.html', result="BLOCKED", final_msg="Transaction Cancelled")

    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    txn = session['txn_details']

    # 👇 DEMO KE LIYE OTP LOGS ME PRINT KARO
    print(f"✅✅✅ DEMO OTP: {otp} for {session['user']}")

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
        </body></html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ OTP {otp} sent to {session['user']}")

    except Exception as e:
        print(f"❌ OTP Error: {e} | Using console OTP instead")

    return render_template('otp.html', email=session['user'], amount=txn['amount'])

@app.route('/verify', methods=['POST'])
def verify():
    if 'user' not in session or 'otp' not in session: return redirect('/')

    user_otp = request.form['otp']
    if user_otp == session['otp']:
        session.pop('otp', None)
        txn = session.pop('txn_details', None)
        return render_template('success.html', txn=txn)
    else:
        return render_template('otp.html', email=session['user'], amount=session['txn_details']['amount'], error="Invalid OTP")

# ========== GUNICORN FIX ==========
train_model()
train_url_model()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
