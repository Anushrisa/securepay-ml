from flask import Flask, request, redirect, session
import smtplib
from email.mime.text import MIMEText
import random
import os

app = Flask(__name__)
app.secret_key = "vanshika-secure-2024"

# Common CSS for banking look
STYLE = """
<style>
body{font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:0}
.container{max-width:450px;margin:40px auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}
.header{background:#1565c0;color:white;padding:20px;text-align:center;border-radius:12px 12px 0 0;margin:-30px -30px 20px -30px}
h2{margin:0}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:6px;box-sizing:border-box}
button{width:100%;background:#1976d2;color:white;padding:14px;border:none;border-radius:6px;font-size:16px;cursor:pointer;margin-top:10px}
button:hover{background:#0d47a1}
.logout{float:right;color:white;text-decoration:none;font-size:14px}
.card{background:#e3f2fd;padding:15px;border-radius:8px;margin:15px 0;border-left:4px solid #1976d2}
.success{color:#2e7d32;background:#e8f5e9;padding:15px;border-radius:8px;text-align:center}
.error{color:#c62828;background:#ffebee;padding:12px;border-radius:6px;margin:10px 0}
</style>
"""

@app.route('/')
def home():
    if 'user' in session: return redirect('/dashboard')
    return f'''
    {STYLE}
    <div class="container">
        <div class="header"><h2>SecurePay Login</h2></div>
        <form action="/login" method="POST">
        <label>Email</label>
        <input name="email" value="vanshikauser65@gmail.com" type="email" required>
        <label>Password</label>
        <input name="password" value="user123" type="password" required>
        <button>Login to SecurePay</button>
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
    <div class="container">
        <div class="header">
            <h2>SecurePay Dashboard <a href="/logout" class="logout">Logout</a></h2>
        </div>
        <div class="card">
            <b>Welcome:</b> vanshikauser65@gmail.com<br>
            <b>Account Status:</b> ✅ Active
        </div>
        <h3>Make Payment</h3>
        <form action="/pay" method="POST">
        <label>Amount (₹)</label>
        <input name="amount" value="5000" type="number" required>
        <label>Merchant</label>
        <input name="merchant" value="Amazon India" required>
        <label>Card Last 4 Digits</label>
        <input name="card" value="1111" maxlength="4" required>
        <button>Proceed to Pay</button>
        </form>
    </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/pay', methods=['POST'])
def pay():
    if 'user' not in session: return redirect('/')
    amount = request.form['amount']
    merchant = request.form['merchant']
    card = request.form['card']
    
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['txn'] = {'amount': amount, 'merchant': merchant, 'card': card}
    
    try:
        msg = MIMEText(f"""
        <div style='font-family:Arial;padding:20px'>
        <h2 style='color:#1976d2'>SecurePay OTP</h2>
        <h1 style='font-size:32px;letter-spacing:5px;color:#007bff'>{otp}</h1>
        <p><b>Amount:</b> ₹{amount}</p>
        <p><b>Merchant:</b> {merchant}</p>
        <p style='color:gray'>Valid for 5 minutes. Do not share.</p>
        </div>
        """, 'html')
        msg['Subject'] = f"SecurePay OTP: {otp}"
        msg['From'] = "vanshikauser65@gmail.com"
        msg['To'] = "vanshikauser65@gmail.com"
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login("vanshikauser65@gmail.com", "gahcyhlytluunzlz")
        s.send_message(msg)
        s.quit()
        
        return f'''
        {STYLE}
        <div class="container">
            <div class="header"><h2>OTP Verification</h2></div>
            <div class="card">
                <b>Amount:</b> ₹{amount}<br>
                <b>Merchant:</b> {merchant}<br>
                <b>Card:</b> **** **** **** {card}
            </div>
            <p>OTP sent to vanshikauser65@gmail.com</p>
            <form action="/verify" method="POST">
            <input name="otp" placeholder="Enter 6-digit OTP" maxlength="6" required>
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
        <div class="container">
            <div class="success">
                <h2>✅ Payment Successful!</h2>
                <p><b>₹{txn['amount']}</b> paid to <b>{txn['merchant']}</b></p>
                <p>Card: **** **** **** {txn['card']}</p>
            </div>
            <a href='/dashboard'><button>New Transaction</button></a>
        </div>
        '''
    return f'{STYLE}<div class="container"><div class="error">Wrong OTP</div><a href="/dashboard">Back</a></div>'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
