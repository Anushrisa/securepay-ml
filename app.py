from flask import Flask, render_template, request, session, redirect
import datetime
import random
import requests
import smtplib
from email.mime.text import MIMEText
import math
import os
import json
import numpy as np # 👈 Fix 1: Numpy import add kiya
import pandas as pd

print("Starting SecurePay...")
from ml_model import predict_fraud_risk
from ml_url_model import predict_url_safe
print("Models loaded successfully")

app = Flask(__name__)
app.secret_key = 'securepay-secret-key-2024'

# ---------------- Config ----------------
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASS = "your_app_password"
BETUL_LAT, BETUL_LONG = 21.9015, 77.9013
VALID_PIN = "123456"
TRANSACTION_FILE = "transactions.json"
otp_store = {}

# ---------------- Domain Security ----------------
BLACKLISTED_DOMAINS = [
    "phishing-site.com", "fake-amazon.net", "scam-flipkart.org",
    "fraud-paytm.com", "malicious-site.net", "phish-bank.com"
]

def extract_domain(user_input):
    if not user_input:
        return""
    clean_input = user_input.strip().lower()
    clean_input = clean_input.replace("https://", "").replace("http://", "")
    clean_input = clean_input.split('/')[0]
    clean_input = clean_input.split(':')[0]
    return clean_input

# ---------------- Geo Utils ----------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_location():
    try:
        data = requests.get("http://ip-api.com/json/", timeout=3).json()
        return data.get("city", "Unknown"), data.get("lat", 0), data.get("lon", 0)
    except:
        return "Unknown", 0, 0

# ---------------- Email OTP ----------------
def send_email_otp(receiver_email, otp):
    try:
        msg = MIMEText(f"Your SecurePay OTP is: {otp}\n\nValid for 2 minutes.")
        msg["Subject"] = "SecurePay Transaction OTP"
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# ---------------- ML Integration ----------------
def run_ml_analysis(amount, lat, lon, is_approved):
    ml_risk = predict_fraud_risk(amount, lat, lon, is_approved)

    # 👈 Fix 2: ML model array/list return karta hai, usko number banao
    if hasattr(ml_risk, '__len__'):
        ml_risk = ml_risk[0]

    ml_model_name = "RandomForest-ML"
    if is_approved and amount < 50000:
        ml_model_name = f"Whitelist+{ml_model_name}"

    ml_risk = int(float(ml_risk) * 0.1)
    return ml_risk, ml_model_name

def is_rbi_approved_merchant(user_merchant_input):
    clean_domain = extract_domain(user_merchant_input)

    for blacklisted in BLACKLISTED_DOMAINS:
        if blacklisted in clean_domain:
            return False, "Blacklisted", 60, "Rule-Blacklist"

    try:
        ml_risk, ml_model_name = predict_url_safe(clean_domain)
        if ml_risk > 40:
            return False, f"ML-Blocked ({clean_domain})", ml_risk, ml_model_name
        else:
            return True, clean_domain, ml_risk, ml_model_name
    except:
        return True, clean_domain, 5, "Rule-Whitelist"

# ---------------- Transaction Storage ----------------
def save_transaction(data):
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            transactions = json.load(f)
    except:
        transactions = []

    transactions.append(data)
    with open(TRANSACTION_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)

# ---------------- Routes ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            session['user'] = email
            return redirect('/dashboard')
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

    merchant_input = request.form.get('merchant',' ')
    amount = float(request.form.get('amount', 0))

    if not merchant_input:
        return render_templates('result.html', result="ERROR", final_msg="MERCHANT name cannot be empty")
    is_approved, merchant_domain, ml_risk, ml_model_name = is_rbi_approved_merchant(merchant_input)
    city, lat, lon = get_location()

    ml_analysis_risk, ml_analysis_name = run_ml_analysis(amount, lat, lon, is_approved)

    session['txn_details'] = {
        "card": "1234567890123456",
        "pin": "123456",
        "amount": amount,
        "merchant_input": merchant_input,
        "merchant_domain": merchant_domain,
        "is_approved": is_approved,
        "city": city,
        "lat": lat,
        "lon": lon,
        "ml_risk_score": ml_risk + ml_analysis_risk,
        "ml_model_name": ml_analysis_name
    }

    return render_template('approve.html',
                         amount=amount,
                         merchant=merchant_input,
                         domain=merchant_domain,
                         ml_model_name=ml_analysis_name,
                         risk_score=ml_risk + ml_analysis_risk,
                         city=city)

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
            return render_template('otp.html', amount=data['amount'], merchant=data['merchant_input'], domain=data['merchant_domain'])
        else:
            return render_template('result.html', result="CANCELLED", final_msg="Transaction Cancelled by User")

    return render_template('approve.html', amount=data['amount'], merchant=data['merchant_input'], domain=data['merchant_domain'], ml_model_name=data['ml_model_name'], risk_score=data['ml_risk_score'], city=data['city'])

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
        "amount": data["amount"], # 👈 Fix 3: Syntax quote fix kiya
        "merchant_input": data['merchant_input'],
        "merchant_verified": data['merchant_domain'],
        "rbi_approved": data['is_approved'],
        "risk_score": risk,
        "result": result,
        "location": f"{data['city']} {'Safe' if result=='APPROVED' else 'Risk'}",
        "timestamp": str(datetime.datetime.now())[:19],
        "risk_factors": " | ".join(reasons),
        "ml_risk_used": "Yes",
        "ml_model_name": data['ml_model_name'],
        "check_method": data['ml_model_name'],
        "distance_from_base_km": round(haversine(BETUL_LAT, BETUL_LONG, data['lat'], data['lon']), 2) if data['lat']!= 0 else 0,
        "gps_coordinates": f"{data['lat']}, {data['lon']}"
    }
    save_transaction(trans_data)
    del otp_store[email]
    session.pop('txn_details', None)

    return render_template('result.html', **trans_data, final_msg=final_msg)

@app.route('/history')
def history():
    try:
        with open(TRANSACTION_FILE, 'r') as f:
            transactions = json.load(f)
    except:
        transactions = []
    return render_template('history.html', transactions=transactions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
