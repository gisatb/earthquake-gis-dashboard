import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import leafmap.foliumap as leafmap

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
df = df.dropna(subset=["mag"])

# -------------------
# Sidebar filters
st.sidebar.header("🔎 Filters")
min_mag = st.sidebar.slider("Minimum Magnitude", 0.0, 10.0, 4.0, 0.1)
start_date = st.sidebar.date_input("Start Date", df["time"].min().date() if not df.empty else datetime.today())
end_date = st.sidebar.date_input("End Date", df["time"].max().date() if not df.empty else datetime.today())

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
# Leafmap interactive map
st.subheader("🗺️ Earthquake Map")
m = leafmap.Map(center=[20, 0], zoom=2)

def get_marker_color(mag):
    if mag >= 6:
        return "red"
    elif mag >= 4:
        return "orange"
    else:
        return "green"

for _, row in filtered_df.iterrows():
    popup = f"<b>Place:</b> {row['place']}<br>" \
            f"<b>Magnitude:</b> {row['mag']}<br>" \
            f"<b>Time (UTC):</b> {row['time']}<br>" \
            f"<b>Depth:</b> {row['depth']} km<br>" \
            f"<a href='{row['url']}' target='_blank'>USGS Link</a>"
    m.add_marker(
        location=[row["lat"], row["lon"]],
        popup=popup,
        icon_color=get_marker_color(row["mag"])
    )

# Add heatmap
if not filtered_df.empty:
    heat_data = [[row['lat'], row['lon'], row['mag']] for idx, row in filtered_df.iterrows()]
    m.add_heatmap(heat_data, radius=15, blur=25)

m.to_streamlit(height=500)

# -------------------
# Data Table
st.subheader("📊 Earthquake Data Table")
st.dataframe(filtered_df[["time", "place", "mag", "depth", "lon", "lat"]].sort_values(by="time", ascending=False))

# -------------------
# Download CSV
st.subheader("💾 Download Filtered Data")
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download CSV",
    data=csv,
    file_name="filtered_earthquakes.csv",
    mime="text/csv"
)

# -------------------
# Plotly Charts
st.subheader("📊 Earthquake Charts")
if not filtered_df.empty:
    # Time series
    df_time = filtered_df.groupby(filtered_df["time"].dt.date).size().reset_index(name="Count")
    fig1 = px.line(df_time, x="time", y="Count", title="Earthquakes Over Time")
    st.plotly_chart(fig1, use_container_width=True)

    # Magnitude histogram
    fig2 = px.histogram(filtered_df, x="mag", nbins=20, title="Magnitude Distribution")
    st.plotly_chart(fig2, use_container_width=True)

    # Depth histogram
    fig3 = px.histogram(filtered_df, x="depth", nbins=30, title="Depth Distribution (km)")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No data available for the selected filters.")
