import re
import os
import random
from flask import Flask, render_template, request, redirect, url_for, flash, session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_12345' # Session ke liye zaruri

# ML Model - Abhi comment hai
# model = joblib.load('fraud_model.pkl')

# ===== SENDGRID SETUP =====
# Railway Variables me ye 2 add karna: SENDGRID_API_KEY, SENDER_EMAIL
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'your_verified_vanshikauser65@example.com')
# ==========================

# ===== FRAUD LINK CHECKER =====
def check_fraud_link(text):
    if not text:
        return False
    pattern = r'http[s]?://|bit\.ly|tinyurl|free|lottery|prize|kyc|bank|account|verify|urgent'
    if re.search(pattern, text.lower()):
        return True
    return False
# ==============================

# ===== SEND OTP FUNCTION =====
def send_otp_email(receiver_email, otp):
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=receiver_email,
        subject='SecurePay - Your OTP Code',
        html_content=f'<h3>Your SecurePay OTP is: <strong>{otp}</strong></h3><p>This OTP is valid for 5 minutes.</p>')
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return False
# =============================

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
        receiver = request.form['receiver'] # Isme email aayega

        # ===== FRAUD CHECK =====
        if check_fraud_link(description):
            return render_template('blocked.html',
                reason="Suspicious link or fraud keywords detected in description")
        # =======================

        # OTP Generate karke session me save karo
        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['receiver'] = receiver
        session['amount'] = amount

        # SendGrid se email bhejo
        if send_otp_email(receiver, otp):
            flash('OTP sent to your email successfully!', 'success')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to send OTP. Check SendGrid setup.', 'danger')
            return redirect(url_for('send_money'))

    return render_template('send_money.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']

        # Session se OTP check karo
        if 'otp' in session and str(session['otp']) == str(user_otp):
            flash(f"Transaction of ₹{session['amount']} Successful!", 'success')
            session.clear() # OTP use hone ke baad clear karo
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html')

if __name__ == '__main__':
    app.run(debug=True)
