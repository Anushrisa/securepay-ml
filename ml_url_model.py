import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import tldextract
import os

URL_MODEL_FILE = 'url_classifier.pkl'

def extract_url_features(url):
    ext = tldextract.extract(url)
    features = [
        len(url),
        len(ext.domain),
        url.count('.'),
        url.count('-'),
        1 if 'https' in url else 0,
        1 if '.gov.in' in url else 0,
        1 if 'sbi' in url else 0,
        1 if 'irctc' in url else 0,
        1 if any(word in url for word in ['free', 'offer', 'win', 'lucky', 'loot']) else 0
    ]
    return features

def train_url_model():
    if not os.path.exists('merchant_dataset.csv'):
        default_data = {
            'url': ['irctc.co.in', 'onlinesbi.sbi', 'uidai.gov.in', 'amazon.in', 'irctc-fake-offer.com', 'sbi-customer-care.net', 'free-aadhaar-update.in'],
            'label': [1, 1, 1, 1, 0, 0, 0]
        }
        pd.DataFrame(default_data).to_csv('merchant_dataset.csv', index=False)

    df = pd.read_csv('merchant_dataset.csv')
    X = [extract_url_features(url) for url in df['url']]
    y = df['label']
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, URL_MODEL_FILE)
    print("URL Model trained!")

def predict_url_safe(user_url):
    if not os.path.exists(URL_MODEL_FILE):
        return None
    try:
        model = joblib.load(URL_MODEL_FILE)
        features = [extract_url_features(user_url)]
        prob = model.predict_proba(features)[0][1]
        return prob * 100
    except:
        return None

if __name__ == "__main__":
    train_url_model()