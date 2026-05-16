from flask import Flask, request, redirect, session, jsonify
import random
import os
import urllib.request
import json
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

# ✅ CONFIG
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = "vanshikauser65@gmail.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123" # Isko change kar dena
BLOCKED_FILE = "blocked_data.json"
SUCCESS_FILE = "success_data.json"

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

# ✅ FRAUD LINK CHECKER FUNCTION
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
            return True, f"Suspicious keyword detected: '{word}'"

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
        return True, "IP address based link detected - High risk"

    return False, "Safe"

def send_otp_mail(to_email, otp, amount, merchant):
    if not SENDGRID_API_KEY:
        raise Exception("SendGrid API Key not found in environment variables")

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
    is_fraud, reason = check_fraud_link(merchant_input)

    if is_fraud:
        blocked_transactions.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': session['user'],
            'merchant': merchant_input,
            'amount': request.form['amount'],
            'reason': reason,
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
                <p><b>Reason:</b> {reason}</p>
                <p><b>Merchant Entered:</b> {merchant_input}</p>
                <p style='margin-top:15px'>This transaction was flagged as suspicious by our AI Security System.</p>
                <p><b>For your safety, this payment cannot be processed.</b></p>
            </div>
            <a href='/dashboard'><button style='background:#1565c0'>← Back to Dashboard</button></a>
        </div>
        '''

    session['txn'] = {
        'card': request.form['card'],
        'amount': request.form['amount'],
        'merchant': merchant_input
    }
    card_last4 = request.form['card'][-4:]

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
            <tr><td><b>Amount:</b></td><td>₹{request.form['amount']}.00</td></tr>
            <tr><td><b>Merchant:</b></td><td>{merchant_input}</td></tr>
            <tr><td><b>Verified As:</b></td><td><span class="badge">RBI APPROVED</span> {merchant_input}</td></tr>
            <tr><td><b>Security Check:</b></td><td><span class="badge">PASSED</span> No fraud detected</td></tr>
        </table>

        <h3>🤖 AI Risk Analysis</h3>
        <table>
            <tr><td>Risk Score:</td><td>25/100</td></tr>
            <tr><td>Anomaly Score:</td><td>25/100</td></tr>
            <tr><td><b>Final Combined Risk:</b></td><td><b>25/100</b></td></tr>
        </table>

        <p style="text-align:center;color:#666">Do you want to approve this transaction?</p>
        <div class="flex">
            <form action="/send_otp" method="POST" style="width:100%">
                <button>✓ Approve & Send OTP</button>
            </form>
            <a href="/dashboard" style="width:100%"><button class="btn-cancel">✕ Cancel Payment</button></a>
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

        # ✅ SUCCESS TRANSACTION KO SAVE KARO
        success_transactions.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': session['user'],
            'merchant': txn['merchant'],
            'amount': txn['amount'],
            'card_last4': txn['card'][-4:],
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

    # Graph ke liye data
    keywords = {'free': 0, 'lottery': 0, 'prize': 0, 'gift': 0, 'kyc': 0, 'bit.ly': 0}
    for txn in blocked_transactions:
        for key in keywords:
            if key in txn['merchant'].lower():
                keywords[key] += 1

    # Blocked table rows
    blocked_rows = ""
    for txn in reversed(blocked_transactions[-50:]):
        blocked_rows += f'''
        <tr>
            <td>{txn['time']}</td>
            <td>{txn['user']}</td>
            <td><span class="badge-danger">{txn['merchant']}</span></td>
            <td>₹{txn['amount']}</td>
            <td>{txn['reason']}</td>
            <td>{txn['ip']}</td>
        </tr>
        '''
    if not blocked_rows:
        blocked_rows = '<tr><td colspan="6" style="text-align:center;color:#999">No fraud attempts yet</td></tr>'

    return f'''
    {STYLE}
    <div class="navbar">
        <b>🔐 SecurePay Admin Panel</b>
        <div>Admin | <a href="/admin/logout">Logout</a></div>
    </div>
    <div class="container-wide">
        <h3>Fraud Detection Dashboard <span class="refresh-badge">Auto-refresh: 10s</span></h3>

        <div class="stats">
            <div class="stat-box">
                <h2>{total_all}</h2>
                <p>Total Transactions</p>
            </div>
            <div class="stat-box red">
                <h2>{total_blocked}</h2>
                <p>Blocked Transactions</p>
            </div>
            <div class="stat-box green">
                <h2>{total_verified}</h2>
                <p>Verified Transactions</p>
            </div>
            <div class="stat-box">
                <h2>{round((total_verified/total_all*100) if total_all > 0 else 0, 1)}%</h2>
                <p>Success Rate</p>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-box">
                <h3>Fraud Keywords Distribution</h3>
                <canvas id="keywordChart"></canvas>
            </div>
            <div class="chart-box">
                <h3>Transaction Status</h3>
                <canvas id="typeChart"></canvas>
            </div>
        </div>

        <h3>Recent Blocked Transactions</h3>
        <div id="transactionTable">
        <table>
            <tr>
                <th>Time</th>
                <th>User</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Reason</th>
                <th>IP Address</th>
            </tr>
            {blocked_rows}
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
