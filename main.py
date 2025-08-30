import streamlit as st
import pandas as pd
import joblib  # for loading saved model and scaler

# Load your trained model and scaler
# Make sure you have saved them earlier using joblib
# Example:
# joblib.dump(model, "ridge_model.pkl")
# joblib.dump(scaler, "scaler.pkl")
model = joblib.load("ridge_model.pkl")
scaler = joblib.load("scaler.pkl")

st.title("California Housing Price Predictor 🏡")

# User inputs
MedInc = st.number_input("Median Income", min_value=0.0)
HouseAge = st.number_input("House Age", min_value=0.0)
AveRooms = st.number_input("Average Rooms", min_value=0.0)
AveBedrms = st.number_input("Average Bedrooms", min_value=0.0)
Population = st.number_input("Population", min_value=0.0)
AveOccup = st.number_input("Average Occupancy", min_value=0.0)
Latitude = st.number_input("Latitude", min_value=0.0)
Longitude = st.number_input("Longitude", min_value=0.0)

# Prepare input
input_data = [[MedInc, HouseAge, AveRooms, AveBedrms, Population, AveOccup, Latitude, Longitude]]
input_scaled = scaler.transform(input_data)

# Prediction button
if st.button("Predict"):
    prediction = model.predict(input_scaled)
    st.success(f"Predicted Median House Value: ${prediction[0]*100000:.2f}")
