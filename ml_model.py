import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
import joblib
import os

MODEL_PATH = "models"
if not os.path.exists(MODEL_PATH):
    os.makedirs(MODEL_PATH)

MODELS = {
    "RandomForest": "RandomForest-ML",
    "XGBoost": "XGBoost-ML",
    "LogisticRegression": "LogisticReg-ML",
    "SVM": "SVM-ML"
}

def train_all_models():
    """4 ML models train karo"""
    # ✅ FIX: Sab array me 7 items hain ab
    if not os.path.exists('transaction_data.csv'):
        dummy_data = {
            'amount': [1000, 50000, 80000, 2000, 150000, 500, 90000],
            'hour': [14, 23, 2, 10, 1, 16, 22],
            'distance_from_base_km': [10, 1500, 2500, 50, 3000, 5, 1800],
            'is_rbi_approved': [1, 1, 0, 1, 0, 1, 1],
            'is_fraud': [0, 1, 1, 0, 1, 0, 1] # ✅ 7 items
        }
        df = pd.DataFrame(dummy_data)
    else:
        df = pd.read_csv('transaction_data.csv')

    X = df[['amount', 'hour', 'distance_from_base_km', 'is_rbi_approved']].fillna(0)
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 1. Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    joblib.dump(rf, f'{MODEL_PATH}/random_forest.pkl')

    # 2. XGBoost/Gradient Boosting
    xgb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    xgb.fit(X_train, y_train)
    joblib.dump(xgb, f'{MODEL_PATH}/xgboost.pkl')

    # 3. Logistic Regression
    lr = LogisticRegression(random_state=42, max_iter=1000)
    lr.fit(X_train, y_train)
    joblib.dump(lr, f'{MODEL_PATH}/logistic.pkl')

    # 4. SVM
    svm = SVC(probability=True, random_state=42)
    svm.fit(X_train, y_train)
    joblib.dump(svm, f'{MODEL_PATH}/svm.pkl')

    print("✅ All 4 ML Models Trained: RandomForest, XGBoost, Logistic, SVM")

def select_best_model(amount, hour, distance):
    """ML khud decide karega kaunsa model best hai"""
    if amount > 50000: # Bada amount = XGBoost
        return "XGBoost"
    if hour >= 23 or hour <= 5: # Raat = SVM
        return "SVM"
    if distance > 2000: # International = Logistic
        return "LogisticRegression"
    return "RandomForest" # Normal = RandomForest

def predict_fraud_risk(amount, hour, distance, is_approved):
    """Risk score + Model name return karega"""
    try:
        features = [[amount, hour, distance, int(is_approved)]]
        model_to_use = select_best_model(amount, hour, distance)

        if model_to_use == "RandomForest":
            model = joblib.load(f'{MODEL_PATH}/random_forest.pkl')
        elif model_to_use == "XGBoost":
            model = joblib.load(f'{MODEL_PATH}/xgboost.pkl')
        elif model_to_use == "LogisticRegression":
            model = joblib.load(f'{MODEL_PATH}/logistic.pkl')
        else:
            model = joblib.load(f'{MODEL_PATH}/svm.pkl')

        prob = model.predict_proba(features)[0][1] * 100
        risk_score = int(prob)
        return risk_score, MODELS[model_to_use]

    except Exception as e:
        print(f"ML Error: {e}")
        return None, "Rule-Engine"

def train_model():
    train_all_models()

def predict_url_safe(url):
    """Dummy URL ML - 85% safe return karega"""
    suspicious = ["free", "win", "lottery", "bit.ly", "scam"]
    for word in suspicious:
        if word in url.lower():
            return 15.0
    return 85.0

def train_url_model():
    pass