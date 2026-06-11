from flask import Flask, request, redirect, session
import random
import os
import urllib.request
import json
import re
from datetime import datetime
import numpy as np

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('SMTP_EMAIL', "vanshikauser65@gmail.com")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

ml_model = None

def get_ml_model():
    global ml_model
    if ml_model is not None:
        return ml_model

    try:
        from sklearn.ensemble import IsolationForest
        # Chhota model: 30 trees, max_samples=20. Memory ~40MB
        print("Training ML model...")
        normal_data = np.array([
            [500, 14, 600, 2], [1200, 18, 1000, 1], [300, 12, 400, 3],
            [2000, 16, 1800, 1], [150, 10, 200, 5], [800, 20, 900, 2],
            [50, 11, 100, 4], [5000, 15, 4500, 1]
        ])
        ml_model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=30,
            max_samples=20,
            n_jobs=1
        )
        ml_model.fit(normal_data)
        return ml_model
    except Exception as e:
        print(f"ML Load Failed: {e}")
        return None

def init_session():
    if 'transactions' not in session:
        session['transactions'] = []

def check_fraud_link(text):
    if not text:
        return False, "Empty merchant", 0
    text_lower = text.lower()
    score = 0
    reasons = []

    suspicious_words = ['free','lottery','prize','winner','kyc','verify','urgent','gift','reward','bonus','claim','bit.ly','tinyurl']
    for word in suspicious_words:
        if word in text_lower:
            score += 40
            reasons.append(f"Keyword: {word}")

    trusted_domains = ['amazon.in','amazon.com','flipkart.com','myntra.com','paytm.com','phonepe.com','googlepay.in','swiggy.com','zomato.com']
    if text_lower.startswith('http') and not any(d in text_lower for d in trusted_domains):
        score += 30
        reasons.append("Untrusted domain")

    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text_lower):
        score += 50
        reasons.append("IP address link")

    return score >= 50, " | ".join(reasons) if reasons else "Safe", min(score, 100)

def calculate_ml_risk(amount, merchant, user_email):
    model = get_ml_model()
    if model is None:
        return 30, "ML Disabled"

    try:
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
        return 30, "ML Error"

def send_otp_mail(to_email, otp, amount, merchant):
    if not SENDGRID_API_KEY:
        raise Exception("SENDGRID_API_KEY not set")

    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": "SecurePay"},
        "subject": f"SecurePay OTP: {otp}",
        "content": [{"type": "text/html", "value": f"<h2>OTP: {otp}</h2><p>Amount: ₹{amount}<br>Merchant: {merchant}</p>"}]
    }

    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send")
    req.add_header('Authorization', f'Bearer {SENDGRID_API_KEY}')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, json.dumps(data).encode('utf-8'))

STYLE = """<style>
body{font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:0}
.navbar{background:#1565c0;color:white;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.container{max-width:1100px;margin:30px auto;background:white;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
h3{color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px}
label{display:block;margin:12px 0 4px 0;font-weight:600}
input{width:100%;padding:10px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
button{width:100%;background:#43a047;color:white;padding:12px;border:none;border-radius:4px;font-size:16px;cursor:pointer;margin-top:15px}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.badge{background:#43a047;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-danger{background:#c62828;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-warning{background:#ff9800;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
table{width:100%;border-collapse:collapse;margin:15px 0}
td,th{padding:10px;border-bottom:1px solid #eee;text-align:left}
th{background:#f5f5f5}
.block-alert{background:#ffcdd2;border:2px solid #c62828;padding:20px;border-radius:8px;text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:20px 0}
.card{background:#f5f5f5;padding:15px;border-radius:8px;text-align:center}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

@app.route('/')
def home():
    init_session()
    if 'user' in session:
        return redirect('/dashboard')
    return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b></div>
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
    <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div></div>
    <div class="container"><h3>New Transaction</h3>
    <form action="/check" method="POST">
    <label>Card Number</label><input name="card" value="1234 5678 9012 3456" required>
    <label>Amount (₹)</label><input name="amount" type="number" min="1" required>
    <label>Merchant</label><input name="merchant" placeholder="amazon.in" required>
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

    is_fraud_rule, reason_rule, rule_score = check_fraud_link(merchant_input)
    ml_risk_score, ml_reason = calculate_ml_risk(amount, merchant_input, session['user'])

    final_score = max(rule_score, ml_risk_score)

    if is_fraud_rule or final_score > 70:
        final_reason = reason_rule if is_fraud_rule else f"ML Risk High: {ml_risk_score}/100 - {ml_reason}"
        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'user': session['user'],'merchant': merchant_input,'amount': amount,'status': 'Blocked','reason': final_reason,'score': final_score})
        session['transactions'] = txns
        return f'''{STYLE}<div class="container"><div class="block-alert"><h2>🚨 Transaction Blocked!</h2>
        <p><b>Reason:</b> {final_reason}</p><p><b>Risk Score:</b> {final_score}/100</p></div>
        <a href='/dashboard'><button>Back</button></a></div>'''

    session['txn'] = {'card': request.form['card'],'amount': amount,'merchant': merchant_input,'score': final_score}
    risk_badge = '<span class="badge">LOW</span>' if final_score < 40 else '<span class="badge-warning">MEDIUM</span>'

    return f'''{STYLE}<div class="container"><h3>Transaction Details</h3>
    <table><tr><td>Amount:</td><td>₹{amount}</td></tr>
    <tr><td>Merchant:</td><td>{merchant_input}</td></tr>
    <tr><td>Risk Score:</td><td><b>{final_score}/100</b> {risk_badge}</td></tr>
    <tr><td>Rule Check:</td><td>{reason_rule}</td></tr>
    <tr><td>ML Analysis:</td><td>{ml_reason}</td></tr></table>
    <form action="/send_otp" method="POST"><button>Approve & Send OTP</button></form></div>'''

@app.route('/send_otp', methods=['POST'])
def send_otp():
    init_session()
    if 'user' not in session:
        return redirect('/')
    txn = session.get('txn')
    if not txn:
        return f'{STYLE}<div class="container"><div class="error">Session expired</div><a href="/dashboard">Back</a></div>'

    otp = str(random.randint(100000, 999))
    session['otp'] = otp

    try:
        send_otp_mail("vanshikauser65@gmail.com", otp, txn['amount'], txn['merchant'])
        return f'''{STYLE}<div class="container"><h3>OTP Sent</h3>
        <p>Check vanshikauser65@gmail.com</p>
        <form action="/verify" method="POST">
        <input name="otp" maxlength="6" required>
        <button>Verify</button></form></div>'''
    except Exception as e:
        return f'''{STYLE}<div class="container">
        <div class="error">OTP Send Failed: {str(e)}</div>
        <a href="/dashboard"><button>Back</button></a></div>'''

@app.route('/verify', methods=['POST'])
def verify():
    init_session()
    if request.form['otp'] == session.get('otp'):
        txn = session.pop('txn', None)
        session.pop('otp', None)
        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'user': session['user'],'merchant': txn['merchant'],'amount': txn['amount'],'status': 'Success','score': txn.get('score', 0)})
        session['transactions'] = txns
        return f'''{STYLE}<div class="container"><div class="success"><h2>✅ Payment Successful!</h2>
        <p>₹{txn['amount']} paid to {txn['merchant']}</p>
        <p>Risk Score: {txn.get('score', 0)}/100</p></div>
        <a href='/dashboard'><button>New Transaction</button></a></div>'''
    return f'{STYLE}<div class="container"><div class="error">Wrong OTP</div><a href="/dashboard">Back</a></div>'

@app.route('/admin')
def admin():
    init_session()
    txns = session.get('transactions', [])
    blocked = [t for t in txns if t['status'] == 'Blocked']
    success = [t for t in txns if t['status'] == 'Success']

    rows = ""
    for txn in reversed(txns[-50:]):
        color = 'badge-danger' if txn['status'] == 'Blocked' else 'badge'
        rows += f"<tr><td>{txn['time']}</td><td>{txn['merchant']}</td><td>₹{txn['amount']}</td><td><span class='{color}'>{txn['status']}</span></td><td>Score: {txn.get('score', 0)}</td></tr>"

    return f'''{STYLE}<div class="navbar"><b>🔐 Admin Panel</b><div><a href="/">Home</a></div></div>
    <div class="container">
    <h3>Dashboard</h3>
    <div class="grid">
        <div class="card"><h2>{len(txns)}</h2><p>Total</p></div>
        <div class="card" style="background:#ffebee"><h2 style="color:#c62828">{len(blocked)}</h2><p>Blocked</p></div>
        <div class="card" style="background:#e8f5e9"><h2 style="color:#2e7d32">{len(success)}</h2><p>Success</p></div>
    </div>
    <table><tr><th>Time</th><th>Merchant</th><th>Amount</th><th>Status</th><th>Score</th></tr>{rows}</table>
    </div>'''

@app.errorhandler(500)
def internal_error(e):
    return f'''{STYLE}<div class="container">
    <div class="error">Something went wrong</div>
    <a href="/"><button>Go Home</button></a></div>''', 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
