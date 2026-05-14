from flask import Flask, request, render_template, redirect, session
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import smtplib
from email.mime.text import MIMEText
import random
import os

app = Flask(__name__)
app.secret_key = "only-vanshika-2024"

SMTP_EMAIL = "Vanshikauser65@gmail.com"
SMTP_PASSWORD = "djdaihesjsddahzs" # App Password

# SIRF TUMHARA ACCOUNT
USER_EMAIL = "vanshikauser65@gmail.com"
USER_PASSWORD = "user123"

ml_model = RandomForestClassifier()
ml_model.fit([[500,10,1,5],[5000,22,3,2]], [0,0])

@app.route('/')
def home():
    if 'user' in session: return redirect('/dashboard')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email','').lower().strip()
    password = request.form.get('password','').strip()
    if email == USER_EMAIL and password == USER_PASSWORD:
        session['user'] = email
        return redirect('/dashboard')
    return render_template('login.html', error="Only vanshikauser65@gmail.com allowed")

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template('dashboard.html')

@app.route('/approve', methods=['POST'])
def approve():
    if 'user' not in session: return redirect('/')
    try:
        amount = float(request.form['amount'])
        merchant = request.form['merchant']
        card = request.form['card']
        lat = float(request.form['lat'])
        lon = float(request.form['lon'])
        risk = int(ml_model.predict_proba([[amount, 14, 2, 3]])[0][1] * 100)

        session['txn'] = {
            'amount': amount, 'merchant': merchant, 'card': card[-4:],
            'risk': risk, 'status': '✅ APPROVED' if risk < 60 else '❌ FLAGGED'
        }
        return render_template('approve.html', txn=session['txn'])
    except Exception as e:
        return f"Error: {e}"

@app.route('/send_otp', methods=['POST'])
def send_otp():
    if 'txn' not in session: return redirect('/dashboard')
    if request.form.get('action') == 'cancel':
        return "Transaction Cancelled"

    otp = str(random.randint(100000, 999999))
    session['otp'] = otp

    try:
        msg = MIMEText(f"Your SecurePay OTP is: {otp}")
        msg['Subject'] = f"SecurePay OTP: {otp}"
        msg['From'] = SMTP_EMAIL
        msg['To'] = session['user']
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(SMTP_EMAIL, SMTP_PASSWORD)
        s.send_message(msg)
        s.quit()
        return render_template('otp.html', email=session['user'])
    except Exception as e:
        return render_template('approve.html', txn=session['txn'], error=f"Mail Failed: {e}")

@app.route('/verify', methods=['POST'])
def verify():
    if request.form.get('otp') == session.get('otp'):
        txn = session.pop('txn')
        session.pop('otp')
        return f"<h1>✅ Success! ₹{txn['amount']} Paid to {txn['merchant']}</h1><a href='/dashboard'>New Transaction</a>"
    return render_template('otp.html', email=session['user'], error="Wrong OTP")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
