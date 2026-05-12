from flask import Flask, render_template, request, redirect, session
import random
import datetime
import smtplib
import requests
import json
import pandas as pd
import os
from email.mime.text import MIMEText
from urllib.parse import urlparse
from ml_model import predict_fraud_risk, train_model
from ml_url_model import predict_url_safe, train_url_model

app = Flask(__name__)
app.secret_key = "SecurePay_2026_RBI_Compliant_ML_@#$"

# ==================== 👇 YAHAN 5 JAGAH APNI DETAILS DAAL ====================
USER_EMAIL = "vanshikauser65@gmail.com"
USER_PASS = "1234"
VALID_PIN = "1111"
ADMIN_USERNAME = "admin"
ADMIN_PASS = "admin@123"

def send_email_otp(receiver_email, otp):
    sender_email = "vanshikauser65@gmail.com"
    app_password = "gahcyhlytluunzlz"
    try:
        msg = MIMEText(f"Dear Customer,\n\nYour SecurePay OTP is: {otp}\n\nValid for 2 minutes.\nNever share this OTP with anyone.\n\nRegards,\nSecurePay Security Team")
        msg['Subject'] = "SecurePay - Transaction OTP"
        msg['From'] = f"SecurePay <{sender_email}>"
        msg['To'] = receiver_email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email Error:", e)

otp_store = {}
TRANSACTION_FILE = "transactions.json"
BETUL_LAT, BETUL_LONG = 21.9064, 77.9006

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
    clean_domain_base = clean_domain.split('.')[0]
    for official_domain, keywords in RBI_APPROVED_MERCHANTS.items():
        official_base = official_domain.split('.')[0].replace('.co', '')
        if clean_domain_base == official_base:
            return True, official_domain, 0, "Rule-Keyword"
        for keyword in keywords:
            if keyword in user_merchant_input.lower():
                return True, official_domain, 0, "Rule-Keyword"
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

def save_transaction(data):
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            transactions = json.load(f)
    except:
        transactions = []
    transactions.append(data)
    with open(TRANSACTION_FILE, 'w') as f:
        json.dump(transactions, f, indent=4)
    if len(transactions) % 10 == 0:
        train_model()
        train_url_model()

def get_city_from_gps(lat, lon):
    try:
        res = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json",
                          headers={'User-Agent': 'SecurePay-RBI-Compliant/1.0'}, timeout=3)
        data = res.json()
        address = data.get('address', {})
        city = address.get('city') or address.get('town') or address.get('village') or address.get('state')
        return f"{city}, {address.get('country')}" if city else "India"
    except:
        return "Location Unavailable"

def get_all_transactions():
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

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

    session['txn_details'] = {
        "card": card, "pin": pin, "amount": amount, "merchant_input": merchant_input,
        "merchant_domain": matched_domain, "lat": lat, "lon": lon,
        "is_approved": is_approved, "check_method": check_method, "merchant_risk": merchant_risk
    }

    if not is_approved or merchant_risk >= 60:
        dist_from_betul = haversine(BETUL_LAT, BETUL_LONG, lat, lon) if lat!= 0 else 0
        city_gps = get_city_from_gps(lat, lon) if lat!= 0 else "GPS Disabled"
        current_hour = datetime.datetime.now().hour

        ml_result = predict_fraud_risk(amount, current_hour, dist_from_betul, is_approved)
        if ml_result[0] is not None:
            final_risk = max(60, ml_result[0])
            ml_model_name = ml_result[1]
        else:
            final_risk = 60
            ml_model_name = "Rule-Engine"

        trans_data = {
            "transaction_id": f"TXN{random.randint(100000,999999)}",
            "email": session['user'],
            "card_masked": "**** **** **** " + card[-4:] if len(card) >= 4 else "****",
            "amount": amount,
            "merchant_input": merchant_input,
            "merchant_verified": matched_domain,
            "rbi_approved": is_approved,
            "risk_score": final_risk,
            "result": "BLOCKED",
            "location": f"{city_gps} ⚠️",
            "timestamp": str(datetime.datetime.now())[:19],
            "risk_factors": f"Blacklisted Merchant | {check_method} | ML: {ml_model_name}",
            "ml_risk_used": "Yes 🤖",
            "ml_model_name": ml_model_name,
            "ml_url_used": "Yes 🤖" if "ML" in check_method else "No",
            "check_method": check_method,
            "distance_from_base_km": round(dist_from_betul, 2),
            "gps_coordinates": f"{lat}, {lon}"
        }
        save_transaction(trans_data)

        return render_template('blocked.html', reason=f"Merchant Not Verified: {check_method}",
                             merchant=merchant_input, domain=matched_domain)
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
            send_email_otp(email, otp)
            return render_template('otp.html', amount=data['amount'],
                                 merchant=data['merchant_input'], domain=data['merchant_domain'])
        else:
            return render_template('result.html', result="CANCELLED", final_msg="Transaction Cancelled by User")
    return render_template('approve.html', amount=data['amount'],
                         merchant=data['merchant_input'], domain=data['merchant_domain'],
                         check_method=data['check_method'])

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

    risk, reasons = 0, []
    ml_risk_used = True
    ml_model_name = "Rule-Engine"
    ml_url_used = "ML" in data['check_method']

    if len(data['card'])!= 16 or not data['card'].isdigit():
        risk += 40
        reasons.append("Invalid Card Number")
    if data['pin']!= VALID_PIN:
        risk += 40
        reasons.append("Incorrect PIN")
    risk += data['merchant_risk']
    if data['merchant_risk'] == 60:
        reasons.append(f"Merchant Issue: {data['check_method']}")

    dist_from_betul = haversine(BETUL_LAT, BETUL_LONG, data['lat'], data['lon']) if data['lat']!= 0 else 0
    city_gps = get_city_from_gps(data['lat'], data['lon']) if data['lat']!= 0 else "GPS Disabled"
    current_hour = datetime.datetime.now().hour

    ml_result = predict_fraud_risk(data['amount'], current_hour, dist_from_betul, data['is_approved'])
    if ml_result[0] is not None:
        risk = ml_result[0]
        ml_model_name = ml_result[1]
        reasons.append(f"ML Analysis: {ml_model_name}")
    else:
        ml_model_name = "Rule-Engine"

    risk = min(risk, 100)
    result = "BLOCKED" if risk >= 50 else "APPROVED"
    final_msg = "Transaction Blocked by Security Protocol" if result == "BLOCKED" else "Transaction Approved"

    trans_data = {
        "transaction_id": f"TXN{random.randint(100000,999999)}",
        "email": email,
        "card_masked": "**** **** **** " + data['card'][-4:],
        "amount": data['amount'],
        "merchant_input": data['merchant_input'],
        "merchant_verified": data['merchant_domain'],
        "rbi_approved": data['is_approved'],
        "risk_score": risk,
        "result": result,
        "location": f"{city_gps} {'⚠️' if result=='BLOCKED' else '✅'}",
        "timestamp": str(datetime.datetime.now())[:19],
        "risk_factors": " | ".join(reasons) if reasons else "All checks passed",
        "ml_risk_used": "Yes 🤖",
        "ml_model_name": ml_model_name,
        "ml_url_used": "Yes 🤖" if ml_url_used else "No",
        "check_method": data['check_method'],
        "distance_from_base_km": round(dist_from_betul, 2),
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
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASS:
            session['admin'] = username
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error="Invalid Username or Password")
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/admin_login')
    transactions = get_all_transactions()
    total = len(transactions)
    approved = len([t for t in transactions if t['result'] == 'APPROVED'])
    blocked = len([t for t in transactions if t['result'] == 'BLOCKED'])
    total_amount = sum([t['amount'] for t in transactions if t['result'] == 'APPROVED'])

    risk_low = len([t for t in transactions if t['risk_score'] <= 25])
    risk_medium = len([t for t in transactions if 25 < t['risk_score'] <= 50])
    risk_high = len([t for t in transactions if 50 < t['risk_score'] <= 75])
    risk_critical = len([t for t in transactions if t['risk_score'] > 75])

    risk_data = {
        'low': risk_low, 'medium': risk_medium,
        'high': risk_high, 'critical': risk_critical
    }

    return render_template('admin.html', transactions=transactions[-50:],
                         total=total, approved=approved, blocked=blocked,
                         total_amount=total_amount, admin=session['admin'],
                         risk_data=json.dumps(risk_data))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')

# ==================== ✅ RAILWAY KE LIYE UPDATED CODE ====================
if __name__ == "__main__":
    print("🚀 Starting SecurePay ML Training...")
    train_model()
    train_url_model()
    print("✅ Models Trained Successfully!")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)