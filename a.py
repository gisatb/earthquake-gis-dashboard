import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import folium
from folium.plugins import HeatMap, MarkerCluster
import streamlit.components.v1 as components

# -------------------
# Page configuration
st.set_page_config(page_title="Earthquake GIS Dashboard", layout="wide")
st.title("🌍 Earthquake GIS Dashboard")
st.markdown("Real-time earthquake data from **USGS (past 30 days)**")

# -------------------
# Fetch earthquake data
url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
response = requests.get(url).json()

# Extract data into DataFrame
features = response["features"]
data = []
for f in features:
    props = f["properties"]
    coords = f["geometry"]["coordinates"]
    data.append({
        "place": props["place"],
        "mag": props["mag"],
        "time": datetime.utcfromtimestamp(props["time"]/1000),
        "lon": coords[0],
        "lat": coords[1],
        "depth": coords[2],
        "url": props["url"]
    })

df = pd.DataFrame(data)
df = df.dropna(subset=["mag"])  # Remove missing magnitudes

# -------------------
# Sidebar filters
st.sidebar.header("🔎 Filters")
min_mag = st.sidebar.slider("Minimum Magnitude", 0.0, 10.0, 4.0, 0.1)
start_date = st.sidebar.date_input("Start Date", df["time"].min().date())
end_date = st.sidebar.date_input("End Date", df["time"].max().date())

# Apply filters and reset index
mask = (
    (df["mag"] >= min_mag) &
    (df["time"].dt.date >= start_date) &
    (df["time"].dt.date <= end_date)
)
filtered_df = df[mask].reset_index(drop=True)

st.sidebar.write(f"✅ Showing {len(filtered_df)} earthquakes")

# -------------------
# Statistics
st.subheader("📈 Summary Statistics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Earthquakes", len(filtered_df))
col2.metric("Max Magnitude", filtered_df["mag"].max() if not filtered_df.empty else 0.0)
col3.metric("Avg Magnitude", round(filtered_df["mag"].mean(), 2) if not filtered_df.empty else 0.0)

# -------------------
# Folium Map with MarkerCluster and HeatMap
st.subheader("🗺️ Earthquake Map")

m = folium.Map(location=[20, 0], zoom_start=2)
marker_cluster = MarkerCluster().add_to(m)

# Function to determine marker color based on magnitude
def get_marker_color(mag):
    if mag >= 6:
        return "red"
    elif mag >= 4:
        return "orange"
    else:
        return "green"

# Add markers with clickable USGS links and color-coded icons
for _, row in filtered_df.iterrows():
    popup_html = f"""
    <b>Place:</b> {row['place']}<br>
    <b>Magnitude:</b> {row['mag']}<br>
    <b>Time (UTC):</b> {row['time']}<br>
    <b>Depth:</b> {row['depth']} km<br>
    <a href="{row['url']}" target="_blank">USGS Link</a>
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=get_marker_color(row["mag"]), icon="info-sign")
    ).add_to(marker_cluster)

# Add heatmap
if not filtered_df.empty:
    heat_data = [[row['lat'], row['lon'], row['mag']] for idx, row in filtered_df.iterrows()]
    HeatMap(heat_data, radius=15, blur=25).add_to(m)

# Render map in Streamlit
components.html(m._repr_html_(), height=500)

# -------------------
# Data Table
st.subheader("📊 Earthquake Data Table")
st.dataframe(filtered_df[["time", "place", "mag", "depth", "lon", "lat"]].sort_values(by="time", ascending=False))

# -------------------
# Download filtered data as CSV
st.subheader("💾 Download Filtered Data")
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download CSV",
    data=csv,
    file_name="filtered_earthquakes.csv",
    mime="text/csv"
)

# -------------------
# Charts
st.subheader("📊 Earthquake Charts")
if not filtered_df.empty:
    # Time series of earthquakes
    df_time = filtered_df.groupby(filtered_df["time"].dt.date).size().reset_index(name="Count")
    fig1 = px.line(df_time, x="time", y="Count", title="Earthquakes Over Time")
    st.plotly_chart(fig1, use_container_width=True)

    # Histogram of magnitudes
    fig2 = px.histogram(filtered_df, x="mag", nbins=20, title="Magnitude Distribution")
    st.plotly_chart(fig2, use_container_width=True)

    # Depth distribution
    fig3 = px.histogram(filtered_df, x="depth", nbins=30, title="Depth Distribution (km)")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No data available for the selected filters.")
