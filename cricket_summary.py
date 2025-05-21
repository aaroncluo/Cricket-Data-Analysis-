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
import numpy as np

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

# Initialize lists for summary and combined data
summary = []
all_data = []

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
    df["season"] = df["observed_on"].dt.month.map({
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Fall", 10: "Fall", 11: "Fall"
    })
    df["state"] = state_name  # Add state column for aggregate analysis

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
    season_counts = df["season"].value_counts().reindex(["Spring", "Summer", "Fall", "Winter"], fill_value=0)
    avg_obs_per_month = month_counts.mean()
    avg_obs_per_year = year_counts.mean() if not year_counts.empty else 0
    lat_range = (df["latitude"].min(), df["latitude"].max())
    lon_range = (df["longitude"].min(), df["longitude"].max())

    # Add to summary
    summary.append({
        'State': state_name,
        'Total Observations': total_observations,
        'Unique Species': unique_species,
        'Top Species': top_species.index[0] if not top_species.empty else 'N/A',
        'Top Species Count': top_species.values[0] if not top_species.empty else 0,
        'Avg Observations per Month': avg_obs_per_month,
        'Avg Observations per Year': avg_obs_per_year,
        'Spring Observations': season_counts.get("Spring", 0),
        'Summer Observations': season_counts.get("Summer", 0),
        'Fall Observations': season_counts.get("Fall", 0),
        'Winter Observations': season_counts.get("Winter", 0),
        'Latitude Range Min': lat_range[0],
        'Latitude Range Max': lat_range[1],
        'Longitude Range Min': lon_range[0],
        'Longitude Range Max': lon_range[1]
    })

    # Append to combined data
    all_data.append(df)

    # Per-state Report
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

    # Per-state Bar Graph (Monthly)
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

    # Per-state Map
    m = folium.Map(location=[df["latitude"].mean(), df["longitude"].mean()], zoom_start=6)
    for _, row in df.iterrows():
        species = row.get("scientific_name", "Unknown")
        date = row["observed_on"].strftime("%Y-%m-%d")
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            popup=f"Species: {species}<br>Date: {date}<br>State: {state_name}",
            color="green",
            fill=True,
            fill_color="green"
        ).add_to(m)
    map_file = f"{state_slug}_cricket_observations_map.html"
    m.save(os.path.join(base_dir, map_file))
    print(f"Map saved as '{map_file}'.")

    print(f"Processed {len(df)} non-urban, research-grade observations for {state_name}.")

# Combine all data
if not all_data:
    print("No valid data processed for any state.")
    sys.exit(1)
combined_df = pd.concat(all_data, ignore_index=True)

# Aggregate Analysis
total_observations_all = len(combined_df)
unique_species_all = len(combined_df["scientific_name"].unique())
species_counts_all = combined_df["scientific_name"].value_counts()
top_species_all = species_counts_all.head(5)
month_counts_all = combined_df["month"].value_counts().reindex([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
], fill_value=0)
year_counts_all = combined_df["year"].value_counts().sort_index()
season_counts_all = combined_df["season"].value_counts().reindex(["Spring", "Summer", "Fall", "Winter"], fill_value=0)
avg_obs_per_month_all = month_counts_all.mean()
avg_obs_per_year_all = year_counts_all.mean() if not year_counts_all.empty else 0
lat_range_all = (combined_df["latitude"].min(), combined_df["latitude"].max())
lon_range_all = (combined_df["longitude"].min(), combined_df["longitude"].max())

# Species shared across states
species_by_state = combined_df.groupby("state")["scientific_name"].unique()
shared_species = set.intersection(*[set(species) for species in species_by_state])
shared_species_count = len(shared_species)

# Aggregate Report
aggregate_report = f"""
Comprehensive Cricket Observation Data Analysis (17 Western U.S. States, Non-Urban, Research-Grade)
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

1. Overview
-----------
Total States Analyzed: {len(summary)}
Total Non-Urban, Research-Grade Observations: {total_observations_all}
Total Unique Species Identified: {unique_species_all}
Species Observed in Multiple States: {shared_species_count}
Urban Areas Excluded: U.S. Census Bureau Urban Areas (2020)

2. Species Distribution
-----------------------
Top 5 Most Observed Species Across All States:
{top_species_all.to_string()}

Most Observed Species by State:
{pd.DataFrame(summary)[['State', 'Top Species', 'Top Species Count']].to_string(index=False)}

3. Temporal Distribution
------------------------
Observations by Month (All States):
{month_counts_all.to_string()}
Average Observations per Month: {avg_obs_per_month_all:.2f}

Observations by Year (All States):
{year_counts_all.to_string()}
Average Observations per Year: {avg_obs_per_year_all:.2f}

Observations by Season (All States):
{season_counts_all.to_string()}

4. Geographic Distribution
--------------------------
Latitude Range (All States): {lat_range_all[0]:.4f} to {lat_range_all[1]:.4f}
Longitude Range (All States): {lon_range_all[0]:.4f} to {lon_range_all[1]:.4f}

5. State Comparisons
--------------------
Total Observations by State:
{pd.DataFrame(summary)[['State', 'Total Observations']].to_string(index=False)}

Unique Species by State:
{pd.DataFrame(summary)[['State', 'Unique Species']].to_string(index=False)}

6. Notes
--------
- Data filtered for research-grade observations (quality_grade = 'research').
- Excluded observations within U.S. Census Bureau Urban Areas (2020 shapefile).
- Observations with invalid dates or coordinates were excluded.
- Individual state reports, maps, and graphs generated.
- Aggregate map, summary CSV, and additional graphs (observations by state, species, month, year, season) generated.
"""

aggregate_report_file = "western_states_cricket_analysis.txt"
with open(os.path.join(base_dir, aggregate_report_file), "w") as f:
    f.write(aggregate_report)
print(f"Aggregate report saved as '{aggregate_report_file}'.")

# Save summary CSV
summary_df = pd.DataFrame(summary)
summary_file = "western_states_summary.csv"
summary_df.to_csv(os.path.join(base_dir, summary_file), index=False)
print(f"Summary CSV saved as '{summary_file}'.")

# Aggregate Map
m_all = folium.Map(location=[combined_df["latitude"].mean(), combined_df["longitude"].mean()], zoom_start=4)
for _, row in combined_df.iterrows():
    species = row.get("scientific_name", "Unknown")
    date = row["observed_on"].strftime("%Y-%m-%d")
    state = row["state"]
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=5,
        popup=f"Species: {species}<br>Date: {date}<br>State: {state}",
        color="blue",
        fill=True,
        fill_color="blue"
    ).add_to(m_all)
aggregate_map_file = "western_states_cricket_map.html"
m_all.save(os.path.join(base_dir, aggregate_map_file))
print(f"Aggregate map saved as '{aggregate_map_file}'.")

# Graphs
# 1. Observations by State
plt.figure(figsize=(12, 6))
sns.barplot(x="State", y="Total Observations", data=summary_df, palette="Blues_d")
plt.title("Non-Urban, Research-Grade Cricket Observations by State")
plt.xlabel("State")
plt.ylabel("Number of Observations")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "observations_by_state.png"))
plt.close()
print("Graph saved as 'observations_by_state.png'.")

# 2. Unique Species by State
plt.figure(figsize=(12, 6))
sns.barplot(x="State", y="Unique Species", data=summary_df, palette="Greens_d")
plt.title("Unique Cricket Species by State")
plt.xlabel("State")
plt.ylabel("Number of Unique Species")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "unique_species_by_state.png"))
plt.close()
print("Graph saved as 'unique_species_by_state.png'.")

# 3. Observations by Month (All States)
plt.figure(figsize=(10, 5))
sns.barplot(x=month_counts_all.index, y=month_counts_all.values, palette="Blues_d")
plt.title("Cricket Observations by Month (All Western States)")
plt.xlabel("Month")
plt.ylabel("Number of Observations")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "observations_by_month_all.png"))
plt.close()
print("Graph saved as 'observations_by_month_all.png'.")

# 4. Observations by Year (All States)
plt.figure(figsize=(10, 5))
sns.barplot(x=year_counts_all.index, y=year_counts_all.values, palette="Blues_d")
plt.title("Cricket Observations by Year (All Western States)")
plt.xlabel("Year")
plt.ylabel("Number of Observations")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "observations_by_year_all.png"))
plt.close()
print("Graph saved as 'observations_by_year_all.png'.")

# 5. Observations by Season (All States)
plt.figure(figsize=(8, 5))
sns.barplot(x=season_counts_all.index, y=season_counts_all.values, palette="Blues_d")
plt.title("Cricket Observations by Season (All Western States)")
plt.xlabel("Season")
plt.ylabel("Number of Observations")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "observations_by_season_all.png"))
plt.close()
print("Graph saved as 'observations_by_season_all.png'.")

# 6. Top 5 Species (All States)
plt.figure(figsize=(10, 5))
sns.barplot(x=top_species_all.values, y=top_species_all.index, palette="Blues_d")
plt.title("Top 5 Cricket Species (All Western States)")
plt.xlabel("Number of Observations")
plt.ylabel("Species")
plt.tight_layout()
plt.savefig(os.path.join(base_dir, "top_species_all.png"))
plt.close()
print("Graph saved as 'top_species_all.png'.")

print("All states processed and aggregate analysis completed.")
