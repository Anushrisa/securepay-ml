from flask import Flask, request, render_template, redirect, session
import smtplib
from email.mime.text import MIMEText
import random
import os

app = Flask(__name__)
app.secret_key = "vanshika123"

@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return '''
    <h2>Login</h2>
    <form action="/login" method="POST">
    Email: <input name="email" value="vanshikauser65@gmail.com"><br><br>
    Password: <input name="password" value="user123"><br><br>
    <button>Login</button>
    </form>
    '''

@app.route('/login', methods=['POST'])
def login():
    if request.form['email'] == "vanshikauser65@gmail.com" and request.form['password'] == "user123":
        session['user'] = "vanshikauser65@gmail.com"
        return redirect('/dashboard')
    return "Wrong Login"

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return '''
    <h2>Welcome vanshikauser65@gmail.com</h2>
    <form action="/pay" method="POST">
    Amount: <input name="amount" value="5000"><br><br>
    <button>Pay Now</button>
    </form>
    '''

@app.route('/pay', methods=['POST'])
def pay():
    if 'user' not in session: return redirect('/')
    amount = request.form['amount']
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['amount'] = amount
    
    try:
        msg = MIMEText(f"Your OTP is: {otp}")
        msg['Subject'] = f"OTP: {otp}"
        msg['From'] = "Vanshikauser65@gmail.com"
        msg['To'] = "vanshikauser65@gmail.com"
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login("Vanshikauser65@gmail.com", "gahcyhlytluunzlz")
        s.send_message(msg)
        s.quit()
        return f'''
        <h3>OTP sent to mail</h3>
        <p>Amount: ₹{amount}</p>
        <form action="/verify" method="POST">
        <input name="otp" placeholder="Enter OTP"><br>
        <button>Verify</button>
        </form>
        '''
    except Exception as e:
        return f"Mail Error: {e}"

@app.route('/verify', methods=['POST'])
def verify():
    if request.form['otp'] == session.get('otp'):
        amt = session.get('amount')
        return f"<h1>✅ Payment Success! ₹{amt} Paid</h1><a href='/dashboard'>Back</a>"
    return "Wrong OTP"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
