from flask import Flask, request, redirect, session, jsonify
import random
import os
import urllib.request
import json
import re
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

# ✅ CONFIG
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = "vanshikauser65@gmail.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
BLOCKED_FILE = "blocked_data.json"
SUCCESS_FILE = "success_data.json"
MODEL_FILE = "fraud_model.pkl"

# ✅ ML MODEL LOAD YA TRAIN KARO
def get_ml_model():
    if os.path.exists(MODEL_FILE):
        with open(MODEL_FILE, 'rb') as f:
            return pickle.load(f)

    # Agar model nahi hai to dummy data se train kar do
    print("Training new ML model...")
    # Normal transactions: amount, hour, user_avg_spend, txn_count_today
    normal_data = np.array([
        [500, 14, 600, 2], [1200, 18, 1000, 1], [300, 12, 400, 3],
        [2000, 16, 1800, 1], [150, 10, 200, 5], [800, 20, 900, 2],
        [50, 11, 100, 4], [5000, 15, 4500, 1], [250, 13, 300, 3],
        [1000, 19, 1100, 2]
    ])
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(normal_data)

    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model, f)
    return model

ml_model = get_ml_model()

# ✅ FILE SE DATA LOAD KARO
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

# ✅ FILE ME DATA SAVE KARO
def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

blocked_transactions = load_data(BLOCKED_FILE)
success_transactions = load_data(SUCCESS_FILE)

# ✅ ML RISK SCORE CALCULATOR
def calculate_ml_risk(amount, merchant, user_email):
    try:
        hour = datetime.now().hour

        # User ka average spend nikaalo
        user_txns = [t for t in success_transactions if t['user'] == user_email]
        user_avg = np.mean([float(t['amount']) for t in user_txns]) if user_txns else 1000
        txn_count_today = len([t for t in user_txns if t['time'].startswith(datetime.now().strftime('%Y-%m-%d'))])

        # Features: [amount, hour, user_avg, txn_count_today]
        features = np.array([[float(amount), hour, user_avg, txn_count_today]])

        # Isolation Forest: -1 = anomaly/fraud, 1 = normal
        prediction = ml_model.predict(features)
        anomaly_score = ml_model.decision_function(features)[0]

        # Score ko 0-100 me convert karo
        # decision_function: negative = anomaly, positive = normal
        risk_score = int(max(0, min(100, 50 - (anomaly_score * 100))))

        # Agar 3 AM me 5000+ ka txn hai to risk badha do
        if hour >= 0 and hour <= 5 and float(amount) > 3000:
            risk_score = min(100, risk_score + 30)

        # Agar user_avg se 5x zyada hai to risk badha do
        if float(amount) > user_avg * 5:
            risk_score = min(100, risk_score + 25)

        return risk_score, "ML Anomaly" if prediction[0] == -1 else "Normal Pattern"

    except Exception as e:
        print(f"ML Error: {e}")
        return 30, "ML Error - Default"

STYLE = """
<style>
body{font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:0}
.navbar{background:#1565c0;color:white;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.navbar a{color:white;text-decoration:none;background:#c62828;padding:6px 12px;border-radius:4px;font-size:14px}
.container{max-width:500px;margin:30px auto;background:white;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
.container-wide{max-width:1100px;margin:30px auto;background:white;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
h3{color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px;margin-top:0}
label{display:block;margin:12px 0 4px 0;font-weight:600;color:#333}
input{width:100%;padding:10px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
button{width:100%;background:#43a047;color:white;padding:12px;border:none;border-radius:4px;font-size:16px;cursor:pointer;margin-top:15px}
button:hover{background:#2e7d32}
.btn-cancel{background:#d32f2f}
.btn-cancel:hover{background:#b71c1c}
table{width:100%;border-collapse:collapse;margin:15px 0}
td,th{padding:8px;border-bottom:1px solid #eee;text-align:left;font-size:14px}
th{background:#f5f5f5;font-weight:600}
.badge{background:#43a047;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-danger{background:#c62828;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-warning{background:#ff9800;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
.flex{display:flex;gap:10px}
.block-alert{background:#ffcdd2;border:2px solid #c62828;padding:20px;border-radius:8px;text-align:center}
.block-alert h2{color:#b71c1c;margin:0 0 10px 0}
.stats{display:flex;gap:15px;margin:20px 0;flex-wrap:wrap}
.stat-box{background:#e3f2fd;padding:15px;border-radius:8px;flex:1;text-align:center;min-width:150px}
.stat-box h2{margin:0;color:#1565c0}
.stat-box p{margin:5px 0 0 0;color:#666}
.stat-box.green{background:#e8f5e9}
.stat-box.green h2{color:#2e7d32}
.stat-box.red{background:#ffebee}
.stat-box.red h2{color:#c62828}
.chart-container{display:flex;gap:20px;margin:20px 0;flex-wrap:wrap}
.chart-box{flex:1;min-width:300px;background:#fafafa;padding:15px;border-radius:8px}
.refresh-badge{background:#ff9800;color:white;padding:5px 10px;border-radius:4px;font-size:12px;margin-left:10px}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

# ✅ FRAUD LINK CHECKER FUNCTION - Rule Based
def check_fraud_link(text):
    if not text:
        return False, "Empty merchant"

    text_lower = text.lower()
    suspicious_words = [
        'free', 'lottery', 'prize', 'winner', 'kyc', 'verify', 'urgent',
        'suspended', 'blocked', 'gift', 'reward', 'bonus', 'claim',
        'bit.ly', 'tinyurl', 'cutt.ly', 'rb.gy', 't.co'
    ]
    for word in suspicious_words:
        if word in text_lower:
            return True, f"Suspicious keyword: '{word}'"

    trusted_domains = [
        'amazon.in', 'amazon.com', 'flipkart.com', 'myntra.com', 'ajio.com',
        'paytm.com', 'phonepe.com', 'googlepay.in',
        'swiggy.com', 'zomato.com', 'irctc.co.in', 'makemytrip.com'
    ]

    if text_lower.startswith('http://') or text_lower.startswith('https://'):
        is_trusted = any(domain in text_lower for domain in trusted_domains)
        if not is_trusted:
            return True, "Untrusted website link detected"

    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text_lower):
        return True, "IP address based link - High risk"

    return False, "Safe"

def send_otp_mail(to_email, otp, amount, merchant):
    if not SENDGRID_API_KEY:
        raise Exception("SendGrid API Key not found")
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL},
        "subject": f"SecurePay OTP: {otp}",
        "content": [{"type": "text/html", "value": f"""
        <div style='font-family:Arial;padding:20px'>
        <h2 style='color:#1976d2'>SecurePay OTP</h2>
        <h1 style='font-size:32px;letter-spacing:5px;color:#007bff'>{otp}</h1>
        <p><b>Amount:</b> ₹{amount}</p>
        <p><b>Merchant:</b> {merchant}</p>
        <p style='color:gray'>Valid for 5 minutes. Do not share.</p>
        </div>
        """}]
    }
    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send")
    req.add_header('Authorization', f'Bearer {SENDGRID_API_KEY}')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req, json.dumps(data).encode('utf-8'))

# ==================== USER ROUTES ====================
@app.route('/')
def home():
    if 'user' in session: return redirect('/dashboard')
    if 'admin' in session: return redirect('/admin/dashboard')
    return f'''
    {STYLE}
    <div class="navbar"><b>🏦 SecurePay</b> <a href="/admin">Admin Login</a></div>
    <div class="container">
        <h3>User Login</h3>
        <form action="/login" method="POST">
        <label>Email</label>
        <input name="email" value="vanshikauser65@gmail.com" type="email" required>
        <label>Password</label>
        <input name="password" value="user123" type="password" required>
        <button>Login</button>
        </form>
    </div>
    '''

@app.route('/login', methods=['POST'])
def login():
    if request.form['email'] == "vanshikauser65@gmail.com" and request.form['password'] == "user123":
        session['user'] = "vanshikauser65@gmail.com"
        return redirect('/dashboard')
    return f'{STYLE}<div class="container"><div class="error">Wrong Login</div><a href="/">Try Again</a></div>'

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return f'''
    {STYLE}
    <div class="navbar">
        <b>🏦 SecurePay</b>
        <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div>
    </div>
    <div class="container">
        <h3>New Transaction</h3>
        <form action="/check" method="POST">
        <label>Card Number</label>
        <input name="card" value="1234 5678 9012 3456" placeholder="1234 5678 9012 3456" required>
        <label>Card PIN</label>
        <input name="pin" type="password" placeholder="****" maxlength="4" required>
        <label>Amount (₹)</label>
        <input name="amount" type="number" placeholder="Enter Amount" required>
        <label>Merchant Website/URL</label>
        <input name="merchant" placeholder="amazon.in or https://example.com" required>
        <button>Verify & Proceed</button>
        </form>
    </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/check', methods=['POST'])
def check():
    if 'user' not in session: return redirect('/')

    merchant_input = request.form['merchant']
    amount = request.form['amount']

    # 1. RULE BASED CHECK
    is_fraud_rule, reason_rule = check_fraud_link(merchant_input)

    # 2. ML BASED RISK SCORE
    ml_risk_score, ml_reason = calculate_ml_risk(amount, merchant_input, session['user'])

    # 3. COMBINED DECISION
    # Agar rule se fraud hai YA ML risk > 70 hai to block
    if is_fraud_rule or ml_risk_score > 70:
        final_reason = reason_rule if is_fraud_rule else f"ML Risk Score High: {ml_risk_score}/100 - {ml_reason}"

        blocked_transactions.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': session['user'],
            'merchant': merchant_input,
            'amount': amount,
            'reason': final_reason,
            'ml_score': ml_risk_score,
            'ip': request.remote_addr
        })
        save_data(BLOCKED_FILE, blocked_transactions)

        return f'''
        {STYLE}
        <div class="navbar">
            <b>🏦 SecurePay</b>
            <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div>
        </div>
        <div class="container">
            <div class="block-alert">
                <h2>🚨 Transaction Blocked!</h2>
                <p><b>Reason:</b> {final_reason}</p>
                <p><b>ML Risk Score:</b> {ml_risk_score}/100</p>
                <p><b>Merchant:</b> {merchant_input}</p>
                <p style='margin-top:15px'>Flagged by AI Security System.</p>
            </div>
            <a href='/dashboard'><button style='background:#1565c0'>← Back to Dashboard</button></a>
        </div>
        '''

    # Agar sab safe hai to proceed
    session['txn'] = {
        'card': request.form['card'],
        'amount': amount,
        'merchant': merchant_input,
        'risk_score': ml_risk_score
    }
    card_last4 = request.form['card'][-4:]

    risk_badge = '<span class="badge">LOW</span>' if ml_risk_score < 40 else '<span class="badge-warning">MEDIUM</span>'

    return f'''
    {STYLE}
    <div class="navbar">
        <b>🏦 SecurePay</b>
        <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div>
    </div>
    <div class="container">
        <h3>Transaction Details</h3>
        <table>
            <tr><td><b>Card Number:</b></td><td>**** **** **** {card_last4}</td></tr>
            <tr><td><b>Amount:</b></td><td>₹{amount}.00</td></tr>
            <tr><td><b>Merchant:</b></td><td>{merchant_input}</td></tr>
            <tr><td><b>Rule Check:</b></td><td><span class="badge">PASSED</span> No fraud keywords</td></tr>
        </table>

        <h3>🤖 AI Risk Analysis</h3>
        <table>
            <tr><td>ML Risk Score:</td><td><b>{ml_risk_score}/100</b> {risk_badge}</td></tr>
            <tr><td>Pattern Analysis:</td><td>{ml_reason}</td></tr>
            <tr><td>Time Check:</td><td>{datetime.now().strftime('%H:%M')} - Normal</td></tr>
        </table>

        <p style="text-align:center;color:#666">Do you want to approve this transaction?</p>
        <div class="flex">
            <form action="/send_otp" method="POST" style="width:100%">
                <button>✓ Approve & Send OTP</button>
            </form>
            <a href="/dashboard" style="width:100%"><button class="btn-cancel">✕ Cancel Payment</button></a>
        </div>
    </div>
    '''

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'user' not in session: return redirect('/')
    txn = session.get('txn')
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp

    try:
        send_otp_mail("vanshikauser65@gmail.com", otp, txn['amount'], txn['merchant'])
        return f'''
        {STYLE}
        <div class="navbar">
            <b>🏦 SecurePay</b>
            <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div>
        </div>
        <div class="container">
            <h3>OTP Verification</h3>
            <p>OTP sent to vanshikauser65@gmail.com</p>
            <form action="/verify" method="POST">
            <label>Enter 6-digit OTP</label>
            <input name="otp" placeholder="123456" maxlength="6" required>
            <button>Verify & Pay</button>
            </form>
        </div>
        '''
    except Exception as e:
        return f'{STYLE}<div class="container"><div class="error">Mail Error: {e}</div><a href="/dashboard">Back</a></div>'

@app.route('/verify', methods=['POST'])
def verify():
    if request.form['otp'] == session.get('otp'):
        txn = session.pop('txn')
        session.pop('otp')

        success_transactions.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': session['user'],
            'merchant': txn['merchant'],
            'amount': txn['amount'],
            'card_last4': txn['card'][-4:],
            'risk_score': txn.get('risk_score', 0),
            'ip': request.remote_addr
        })
        save_data(SUCCESS_FILE, success_transactions)

        return f'''
        {STYLE}
        <div class="navbar">
            <b>🏦 SecurePay</b>
            <div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div>
        </div>
        <div class="container">
            <div class="success">
                <h2>✅ Payment Successful!</h2>
                <p><b>₹{txn['amount']}</b> paid to <b>{txn['merchant']}</b></p>
                <p>Card: **** **** **** {txn['card'][-4:]}</p>
                <p>Risk Score: {txn.get('risk_score', 0)}/100 - Verified by AI</p>
            </div>
            <a href='/dashboard'><button>New Transaction</button></a>
        </div>
        '''
    return f'{STYLE}<div class="container"><div class="error">Wrong OTP</div><a href="/dashboard">Back</a></div>'

# ==================== ADMIN ROUTES ====================
@app.route('/admin')
def admin_login_page():
    if 'admin' in session: return redirect('/admin/dashboard')
    return f'''
    {STYLE}
    <div class="navbar"><b>🔐 SecurePay Admin</b> <a href="/">User Login</a></div>
    <div class="container">
        <h3>Admin Login</h3>
        <form action="/admin/login" method="POST">
        <label>Username</label>
        <input name="username" placeholder="admin" required>
        <label>Password</label>
        <input name="password" type="password" placeholder="Enter password" required>
        <button>Login as Admin</button>
        </form>
    </div>
    '''

@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
        session['admin'] = ADMIN_USERNAME
        return redirect('/admin/dashboard')
    return f'{STYLE}<div class="container"><div class="error">Wrong Admin Credentials</div><a href="/admin">Try Again</a></div>'

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session: return redirect('/admin')

    global blocked_transactions, success_transactions
    blocked_transactions = load_data(BLOCKED_FILE)
    success_transactions = load_data(SUCCESS_FILE)

    total_blocked = len(blocked_transactions)
    total_verified = len(success_transactions)
    total_all = total_blocked + total_verified
    avg_risk = round(np.mean([t.get('risk_score', 0) for t in success_transactions]), 1) if success_transactions else 0

    keywords = {'free': 0, 'lottery': 0, 'prize': 0, 'gift': 0, 'kyc': 0, 'bit.ly': 0}
    for txn in blocked_transactions:
        for key in keywords:
            if key in txn['merchant'].lower():
                keywords[key] += 1

    blocked_rows = ""
    for txn in reversed(blocked_transactions[-50:]):
        blocked_rows += f'''
        <tr>
            <td>{txn['time']}</td>
            <td>{txn['user']}</td>
            <td><span class="badge-danger">{txn['merchant']}</span></td>
            <td>₹{txn['amount']}</td>
            <td>{txn['reason']}</td>
            <td>ML: {txn.get('ml_score', 'N/A')}</td>
        </tr>
        '''
    if not blocked_rows:
        blocked_rows = '<tr><td colspan="6" style="text-align:center;color:#999">No fraud attempts yet</td></tr>'

    verified_rows = ""
    for txn in reversed(success_transactions[-50:]):
        verified_rows += f'''
        <tr>
            <td>{txn['time']}</td>
            <td>{txn['user']}</td>
            <td><span class="badge">{txn['merchant']}</span></td>
            <td>₹{txn['amount']}</td>
            <td>**** {txn['card_last4']}</td>
            <td>Risk: {txn.get('risk_score', 0)}/100</td>
        </tr>
        '''
    if not verified_rows:
        verified_rows = '<tr><td colspan="6" style="text-align:center;color:#999">No verified transactions yet</td></tr>'

    return f'''
    {STYLE}
    <div class="navbar">
        <b>🔐 SecurePay Admin Panel</b>
        <div>Admin | <a href="/admin/logout">Logout</a></div>
    </div>
    <div class="container-wide">
        <h3>AI Fraud Detection Dashboard <span class="refresh-badge">Auto-refresh: 10s</span></h3>

        <div class="stats">
            <div class="stat-box">
                <h2>{total_all}</h2>
                <p>Total Transactions</p>
            </div>
            <div class="stat-box red">
                <h2>{total_blocked}</h2>
                <p>Blocked by AI</p>
            </div>
            <div class="stat-box green">
                <h2>{total_verified}</h2>
                <p>Verified by AI</p>
            </div>
            <div class="stat-box">
                <h2>{avg_risk}</h2>
                <p>Avg ML Risk Score</p>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-box">
                <h3>Fraud Keywords Distribution</h3>
                <canvas id="keywordChart"></canvas>
            </div>
            <div class="chart-box">
                <h3>AI Decision Split</h3>
                <canvas id="typeChart"></canvas>
            </div>
        </div>

        <h3>🚨 Blocked by AI Model</h3>
        <div id="blockedTable">
        <table>
            <tr>
                <th>Time</th>
                <th>User</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Reason</th>
                <th>ML Score</th>
            </tr>
            {blocked_rows}
        </table>
        </div>

        <h3 style="margin-top:30px">✅ Verified by AI Model</h3>
        <div id="verifiedTable">
        <table>
            <tr>
                <th>Time</th>
                <th>User</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Card</th>
                <th>Risk Score</th>
            </tr>
            {verified_rows}
        </table>
        </div>
    </div>

    <script>
    setTimeout(function(){{ location.reload(); }}, 10000);

    new Chart(document.getElementById('keywordChart'), {{
        type: 'bar',
        data: {{
            labels: {list(keywords.keys())},
            datasets: [{{
                label: 'Count',
                data: {list(keywords.values())},
                backgroundColor: ['#e74c3c','#c0392b','#e67e22','#f39c12','#9b59b6','#3498db']
            }}]
        }},
        options: {{responsive: true, plugins: {{legend: {{display: false}}}}}}
    }});

    new Chart(document.getElementById('typeChart'), {{
        type: 'doughnut',
        data: {{
            labels: ['Verified', 'Blocked'],
            datasets: [{{
                data: [{total_verified}, {total_blocked}],
                backgroundColor: ['#2ecc71','#e74c3c']
            }}]
        }},
        options: {{responsive: true}}
    }});
    </script>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
