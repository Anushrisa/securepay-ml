from flask import Flask, request, redirect, session
import random
import os
import urllib.request
import urllib.error
import json
import re
from datetime import datetime
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle
import io

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('SMTP_EMAIL', "vanshikauser65@gmail.com")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ML Model ko memory me rakhenge, file me nahi
ml_model = None

def get_ml_model():
    global ml_model
    if ml_model is not None:
        return ml_model

    # Pehli baar run pe dummy data se train karo
    print("Training new ML model...")
    normal_data = np.array([
        [500, 14, 600, 2], [1200, 18, 1000, 1], [300, 12, 400, 3],
        [2000, 16, 1800, 1], [150, 10, 200, 5], [800, 20, 900, 2],
        [50, 11, 100, 4], [5000, 15, 4500, 1], [250, 13, 300, 3],
        [1000, 19, 1100, 2]
    ])
    ml_model = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    ml_model.fit(normal_data)
    return ml_model

def init_session():
    if 'transactions' not in session:
        session['transactions'] = []

def check_fraud_link(text):
    if not text:
        return False, "Empty merchant"
    text_lower = text.lower()

    suspicious_words = ['free','lottery','prize','winner','kyc','verify','urgent','suspended','blocked','gift','reward','bonus','claim','bit.ly','tinyurl','cutt.ly','rb.gy','t.co']
    for word in suspicious_words:
        if word in text_lower:
            return True, f"Suspicious keyword: '{word}'"

    trusted_domains = ['amazon.in','amazon.com','flipkart.com','myntra.com','ajio.com','paytm.com','phonepe.com','googlepay.in','swiggy.com','zomato.com','irctc.co.in','makemytrip.com']
    if text_lower.startswith('http'):
        if not any(d in text_lower for d in trusted_domains):
            return True, "Untrusted website link"

    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text_lower):
        return True, "IP address based link - High risk"

    return False, "Safe"

def calculate_ml_risk(amount, merchant, user_email):
    try:
        model = get_ml_model()
        hour = datetime.now().hour

        txns = session.get('transactions', [])
        user_txns = [t for t in txns if t.get('user') == user_email and t['status'] == 'Success']

        user_avg = np.mean([float(t['amount']) for t in user_txns]) if user_txns else 1000
        txn_count_today = len([t for t in user_txns if t['time'].startswith(datetime.now().strftime('%Y-%m-%d'))])

        features = np.array([[float(amount), hour, user_avg, txn_count_today]])
        prediction = model.predict(features)
        anomaly_score = model.decision_function(features)[0]

        risk_score = int(max(0, min(100, 50 - (anomaly_score * 100))))

        if hour >= 0 and hour <= 5 and float(amount) > 3000:
            risk_score = min(100, risk_score + 30)
        if float(amount) > user_avg * 5:
            risk_score = min(100, risk_score + 25)

        return risk_score, "ML Anomaly" if prediction[0] == -1 else "Normal Pattern"

    except Exception as e:
        print(f"ML Error: {e}")
        return 30, "ML Error - Default"

def send_otp_mail(to_email, otp, amount, merchant):
    if not SENDGRID_API_KEY:
        raise Exception("SENDGRID_API_KEY not set in Railway Variables")

    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": "SecurePay"},
        "subject": f"SecurePay OTP: {otp}",
        "content": [{"type": "text/html", "value": f"<div style='font-family:Arial;padding:20px'><h2>SecurePay OTP</h2><h1 style='font-size:32px'>{otp}</h1><p><b>Amount:</b> ₹{amount}</p><p><b>Merchant:</b> {merchant}</p></div>"}]
    }

    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send")
    req.add_header('Authorization', f'Bearer {SENDGRID_API_KEY}')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, json.dumps(data).encode('utf-8'))

STYLE = """<style>
body{font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:0}
.navbar{background:#1565c0;color:white;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.navbar a{color:white;text-decoration:none;background:#c62828;padding:6px 12px;border-radius:4px;font-size:14px;margin-left:8px}
.container{max-width:1100px;margin:30px auto;background:white;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
h3{color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px;margin-top:0}
label{display:block;margin:12px 0 4px 0;font-weight:600;color:#333}
input{width:100%;padding:10px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
button{width:100%;background:#43a047;color:white;padding:12px;border:none;border-radius:4px;font-size:16px;cursor:pointer;margin-top:15px}
button:hover{background:#2e7d32}
.btn-cancel{background:#d32f2f}
.btn-cancel:hover{background:#b71c1c}
table{width:100%;border-collapse:collapse;margin:15px 0}
td,th{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:14px}
th{background:#f5f5f5;font-weight:600}
.badge{background:#43a047;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-danger{background:#c62828;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-warning{background:#ff9800;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
.flex{display:flex;gap:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:20px 0}
.card{background:#f5f5f5;padding:15px;border-radius:8px;text-align:center}
.card h2{margin:5px 0;color:#1565c0}
.block-alert{background:#ffcdd2;border:2px solid #c62828;padding:20px;border-radius:8px;text-align:center}
.block-alert h2{color:#b71c1c;margin:0 0 10px 0}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

@app.route('/')
def home():
    init_session()
    if 'user' in session:
        return redirect('/dashboard')
    return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b> <a href="/admin">Admin Login</a></div>
    <div class="container"><h3>User Login</h3>
    <form action="/login" method="POST">
    <label>Email</label><input name="email" value="vanshikauser65@gmail.com" type="email" required>
    <label>Password</label><input name="password" value="user123" type="password" required>
    <button>Login</button></form></div>'''

@app.route('/login', methods=['POST'])
def login():
    init_session()
    if request.form['email'] == "vanshikauser65@gmail.com" and request.form['password'] == "user123":
        session['user'] = "vanshikauser65@gmail.com"
        return redirect('/dashboard')
    return f'{STYLE}<div class="container"><div class="error">Wrong Login</div><a href="/">Try Again</a></div>'

@app.route('/dashboard')
def dashboard():
    init_session()
    if 'user' not in session:
        return redirect('/')
    return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b>
    <div>vanshikauser65@gmail.com | <a href="/admin">Admin</a> | <a href="/logout">Logout</a></div></div>
    <div class="container"><h3>New Transaction</h3>
    <form action="/check" method="POST">
    <label>Card Number</label><input name="card" value="1234 5678 9012 3456" required>
    <label>Card PIN</label><input name="pin" type="password" maxlength="4" required>
    <label>Amount (₹)</label><input name="amount" type="number" min="1" required>
    <label>Merchant Website/URL</label><input name="merchant" placeholder="amazon.in" required>
    <button>Verify & Proceed</button></form></div>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/check', methods=['POST'])
def check():
    init_session()
    if 'user' not in session:
        return redirect('/')

    merchant_input = request.form['merchant']
    amount = request.form['amount']

    is_fraud_rule, reason_rule = check_fraud_link(merchant_input)
    ml_risk_score, ml_reason = calculate_ml_risk(amount, merchant_input, session['user'])

    if is_fraud_rule or ml_risk_score > 70:
        final_reason = reason_rule if is_fraud_rule else f"ML Risk Score High: {ml_risk_score}/100 - {ml_reason}"
        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'user': session['user'],'merchant': merchant_input,'amount': amount,'status': 'Blocked','reason': final_reason,'ml_score': ml_risk_score})
        session['transactions'] = txns

        return f'''{STYLE}<div class="container"><div class="block-alert"><h2>🚨 Transaction Blocked!</h2>
        <p><b>Reason:</b> {final_reason}</p><p><b>ML Risk Score:</b> {ml_risk_score}/100</p>
        <p><b>Merchant:</b> {merchant_input}</p></div>
        <a href='/dashboard'><button>Back to Dashboard</button></a></div>'''

    session['txn'] = {'card': request.form['card'],'amount': amount,'merchant': merchant_input,'risk_score': ml_risk_score}
    risk_badge = '<span class="badge">LOW</span>' if ml_risk_score < 40 else '<span class="badge-warning">MEDIUM</span>'

    return f'''{STYLE}<div class="container"><h3>Transaction Details</h3>
    <table><tr><td>Card:</td><td>**** {request.form['card'][-4:]}</td></tr>
    <tr><td>Amount:</td><td>₹{amount}</td></tr>
    <tr><td>Merchant:</td><td>{merchant_input}</td></tr>
    <tr><td>Rule Check:</td><td><span class="badge">PASSED</span></td></tr></table>
    <h3>🤖 AI Risk Analysis</h3>
    <table><tr><td>ML Risk Score:</td><td><b>{ml_risk_score}/100</b> {risk_badge}</td></tr>
    <tr><td>Pattern:</td><td>{ml_reason}</td></tr></table>
    <div class="flex">
    <form action="/send_otp" method="POST" style="width:100%"><button>Approve & Send OTP</button></form>
    <a href="/dashboard" style="width:100%"><button class="btn-cancel">Cancel</button></a></div></div>'''

@app.route('/send_otp', methods=['POST'])
def send_otp():
    init_session()
    if 'user' not in session:
        return redirect('/')
    txn = session.get('txn')
    if not txn:
        return f'{STYLE}<div class="container"><div class="error">Session expired. Start again.</div><a href="/dashboard">Back</a></div>'

    otp = str(random.randint(100000, 999))
    session['otp'] = otp

    try:
        send_otp_mail("vanshikauser65@gmail.com", otp, txn['amount'], txn['merchant'])
        return f'''{STYLE}<div class="container"><h3>OTP Verification</h3>
        <p>OTP sent to vanshikauser65@gmail.com</p>
        <p style="color:gray;font-size:13px">Check spam folder also</p>
        <form action="/verify" method="POST">
        <label>Enter 6-digit OTP</label><input name="otp" maxlength="6" required>
        <button>Verify & Pay</button></form></div>'''
    except Exception as e:
        print(f"[ERROR] OTP failed: {str(e)}")
        return f'''{STYLE}<div class="container">
        <div class="error">OTP Send Failed</div>
        <p>Check SendGrid sender verification and API key.</p>
        <a href="/dashboard"><button>Back</button></a></div>'''

@app.route('/verify', methods=['POST'])
def verify():
    init_session()
    if request.form['otp'] == session.get('otp'):
        txn = session.pop('txn', None)
        session.pop('otp', None)
        if not txn:
            return f'{STYLE}<div class="container"><div class="error">Session expired</div><a href="/dashboard">Back</a></div>'

        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'user': session['user'],'merchant': txn['merchant'],'amount': txn['amount'],'card_last4': txn['card'][-4:],'status': 'Success','reason': '-','ml_score': txn.get('risk_score', 0)})
        session['transactions'] = txns

        return f'''{STYLE}<div class="container"><div class="success"><h2>✅ Payment Successful!</h2>
        <p><b>₹{txn['amount']}</b> paid to <b>{txn['merchant']}</b></p>
        <p>Risk Score: {txn.get('risk_score', 0)}/100 - Verified by AI</p></div>
        <a href='/dashboard'><button>New Transaction</button></a></div>'''
    return f'{STYLE}<div class="container"><div class="error">Wrong OTP</div><a href="/dashboard">Back</a></div>'

@app.route('/admin')
def admin_login_page():
    if 'admin' in session:
        return redirect('/admin/dashboard')
    return f'''{STYLE}<div class="navbar"><b>🔐 SecurePay Admin</b> <a href="/">User Login</a></div>
    <div class="container"><h3>Admin Login</h3>
    <form action="/admin/login" method="POST">
    <label>Username</label><input name="username" value="admin" required>
    <label>Password</label><input name="password" type="password" value="admin123" required>
    <button>Login as Admin</button></form></div>'''

@app.route('/admin/login', methods=['POST'])
def admin_login():
    init_session()
    if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
        session['admin'] = ADMIN_USERNAME
        return redirect('/admin/dashboard')
    return f'{STYLE}<div class="container"><div class="error">Wrong Admin Credentials</div><a href="/admin">Try Again</a></div>'

@app.route('/admin/dashboard')
def admin_dashboard():
    init_session()
    if 'admin' not in session:
        return redirect('/admin')

    txns = session.get('transactions', [])
    total_blocked = len([t for t in txns if t['status'] == 'Blocked'])
    total_verified = len([t for t in txns if t['status'] == 'Success'])
    total_all = len(txns)
    avg_risk = round(np.mean([t.get('ml_score', 0) for t in txns if t['status'] == 'Success']), 1) if total_verified > 0 else 0

    keywords = {'free': 0, 'lottery': 0, 'prize': 0, 'gift': 0, 'kyc': 0, 'bit.ly': 0}
    for txn in txns:
        if txn['status'] == 'Blocked':
            for key in keywords:
                if key in txn['merchant'].lower():
                    keywords[key] += 1

    blocked_rows = ""
    for txn in reversed([t for t in txns if t['status'] == 'Blocked'][-50:]):
        blocked_rows += f"<tr><td>{txn['time']}</td><td>{txn['user']}</td><td><span class='badge-danger'>{txn['merchant']}</span></td><td>₹{txn['amount']}</td><td>{txn['reason']}</td><td>ML: {txn.get('ml_score', 'N/A')}</td></tr>"
    if not blocked_rows:
        blocked_rows = '<tr><td colspan="6" style="text-align:center;color:#999">No fraud attempts yet</td></tr>'

    verified_rows = ""
    for txn in reversed([t for t in txns if t['status'] == 'Success'][-50:]):
        verified_rows += f"<tr><td>{txn['time']}</td><td>{txn['user']}</td><td><span class='badge'>{txn['merchant']}</span></td><td>₹{txn['amount']}</td><td>**** {txn['card_last4']}</td><td>Risk: {txn.get('ml_score', 0)}/100</td></tr>"
    if not verified_rows:
        verified_rows = '<tr><td colspan="6" style="text-align:center;color:#999">No verified transactions yet</td></tr>'

    return f'''{STYLE}<div class="navbar"><b>🔐 SecurePay Admin Panel</b><div>Admin | <a href="/admin/logout">Logout</a></div></div>
    <div class="container">
    <h3>AI Fraud Detection Dashboard <span style="background:#ff9800;color:white;padding:5px 10px;border-radius:4px;font-size:12px;margin-left:10px">Auto-refresh: 10s</span></h3>
    <div class="grid">
        <div class="card"><h2>{total_all}</h2><p>Total Transactions</p></div>
        <div class="card" style="background:#ffebee"><h2 style="color:#c62828">{total_blocked}</h2><p>Blocked by AI</p></div>
        <div class="card" style="background:#e8f5e9"><h2 style="color:#2e7d32">{total_verified}</h2><p>Verified by AI</p></div>
        <div class="card"><h2>{avg_risk}</h2><p>Avg ML Risk Score</p></div>
    </div>
    <div class="grid">
        <div class="card"><h3>Fraud Keywords</h3><canvas id="keywordChart"></canvas></div>
        <div class="card"><h3>AI Decision Split</h3><canvas id="typeChart"></canvas></div>
    </div>
    <h3>🚨 Blocked by AI Model</h3>
    <table><tr><th>Time</th><th>User</th><th>Merchant</th><th>Amount</th><th>Reason</th><th>ML Score</th></tr>{blocked_rows}</table>
    <h3 style="margin-top:30px">✅ Verified by AI Model</h3>
    <table><tr><th>Time</th><th>User</th><th>Merchant</th><th>Amount</th><th>Card</th><th>Risk Score</th></tr>{verified_rows}</table>
    </div>
    <script>
    setTimeout(function(){{ location.reload(); }}, 10000);
    new Chart(document.getElementById('keywordChart'), {{type: 'bar',data: {{labels: {list(keywords.keys())},datasets: [{{label: 'Count',data: {list(keywords.values())},backgroundColor: ['#e74c3c','#c0392b','#e67e22','#f39c12','#9b59b6','#3498db']}}]}},options: {{responsive: true, plugins: {{legend: {{display: false}}}}}}});
    new Chart(document.getElementById('typeChart'), {{type: 'doughnut',data: {{labels: ['Verified', 'Blocked'],datasets: [{{data: [{total_verified}, {total_blocked}],backgroundColor: ['#2ecc71','#e74c3c']}}]}},options: {{responsive: true}}});
    </script>'''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')

@app.errorhandler(500)
def internal_error(e):
    return f'''{STYLE}<div class="container">
    <div class="error">Something went wrong. Please try again.</div>
    <a href="/"><button>Go Home</button></a></div>''', 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
