from flask import Flask, render_template, request, jsonify
import pickle
import pandas as pd
import json
import gzip
import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

model_dir = os.path.join(BASE_DIR, 'model')

with gzip.open(os.path.join(model_dir, 'rent_model.pkl.gz'), 'rb') as f:
    model = pickle.load(f)

with open(os.path.join(model_dir, 'feature_metadata.json'), 'r', encoding='utf-8') as f:
    metadata = json.load(f)


@app.route("/")
def index():
    return render_template("index.html", metadata=metadata)


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    apartment = pd.DataFrame([{
        'size_m2': float(data['size_m2']),
        'room_count': int(data['room_count']),
        'floor_number': int(data['floor_number']),
        'district': data['district'],
        'building_type': data['building_type'],
        'condition': data['condition'],
        'ownership': data['ownership'],
        'furnished': data['furnished'],
        'elevator': data['elevator'],
        'has_separate_kitchen': int(data.get('has_separate_kitchen', 0)),
        'has_balcony': int(data.get('has_balcony', 0)),
        'has_terrace': int(data.get('has_terrace', 0)),
        'has_cellar': int(data.get('has_cellar', 0)),
        'has_parking': int(data.get('has_parking', 0)),
    }])

    predicted_price = model.predict(apartment)[0]
    return jsonify({"price": round(float(predicted_price))})


if __name__ == '__main__':
    app.run(debug=True)