from flask import Flask, request, redirect, session
import random
import os
import urllib.request
import urllib.error
import json
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('SMTP_EMAIL', "vanshikauser65@gmail.com")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

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
td,th{padding:10px;border-bottom:1px solid #eee;text-align:left}
th{background:#f5f5f5}
.badge{background:#43a047;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.badge-danger{background:#c62828;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
.flex{display:flex;gap:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:20px 0}
.card{background:#f5f5f5;padding:15px;border-radius:8px;text-align:center}
.card h2{margin:5px 0;color:#1565c0}
.block-alert{background:#ffcdd2;border:2px solid #c62828;padding:20px;border-radius:8px;text-align:center}
.block-alert h2{color:#b71c1c;margin:0 0 10px 0}
pre{background:#f5f5f5;padding:10px;border-radius:4px;overflow-x:auto}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

def init_session():
    if 'transactions' not in session:
        session['transactions'] = []

def check_fraud_link(text):
    if not text: return False, "Empty merchant"
    text_lower = text.lower()
    suspicious_words = ['free','lottery','prize','winner','kyc','verify','urgent','suspended','blocked','gift','reward','bonus','claim','bit.ly','tinyurl','cutt.ly']
    for word in suspicious_words:
        if word in text_lower: return True, f"Suspicious keyword: '{word}'"
    trusted_domains = ['amazon.in','amazon.com','flipkart.com','myntra.com','ajio.com','paytm.com','phonepe.com','google.com','googlepay.in','swiggy.com','zomato.com','irctc.co.in']
    if text_lower.startswith('http'):
        if not any(d in text_lower for d in trusted_domains): return True, "Untrusted website link"
    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text_lower):
        return True, "IP address based link detected"
    return False, "Safe"

def send_otp_mail(to_email, otp, amount, merchant):
    if not SENDGRID_API_KEY: 
        raise Exception("SENDGRID_API_KEY not found in Railway Variables")
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL},
        "subject": f"SecurePay OTP: {otp}",
        "content": [{"type": "text/html", "value": f"<div style='font-family:Arial;padding:20px'><h2>SecurePay OTP</h2><h1 style='font-size:32px'>{otp}</h1><p><b>Amount:</b> ₹{amount}</p><p><b>Merchant:</b> {merchant}</p><p style='color:gray'>Valid for 5 minutes</p></div>"}]
    }
    req = urllib.request.Request("https://api.sendgrid.com/v3/mail/send")
    req.add_header('Authorization', f'Bearer {SENDGRID_API_KEY}')
    req.add_header('Content-Type', 'application/json')
    try:
        urllib.request.urlopen(req, json.dumps(data).encode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise Exception(f"SendGrid HTTP {e.code}: {error_body}")

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
    <button>Login</button></form>
    <p style="text-align:center;margin-top:15px"><a href="/admin/login">Admin Login</a></p></div>'''

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
    <div>vanshikauser65@gmail.com | <a href="/admin/login">Admin</a> | <a href="/logout">Logout</a></div></div>
    <div class="container"><h3>New Transaction</h3>
    <form action="/check" method="POST">
    <label>Card Number</label><input name="card" value="1234 5678 9012 3456" required>
    <label>Card PIN</label><input name="pin" type="password" maxlength="4" required>
    <label>Amount (₹)</label><input name="amount" type="number" min="1" required>
    <label>Merchant Website/URL</label><input name="merchant" placeholder="amazon.in or https://example.com" required>
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
    is_fraud, reason = check_fraud_link(merchant_input)
    
    if is_fraud:
        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%H:%M:%S'),'merchant': merchant_input,'amount': request.form['amount'],'status': 'Blocked','reason': reason})
        session['transactions'] = txns
        return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b><div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div></div>
        <div class="container"><div class="block-alert"><h2>🚨 Transaction Blocked!</h2>
        <p><b>Reason:</b> {reason}</p><p><b>Merchant:</b> {merchant_input}</p></div>
        <a href='/dashboard'><button>Back to Dashboard</button></a></div>'''
    
    session['txn'] = {'card': request.form['card'],'amount': request.form['amount'],'merchant': merchant_input}
    return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b><div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div></div>
    <div class="container"><h3>Transaction Details</h3>
    <table><tr><td>Card:</td><td>**** **** {request.form['card'][-4:]}</td></tr>
    <tr><td>Amount:</td><td>₹{request.form['amount']}</td></tr>
    <tr><td>Merchant:</td><td>{merchant_input}</td></tr>
    <tr><td>Status:</td><td><span class="badge">Safe</span></td></tr></table>
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
        return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b><div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div></div>
        <div class="container"><h3>OTP Verification</h3>
        <p>OTP sent to vanshikauser65@gmail.com</p>
        <form action="/verify" method="POST">
        <label>Enter 6-digit OTP</label><input name="otp" maxlength="6" required>
        <button>Verify & Pay</button></form></div>'''
    except Exception as e:
        return f'''{STYLE}<div class="container">
        <div class="error"><b>OTP Send Failed:</b><br><pre>{str(e)}</pre></div>
        <p><b>Check:</b> SendGrid me {FROM_EMAIL} verify kiya hai kya?</p>
        <a href="/dashboard"><button>Back</button></a></div>'''

@app.route('/verify', methods=['POST'])
def verify():
    init_session()
    if request.form['otp'] == session.get('otp'):
        txn = session.pop('txn', None)
        session.pop('otp', None)
        if not txn:
            return f'{STYLE}<div class="container"><div class="error">Session expired. Start again.</div><a href="/dashboard">Back</a></div>'
        
        txns = session.get('transactions', [])
        txns.append({'time': datetime.now().strftime('%H:%M:%S'),'merchant': txn['merchant'],'amount': txn['amount'],'status': 'Success','reason': '-'})
        session['transactions'] = txns
        return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay</b><div>vanshikauser65@gmail.com | <a href="/logout">Logout</a></div></div>
        <div class="container"><div class="success"><h2>✅ Payment Successful!</h2>
        <p><b>₹{txn['amount']}</b> paid to <b>{txn['merchant']}</b></p></div>
        <a href='/dashboard'><button>New Transaction</button></a></div>'''
    return f'{STYLE}<div class="container"><div class="error">Wrong OTP</div><a href="/dashboard">Back</a></div>'

@app.route('/admin/login')
def admin_login():
    init_session()
    if 'admin' in session: 
        return redirect('/admin')
    return f'''{STYLE}<div class="navbar"><b>🏦 SecurePay Admin</b></div>
    <div class="container"><h3>Admin Login</h3>
    <form action="/admin/do_login" method="POST">
    <label>Username</label><input name="username" value="admin" required>
    <label>Password</label><input name="password" value="admin123" type="password" required>
    <button>Login</button></form>
    <p style="text-align:center;margin-top:15px"><a href="/">Back to User Login</a></p></div>'''

@app.route('/admin/do_login', methods=['POST'])
def admin_do_login():
    init_session()
    if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
        session['admin'] = ADMIN_USERNAME
        return redirect('/admin')
    return f'{STYLE}<div class="container"><div class="error">Wrong Credentials</div><a href="/admin/login">Try Again</a></div>'

@app.route('/admin')
def admin_dashboard():
    init_session()
    if 'admin' not in session: 
        return redirect('/admin/login')
    
    txns = session.get('transactions', [])
    total = len(txns)
    success = len([t for t in txns if t['status'] == 'Success'])
    blocked = len([t for t in txns if t['status'] == 'Blocked'])
    total_amount = sum([int(t['amount']) for t in txns if t['status'] == 'Success'])
    
    last_10 = txns[-10:]
    labels = [t['time'] for t in last_10]
    amounts = [int(t['amount']) if t['status']=='Success' else 0 for t in last_10]
    
    rows = ''.join([f"<tr><td>{t['time']}</td><td>{t['merchant']}</td><td>₹{t['amount']}</td><td><span class='badge {'badge-danger' if t['status']=='Blocked' else ''}'>{t['status']}</span></td><td>{t['reason']}</td></tr>" for t in reversed(txns[-20:])])
    
    if not rows:
        rows = "<tr><td colspan='5'>No transactions yet</td></tr>"
    
    return f'''{STYLE}
    <div class="navbar"><b>🏦 SecurePay Admin Panel</b><div>Admin | <a href="/admin/logout">Logout</a></div></div>
    <div class="container">
    <h3>Real-Time Dashboard</h3>
    <div class="grid">
        <div class="card"><h2>{total}</h2><p>Total Transactions</p></div>
        <div class="card"><h2>{success}</h2><p>Success</p></div>
        <div class="card"><h2>{blocked}</h2><p>Blocked</p></div>
        <div class="card"><h2>₹{total_amount}</h2><p>Total Amount</p></div>
    </div>
    <h3>Transaction Trend - Last 10</h3>
    <canvas id="txnChart" height="80"></canvas>
    <h3>Recent Transactions</h3>
    <table><tr><th>Time</th><th>Merchant</th><th>Amount</th><th>Status</th><th>Reason</th></tr>{rows}</table>
    </div>
    <script>
    const ctx = document.getElementById('txnChart');
    new Chart(ctx, {{
        type: 'line',
        data: {{labels: {json.dumps(labels)},datasets: [{{label: 'Amount ₹',data: {json.dumps(amounts)},borderColor: '#1565c0',backgroundColor: 'rgba(21,101,192,0.2)',tension: 0.3,fill: true}}]}},
        options: {{responsive: true, scales: {{y: {{beginAtZero: true}}}}}}
    }});
    </script>'''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.errorhandler(500)
def internal_error(e):
    return f'''{STYLE}<div class="container">
    <div class="error"><b>500 Internal Error:</b><br><pre>{str(e)}</pre></div>
    <a href="/"><button>Go Home</button></a></div>''', 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
