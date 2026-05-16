import re
from flask import Flask, render_template, request, redirect, url_for, flash
import joblib
import pandas as pd
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ML Model load karo
model = joblib.load('fraud_model.pkl')

# ===== FRAUD LINK CHECKER - NEW FUNCTION =====
def check_fraud_link(text):
    if not text:
        return False

    pattern = r'http[s]?://|bit\.ly|tinyurl|free|lottery|prize|kyc|bank|account|verify|urgent'
    if re.search(pattern, text.lower()):
        return True

    return False
# =============================================

# Email OTP Function
def send_otp_email(receiver_email, otp):
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password" # Gmail app password

    msg = MIMEText(f"Your OTP for SecurePay transaction is: {otp}")
    msg['Subject'] = 'SecurePay OTP Verification'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if request.method == 'POST':
        amount = request.form['amount']
        description = request.form['description']
        receiver = request.form['receiver']

        # ===== FRAUD CHECK - YAHI ADD KIYA HAI =====
        if check_fraud_link(description):
            return render_template('blocked.html',
                reason="Suspicious link or fraud keywords detected in description")
        # ===========================================

        # Tumhara purana OTP + ML wala code yahan aayega
        # Example:
        otp = random.randint(100000, 999999)
        if send_otp_email(receiver, str(otp)):
            flash('OTP sent successfully!', 'success')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to send OTP', 'error')

    return render_template('send_money.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        # Yahan OTP verify ka logic daalna
        flash('Transaction Successful!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('verify_otp.html')

if __name__ == '__main__':
    app.run(debug=True)
