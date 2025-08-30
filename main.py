import streamlit as st
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

# Load model and scaler (after training)
# model = Ridge(...)  # trained Ridge model
# scaler = StandardScaler()  # fitted scaler

st.title("California Housing Price Predictor")

MedInc = st.number_input("Median Income", min_value=0.0)
HouseAge = st.number_input("House Age", min_value=0.0)
AveRooms = st.number_input("Average Rooms", min_value=0.0)
AveBedrms = st.number_input("Average Bedrooms", min_value=0.0)
Population = st.number_input("Population", min_value=0.0)
AveOccup = st.number_input("Average Occupancy", min_value=0.0)
Latitude = st.number_input("Latitude", min_value=0.0)
Longitude = st.number_input("Longitude", min_value=0.0)

input_data = [[MedInc, HouseAge, AveRooms, AveBedrms, Population, AveOccup, Latitude, Longitude]]
input_scaled = scaler.transform(input_data)
prediction = model.predict(input_scaled)

st.write(f"Predicted Median House Value: ${prediction[0]*100000:.2f}")
