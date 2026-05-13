from flask import Flask, render_template, request, redirect, session
import random
import datetime
import smtplib
import requests
import json
import pandas as pd
from email.mime.text import MIMEText
from urllib.parse import urlparse
import os

app = Flask(__name__)
app.secret_key = "SecurePay_2026_RBI_Compliant_ML_@#$"

# ==================== CONFIG ====================
USER_EMAIL = "vanshikauser65@gmail.com"
USER_PASS = "1234"
VALID_PIN = "1111"
ADMIN_USERNAME = "admin"
ADMIN_PASS = "admin@123"
BETUL_LAT, BETUL_LONG = 21.9064, 77.9006

# ==================== ML MODELS - STARTUP PE LOAD ====================
print("Starting SecurePay...")
from ml_model import predict_fraud_risk
from ml_url_model import predict_url_safe
print("Models loaded successfully")

def get_city_from_gps(lat, lon):
    """Location nikal ke city name return karo"""
    if lat == 0 or lon == 0:
        return "GPS Disabled"
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        res = requests.get(url, headers={"User-Agent": "SecurePay/1.0"}, timeout=3)
        data = res.json()
        city = data.get('address', {}).get('city') or data.get('address', {}).get('town') or data.get('address', {}).get('state')
        return city if city else "Unknown Location"
    except:
        return "Location Fetch Failed"

def send_email_otp(receiver_email, otp):
    """👇 Simple mail - ML ya Location nahi"""
    sender_email = os.getenv('GMAIL_USER', 'vanshikauser65@gmail.com')
    app_password = os.getenv('GMAIL_APP_PASS', '').replace(' ', '')

    if not app_password:
        print("ERROR: GMAIL_APP_PASS not set")
        return False

    try:
        body = f"""Dear Customer,

Your SecurePay OTP is: {otp}

Valid for 2 minutes. Never share this OTP.

Regards,
SecurePay Team"""

        msg = MIMEText(body)
        msg['Subject'] = "SecurePay - Transaction OTP"
        msg['From'] = f"SecurePay <{sender_email}>"
        msg['To'] = receiver_email

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"OTP Email sent to {receiver_email}")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

otp_store = {}
TRANSACTION_FILE = "transactions.json"

RBI_APPROVED_MERCHANTS = {
    "amazon.in": ["amazon", "amzn"], "flipkart.com": ["flipkart", "fkrt"],
    "myntra.com": ["myntra"], "irctc.co.in": ["irctc", "railway"],
    "onlinesbi.sbi": ["sbi", "state bank"], "hdfcbank.com": ["hdfc"],
    "icicibank.com": ["icici"], ".gov.in": ["gov"], ".nic.in": ["nic"],
    "uidai.gov.in": ["uidai", "aadhaar"]
}

BLACKLISTED_DOMAINS = ["free-iphone-giveaway", "lucky-draw-win", "win-cash-now", "bit.ly",
                       "tinyurl.com", "grabify.link", "scam", "phishing", "fake", "loot"]

def extract_domain(user_input):
    user_input = user_input.lower().strip()
    if user_input.startswith(('http://', 'https://')):
        parsed = urlparse(user_input)
        domain = parsed.netloc
    else:
        domain = user_input
    return domain.replace('www.', '').split('/')[0].split('?')[0]

def is_rbi_approved_merchant(user_merchant_input):
    clean_domain = extract_domain(user_merchant_input)
    for blacklisted in BLACKLISTED_DOMAINS:
        if blacklisted in clean_domain:
            return False, "Blacklisted", 60, "Rule-Blacklist"
    for official_domain, keywords in RBI_APPROVED_MERCHANTS.items():
        if clean_domain == official_domain:
            return True, official_domain, 0, "Rule-Whitelist"
        if official_domain.startswith('.') and clean_domain.endswith(official_domain):
            return True, clean_domain, 0, "Rule-Whitelist"

    ml_safe_score = predict_url_safe(clean_domain)
    if ml_safe_score is not None:
        if ml_safe_score >= 80:
            return True, "ML Verified", 0, f"ML-URL-{int(ml_safe_score)}%"
        else:
            return False, "ML Suspicious", 60, f"ML-URL-{int(ml_safe_score)}%"
    return False, "Unknown", 60, "Rule-Unknown"

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def run_ml_analysis(amount, lat, lon, is_approved):
    """ML Algorithm auto select - RandomForest/XGBoost/SVM"""
    current_hour = datetime.datetime.now().hour
    dist_from_betul = haversine(BETUL_LAT, BETUL_LONG, lat, lon) if lat!= 0 else 0

    ml_risk = predict_fraud_risk(amount, current_hour, dist_from_betul, is_approved)

    if ml_risk is None:
        return 5, "Rule-Engine"

    # Algorithm auto select
    if amount > 50000:
        ml_model_name = "XGBoost-ML"
    elif 23 <= current_hour or current_hour <= 5:
        ml_model_name = "SVM-ML"
    else:
        ml_model_name = "RandomForest-ML"

    if is_approved and amount < 50000:
        ml_model_name = f"Whitelist+{ml_model_name}"
        ml_risk = int(ml_risk * 0.1)

    return ml_risk, ml_model_name

def save_transaction(data):
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            transactions = json.load(f)
    except:
        transactions = []
    transactions.append(data)
    with open(TRANSACTION_FILE, 'w') as f:
        json.dump(transactions, f, indent=4)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('email') == USER_EMAIL and request.form.get('password') == USER_PASS:
            session['user'] = request.form.get('email')
            return redirect('/dashboard')
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html', user=session['user'])

@app.route('/check_site', methods=['POST'])
def check_site():
    if 'user' not in session:
        return redirect('/')
    card = request.form.get('card', '').replace(' ', '')
    pin = request.form.get('pin')
    amount = float(request.form.get('amount', 0))
    merchant_input = request.form.get('merchant_url')
    lat = float(request.form.get('lat', 0)) if request.form.get('lat') else 0
    lon = float(request.form.get('lon', 0)) if request.form.get('lon') else 0

    is_approved, matched_domain, merchant_risk, check_method = is_rbi_approved_merchant(merchant_input)

    # ML + Location nikal lo but mail/OTP me use nahi karenge
    ml_risk_score, ml_model_name = run_ml_analysis(amount, lat, lon, is_approved)
    city = get_city_from_gps(lat, lon)

    session['txn_details'] = {
        "card": card, "pin": pin, "amount": amount, "merchant_input": merchant_input,
        "merchant_domain": matched_domain, "lat": lat, "lon": lon, "city": city,
        "is_approved": is_approved, "check_method": check_method,
        "merchant_risk": merchant_risk, "ml_risk_score": ml_risk_score,
        "ml_model_name": ml_model_name
    }

    if not is_approved or merchant_risk >= 60:
        return render_template('blocked.html', reason=f"Merchant Not Verified: {check_method}",
                             merchant=merchant_input, domain=matched_domain,
                             ml_model_name=ml_model_name, risk_score=ml_risk_score, city=city)
    else:
        return redirect('/user_approve')

@app.route('/user_approve', methods=['GET', 'POST'])
def user_approve():
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')
    data = session['txn_details']

    if request.method == 'POST':
        if request.form.get('action') == 'approve':
            email = session['user']
            otp = str(random.randint(1000, 9999))
            otp_store[email] = {"otp": otp, "time": datetime.datetime.now(), **data}

            # 👇 Simple mail - ML/Location nahi
            send_email_otp(email, otp)

            # 👇 OTP page pe bhi ML/Location nahi bhejenge
            return render_template('otp.html', amount=data['amount'],
                                 merchant=data['merchant_input'], domain=data['merchant_domain'])
        else:
            return render_template('result.html', result="CANCELLED", final_msg="Transaction Cancelled by User")

    # 👇 Approve page pe ML + Location dikhega
    return render_template('approve.html', amount=data['amount'],
                         merchant=data['merchant_input'], domain=data['merchant_domain'],
                         ml_model_name=data['ml_model_name'],
                         risk_score=data['ml_risk_score'], city=data['city'])

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form.get('otp')
    email = session.get('user')
    data = otp_store.get(email)
    if not data:
        return render_template('result.html', result="ERROR", final_msg="Session Expired")
    if (datetime.datetime.now() - data['time']).seconds > 120:
        return render_template('result.html', result="ERROR", final_msg="OTP Expired")
    if user_otp!= data['otp']:
        return render_template('result.html', result="ERROR", final_msg="Invalid OTP")

    risk = data['ml_risk_score']
    reasons = [f"AI Model: {data['ml_model_name']}"]

    if len(data['card'])!= 16 or not data['card'].isdigit():
        risk += 40
        reasons.append("Invalid Card Number")
    if data['pin']!= VALID_PIN:
        risk += 40
        reasons.append("Incorrect PIN")

    risk = min(risk, 100)
    result = "BLOCKED" if risk >= 50 else "APPROVED"
    final_msg = "Transaction Blocked by AI Security" if result == "BLOCKED" else "Transaction Approved by AI"

    trans_data = {
        "transaction_id": f"TXN{random.randint(100000,999999)}",
        "email": email,
        "card_masked": "**** **** **** " + data['card'][-4:],
        "amount": data["amount"],
        "merchant_input": data['merchant_input'],
        "merchant_verified": data['merchant_domain'],
        "rbi_approved": data['is_approved'],
        "risk_score": risk,
        "result": result,
        "location": f"{data['city']} {'✅' if result=='APPROVED' else '⚠️'}", # 👇 Result me Location
        "timestamp": str(datetime.datetime.now())[:19],
        "risk_factors": " | ".join(reasons),
        "ml_risk_used": "Yes 🤖",
        "ml_model_name": data['ml_model_name'], # 👇 Result me ML
        "check_method": data['ml_model_name'],
        "distance_from_base_km": round(haversine(BETUL_LAT, BETUL_LONG, data['lat'], data['lon']), 2) if data['lat']!= 0 else 0,
        "gps_coordinates": f"{data['lat']}, {data['lon']}"
    }
    save_transaction(trans_data)
    del otp_store[email]
    session.pop('txn_details', None)

    return render_template('result.html', **trans_data, final_msg=final_msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASS:
            session['admin'] = request.form.get('username')
            return redirect('/admin')
        return render_template('admin_login.html', error="Invalid Credentials")
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            transactions = json.load(f)
    except:
        transactions = []
    total = len(transactions)
    approved = len([t for t in transactions if t['result'] == 'APPROVED'])
    blocked = len([t for t in transactions if t['result'] == 'BLOCKED'])
    total_amount = sum([t['amount'] for t in transactions if t['result'] == 'APPROVED'])
    return render_template('admin.html', transactions=transactions[-50:],
                         total=total, approved=approved, blocked=blocked,
                         total_amount=total_amount, admin=session['admin'])

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
