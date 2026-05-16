from flask import Flask, render_template, request, redirect, url_for, flash, session
import re
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
# import pickle # Apna ML model load karne ke liye uncomment karna
# import numpy as np

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production' # Isse change kar dena

# Apna ML model load karo yahan
# model = pickle.load(open('fraud_model.pkl', 'rb'))

# ===== FRAUD LINK CHECK FUNCTION =====
def check_fraud_link(text):
    """
    Description me link ya fraud keywords check karta hai
    """
    text = text.lower()
    # URL patterns + fraud keywords
    url_pattern = re.search(r'http[s]?://|www\.|\.com|\.in|\.net|\.org|bit\.ly|tinyurl|t\.co|goo\.gl', text)
    fraud_keywords = ['free', 'lottery', 'prize', 'winner', 'kyc', 'verify', 'update',
                      'blocked', 'suspend', 'click here', 'urgent', 'account blocked']

    if url_pattern or any(word in text for word in fraud_keywords):
    return True
    return False

# ===== EMAIL FUNCTION =====
def send_otp_email(receiver_email, otp):
    """SendGrid se OTP email bhejo"""
    message = Mail(
        from_email='your_verified_sender@sendgrid.com', # SendGrid me verified email daalo
        to_emails=receiver_email,
        subject='SecurePay - OTP for Transaction',
        html_content=f'<strong>Your OTP is: {otp}</strong><br>Do not share with anyone.')
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        return True
    except Exception as e:
        print(e)
        return False

# ===== ROUTES =====
@app.route('/')
def index():
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

        # STEP 1: FRAUD LINK CHECK - Sabse pehle ye chalega
        if check_fraud_link(description):
            return render_template('blocked.html',
                reason="Suspicious link or fraud keywords detected in description")

        # STEP 2: ML MODEL CHECK - Tumhara purana code yahan aayega
        # Example:
        # features = np.array([[float(amount), len(description)]]).reshape(1, -1)
        # prediction = model.predict(features)
        #
        # if prediction[0] == 1: # 1 = Fraud
        # return render_template('fraud_detected.html')

        # STEP 3: OTP GENERATE AUR BHEJO
        import random
        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['amount'] = amount
        session['receiver'] = receiver

        if send_otp_email(receiver, otp):
            flash('OTP sent to receiver email', 'success')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to send OTP', 'danger')
            return redirect(url_for('dashboard'))

    return render_template('send_money.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and int(user_otp) == session['otp']:
            # Transaction Success
            flash('Transaction Successful!', 'success')
            # Yahan database me save karne ka code daalo
            session.pop('otp', None)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid OTP', 'danger')

    return render_template('verify_otp.html')

@app.route('/admin')
def admin():
    # Admin panel ka code
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
