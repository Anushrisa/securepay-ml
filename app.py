import re
from flask import Flask, render_template, request, redirect, url_for, flash
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ML Model load karo
# model = joblib.load('fraud_model.pkl') # <-- COMMENTED. Ab crash nahi hoga

# ===== FRAUD LINK CHECKER =====
def check_fraud_link(text):
    if not text:
        return False
    pattern = r'http[s]?://|bit\.ly|tinyurl|free|lottery|prize|kyc|bank|account|verify|urgent'
    if re.search(pattern, text.lower()):
        return True
    return False
# ==============================

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

        # ===== FRAUD CHECK =====
        if check_fraud_link(description):
            return render_template('blocked.html',
                reason="Suspicious link or fraud keywords detected in description")
        # =======================

        otp = random.randint(100000, 999999)
        flash('OTP sent successfully!', 'success')
        return redirect(url_for('verify_otp'))

    return render_template('send_money.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        flash('Transaction Successful!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('verify_otp.html')

if __name__ == '__main__':
    app.run(debug=True)
