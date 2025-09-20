import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

# ----------------------------------------------------
# --- Monkey patch for Windows encoding issue ---
def fixed_to_html(self, outfile=None, **kwargs):
    """Export the map to an HTML string with UTF-8 decoding."""
    import os, tempfile
    if outfile is None:
        outfile = os.path.join(tempfile.gettempdir(), "leafmap.html")
    self.save(outfile, **kwargs)
    with open(outfile, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return outfile

def fixed_to_streamlit(self, width=None, height=600, responsive=True):
    import streamlit.components.v1 as components
    outfile = self.to_html()
    try:
        with open(outfile, "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, width=width, height=height, scrolling=False)
    except Exception as e:
        raise Exception(e)

# Patch the methods
leafmap.Map.to_html = fixed_to_html
leafmap.Map.to_streamlit = fixed_to_streamlit
# ------------------------------------------------

# ----------------------------------------------------

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

# Apply filters
mask = (
    (df["mag"] >= min_mag) &
    (df["time"].dt.date >= start_date) &
    (df["time"].dt.date <= end_date)
)
filtered_df = df[mask]

st.sidebar.write(f"✅ Showing {len(filtered_df)} earthquakes")

# -------------------
# Statistics
st.subheader("📈 Summary Statistics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Earthquakes", len(filtered_df))
col2.metric("Max Magnitude", filtered_df["mag"].max() if not filtered_df.empty else 0.0)
col3.metric("Avg Magnitude", round(filtered_df["mag"].mean(), 2) if not filtered_df.empty else 0.0)

# -------------------
# Map
st.subheader("🗺️ Earthquake Map")
m = leafmap.Map(center=[20, 0], zoom=2)

if not filtered_df.empty:
    # 1. Clustered markers
    m.add_points_from_xy(
        filtered_df,
        x="lon",
        y="lat",
        popup=["place", "mag", "time", "depth", "url"],
        layer_name="Earthquakes",
        radius=5,
        fill_color="red",
        clustered=True
    )

    # 2. Heatmap overlay
    m.add_heatmap(
        filtered_df,
        latitude="lat",
        longitude="lon",
        value="mag",
        name="Earthquake Heatmap",
        radius=15,
        blur=25
    )

m.to_streamlit(height=500)

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
    # 1. Time series of earthquakes
    df_time = filtered_df.groupby(filtered_df["time"].dt.date).size().reset_index(name="Count")
    fig1 = px.line(df_time, x="time", y="Count", title="Earthquakes Over Time")
    st.plotly_chart(fig1, use_container_width=True)

    # 2. Histogram of magnitudes
    fig2 = px.histogram(filtered_df, x="mag", nbins=20, title="Magnitude Distribution")
    st.plotly_chart(fig2, use_container_width=True)

    # 3. Depth distribution
    fig3 = px.histogram(filtered_df, x="depth", nbins=30, title="Depth Distribution (km)")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No data available for the selected filters.")
