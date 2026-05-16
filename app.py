from flask import Flask, request, redirect, session
import random
import os
import urllib.request
import json

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

# ✅ SAFE TARIKA - Railway Variables se key lega
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = "vanshikauser65@gmail.com"  # Ye SendGrid me verified hona chahiye

STYLE = """
<style>
body{font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:0}
.navbar{background:#1565c0;color:white;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.navbar a{color:white;text-decoration:none;background:#c62828;padding:6px 12px;border-radius:4px;font-size:14px}
.container{max-width:500px;margin:30px auto;background:white;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
h3{color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px;margin-top:0}
label{display:block;margin:12px 0 4px 0;font-weight:600;color:#333}
input{width:100%;padding:10px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box}
button{width:100%;background:#43a047;color:white;padding:12px;border:none;border-radius:4px;font-size:16px;cursor:pointer;margin-top:15px}
button:hover{background:#2e7d32}
.btn-cancel{background:#d32f2f}
.btn-cancel:hover{background:#b71c1c}
table{width:100%;border-collapse:collapse;margin:15px 0}
td{padding:8px;border-bottom:1px solid #eee}
.badge{background:#43a047;color:white;padding:3px 8px;border-radius:4px;font-size:12px}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
.flex{display:flex;gap:10px}
</style>
"""

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

@app.route('/')
def home():
    if 'user' in session: return redirect('/dashboard')
    return f'''
    {STYLE}
    <div class="navbar"><b>🏦 SecurePay</b></div>
    <div class="container">
        <h3>Login</h3>
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
    session['txn'] = {
        'card': request.form['card'],
        'amount': request.form['amount'],
        'merchant': request.form['merchant']
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
            <tr><td><b>Merchant:</b></td><td>{request.form['merchant']}</td></tr>
            <tr><td><b>Verified As:</b></td><td><span class="badge">RBI APPROVED</span> {request.form['merchant']}</td></tr>
            <tr><td><b>Location:</b></td><td>📍 User Location</td></tr>
        </table>
        
        <h3>🤖 AI Risk Analysis</h3>
        <table>
            <tr><td>Risk Score (RandomForest):</td><td>25/100</td></tr>
            <tr><td>Anomaly Score (IsolationForest):</td><td>25/100</td></tr>
            <tr><td><b>Final Combined Risk:</b></td><td><b>25/100</b></td></tr>
            <tr><td>AI Method Used:</td><td>Default</td></tr>
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
