import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
import sys
import os
import re
from datetime import datetime
import geopandas as gpd
from shapely.geometry import Point

# Set working directory
base_dir = os.path.dirname(os.path.abspath(__file__))
print("Working directory:", base_dir)
print("Files:", os.listdir(base_dir))

# Load urban shapefile once
shapefile_path = os.path.join(base_dir, "tl_2020_us_uac20.shp")
if not os.path.exists(shapefile_path):
    print(f"Shapefile not found at {shapefile_path}")
    sys.exit(1)
try:
    urban_areas = gpd.read_file(shapefile_path).to_crs("EPSG:4326")
except Exception as e:
    print(f"Error loading shapefile: {e}")
    sys.exit(1)

# Detect all *_observations.csv files
csv_files = [f for f in os.listdir(base_dir) if f.endswith("_observations.csv")]
if not csv_files:
    print("No *_observations.csv files found.")
    sys.exit(1)

# Summary list for all states
summary = []

# Process each CSV file
for csv_file in csv_files:
    csv_path = os.path.join(base_dir, csv_file)

    # Extract state name (handle multi-word names)
    match = re.match(r"([a-z_]+)_observations\.csv", csv_file)
    if not match:
        print(f"Could not extract state name from filename: {csv_file}")
        continue
    state_slug = match.group(1)  # e.g., 'new_mexico'
    state_name = state_slug.replace('_', ' ').title()  # e.g., 'New Mexico'
    print(f"\nProcessing observations for: {state_name}")

    # Load CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV {csv_file}: {e}")
        continue

    # Required columns
    required_cols = ["observed_on", "latitude", "longitude", "quality_grade", "scientific_name"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Missing columns in {csv_file}: {missing_cols}")
        continue

    # Filter for research-grade
    df = df[df["quality_grade"] == "research"]
    if df.empty:
        print(f"No research-grade observations found for {state_name}.")
        continue

    # Geo-filter for non-urban
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf_non_urban = gdf[~gdf.geometry.within(urban_areas.unary_union)]
    df = pd.DataFrame(gdf_non_urban.drop(columns="geometry"))
    if df.empty:
        print(f"No non-urban, research-grade observations found for {state_name}.")
        continue

    # Parse dates
    df["observed_on"] = pd.to_datetime(df["observed_on"], errors="coerce")
    df = df.dropna(subset=["observed_on"])
    df["month"] = df["observed_on"].dt.month_name()
    df["year"] = df["observed_on"].dt.year

    # Analysis
    total_observations = len(df)
    species_counts = df["scientific_name"].value_counts()
    unique_species = len(species_counts)
    top_species = species_counts.head(5)
    month_counts = df["month"].value_counts().reindex([
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ], fill_value=0)
    year_counts = df["year"].value_counts().sort_index()
    avg_obs_per_month = month_counts.mean()
    avg_obs_per_year = year_counts.mean() if not year_counts.empty else 0
    lat_range = (df["latitude"].min(), df["latitude"].max())
    lon_range = (df["longitude"].min(), df["longitude"].max())

    # Add to summary
    summary.append({
        'State': state_name,
        'Total Observations': total_observations,
        'Unique Species': unique_species,
        'Top Species': top_species.index[0] if not top_species.empty else 'N/A'
    })

    # Report
    report = f"""
Cricket Observation Data Analysis ({state_name}, Non-Urban, Research-Grade)
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
============================================================

1. Overview
-----------
Total Non-Urban, Research-Grade Observations: {total_observations}
Unique Species Identified: {unique_species}
Urban Areas Excluded: U.S. Census Bureau Urban Areas (2020)

2. Species Distribution
-----------------------
Top 5 Most Observed Species:
{top_species.to_string()}

3. Temporal Distribution
------------------------
Observations by Month:
{month_counts.to_string()}
Average Observations per Month: {avg_obs_per_month:.2f}

Observations by Year:
{year_counts.to_string()}
Average Observations per Year: {avg_obs_per_year:.2f}

4. Geographic Distribution
--------------------------
Latitude Range: {lat_range[0]:.4f} to {lat_range[1]:.4f}
Longitude Range: {lon_range[0]:.4f} to {lon_range[1]:.4f}

5. Notes
--------
- Data filtered for research-grade observations (quality_grade = 'research').
- Excluded observations within U.S. Census Bureau Urban Areas (2020 shapefile).
- Observations with invalid dates or coordinates were excluded.
- Map and bar graph generated for visualization.
"""

    report_file = f"{state_slug}_cricket_data_analysis.txt"
    with open(os.path.join(base_dir, report_file), "w") as f:
        f.write(report)
    print(f"Analysis report saved as '{report_file}'.")

    # Bar Graph
    plt.figure(figsize=(10, 5))
    sns.barplot(x=month_counts.index, y=month_counts.values, palette="Blues_d", legend=False)
    plt.title(f"{state_name} Non-Urban, Research-Grade Cricket Observations by Month")
    plt.xlabel("Month")
    plt.ylabel("Number of Observations")
    plt.xticks(rotation=45)
    plt.tight_layout()
    graph_file = f"{state_slug}_cricket_observations_by_month.png"
    plt.savefig(os.path.join(base_dir, graph_file))
    plt.close()
    print(f"Graph saved as '{graph_file}'.")

    # Map
    m = folium.Map(location=[df["latitude"].mean(), df["longitude"].mean()], zoom_start=6)
    for _, row in df.iterrows():
        species = row.get("scientific_name", "Unknown")
        date = row["observed_on"].strftime("%Y-%m-%d")
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            popup=f"Species: {species}<br>Date: {date}",
            color="green",
            fill=True,
            fill_color="green"
        ).add_to(m)

    map_file = f"{state_slug}_cricket_observations_map.html"
    m.save(os.path.join(base_dir, map_file))
    print(f"Map saved as '{map_file}'.")

    print(f"Processed {len(df)} non-urban, research-grade observations for {state_name}.")
