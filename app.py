from flask import Flask, request, render_template, redirect, session
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os
import traceback

app = Flask(__name__)
app.secret_key = "securepay-debug-2024"

# ========== CONFIG ==========
SMTP_EMAIL = "Vanshikauser65@gmail.com"
SMTP_PASSWORD = "djdaihesjsddahzs" # Gmail App Password

DEMO_USERS = {
    'admin@securepay.com': 'admin123',
    'user@securepay.com': 'user123',
    'vanshikauser65@gmail.com': 'user123'
}

# ========== ML MODELS ==========
ml_model = None
url_model = None

try:
    X = np.array([[500,10,1,5],[5000,22,3,2],[25000,3,8,1],[1000,14,2,4]])
    y = np.array([0,0,1])
    ml_model = RandomForestClassifier(n_estimators=50, random_state=42)
    ml_model.fit(X, y)
    X_url = np.array([[1,10,0],[0,25,1],[1,8,0],[0,30,1]])
    y_url = np.array([0,1,0,1])
    url_model = RandomForestClassifier(n_estimators=20, random_state=42)
    url_model.fit(X_url, y_url)
    print("✅ Models OK")
except Exception as e:
    print(f"Model Error: {e}")

def calc_risk(amount, hour, lat, lon, merchant):
    try:
        loc_risk = 2 if abs(lat-28.61)<1 and abs(lon-77.20)<1 else 8
        features = np.array([[amount, hour, loc_risk, 3]])
        risk = int(ml_model.predict_proba(features)[0][1] * 100)

        https = 1 if str(merchant).startswith('https') else 0
        length = min(len(str(merchant)), 50)
        has_ip = 1 if any(c.isdigit() for c in str(merchant).split('.')[0]) else 0
        url_feat = np.array([[https, length, has_ip]])
        url_risk = int(url_model.predict_proba(url_feat)[0][1] * 100)
        return int((risk + url_risk) / 2)
    except Exception as e:
        print(f"Risk Calc Error: {e}")
        return 45

def send_mail_otp(to_email, otp, amount, merchant):
    try:
        print(f"Attempting mail to {to_email}")
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"SecurePay OTP: {otp}"
        html = f"<h2>SecurePay OTP</h2><h1>{otp}</h1><p>Amount: ₹{amount}</p><p>Merchant: {merchant}</p>"
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Mail sent successfully")
        return True, ""
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Auth Error: {e}")
        return False, "Gmail App Password galat hai. 2-Step Verification ON karke App Password banao."
    except Exception as e:
        print(f"❌ Mail Error: {e}")
        return False, "Mail nahi bhej paaye. Internet ya Gmail issue."

# ========== ROUTES ==========
@app.route('/')
def home():
    return redirect('/dashboard') if 'user' in session else render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    try:
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '').strip()
        print(f"Login attempt: {email}")
        if DEMO_USERS.get(email) == password:
            session['user'] = email
            session.permanent = True
            print(f"Login success: {email}")
            return redirect('/dashboard')
        print("Login failed")
        return render_template('login.html', error="Invalid credentials")
    except Exception as e:
        print(f"Login Error: {e}")
        return render_template('login.html', error="Login failed")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        print("No session, redirecting to login")
        return redirect('/')
    print(f"Dashboard loaded for: {session['user']}")
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/approve', methods=['POST'])
def approve():
    print("Approve route called")
    if 'user' not in session:
        print("No user session")
        return redirect('/')
    try:
        print(f"Form data: {request.form}")
        amount = float(request.form.get('amount', 5000))
        merchant = request.form.get('merchant', 'https://amazon.in')
        card = request.form.get('card', '4111111111111111')
        lat = float(request.form.get('lat', 28.61))
        lon = float(request.form.get('lon', 77.20))

        print(f"Parsed: amount={amount}, merchant={merchant}")
        hour = pd.Timestamp.now().hour
        final_risk = calc_risk(amount, hour, lat, lon, merchant)
        print(f"Risk calculated: {final_risk}")

        session['txn_details'] = {
            'amount': amount,
            'merchant_domain': merchant,
            'card': card[-4:],
            'risk_score': final_risk,
            'rbi_status': '✅ RBI APPROVED' if final_risk < 60 else '❌ RBI FLAGGED'
        }
        print("Rendering approve.html")
        return render_template('approve.html', txn=session['txn_details'])
    except Exception as e:
        print(f"Approve Error: {traceback.format_exc()}")
        return render_template('dashboard.html', error=f"Transaction error: {str(e)[:100]}")

@app.route('/send_otp', methods=['POST'])
def send_otp():
    print("Send OTP called")
    if 'user' not in session or 'txn_details' not in session:
        return redirect('/')
    if request.form.get('action') == 'cancel':
        session.pop('txn_details', None)
        return render_template('result.html', result="BLOCKED", final_msg="Transaction Cancelled")

    otp = str(random.randint(100000, 999999))
    txn = session['txn_details']
    success, error_msg = send_mail_otp(session['user'], otp, txn['amount'], txn['merchant_domain'])

    if success:
        session['otp'] = otp
        print("OTP sent, showing OTP page")
        return render_template('otp.html', email=session['user'], amount=txn['amount'])
    else:
        print(f"OTP send failed: {error_msg}")
        return render_template('approve.html', txn=txn, error=error_msg)

@app.route('/verify', methods=['POST'])
def verify():
    if 'user' not in session: return redirect('/')
    if 'otp' not in session or 'txn_details' not in session: return redirect('/dashboard')
    if request.form.get('otp', '').strip() == session.get('otp', ''):
        txn = session.pop('txn_details', {})
        session.pop('otp', None)
        return render_template('success.html', txn=txn)
    else:
        return render_template('otp.html', email=session['user'], amount=session['txn_details']['amount'], error="Invalid OTP")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
