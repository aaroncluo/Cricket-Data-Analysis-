# cricket
This project analyzes iNaturalist cricket observations for U.S. states, filtering non-urban, research-grade data using the 2020 U.S. Census urban area shapefile. To start, download cricket data by state from iNaturalist as a csv (e.g., california_observations.csv) and save it to your project folder as statename_observations.csv. Get urban area data from the 2020 US Census link provided. Install dependencies with pip install pandas matplotlib seaborn folium geopandas shapely. 

The script generates a text report (<state>_cricket_data_analysis.txt), a monthly observation graph (<state>_cricket_observations_by_month.png), and an interactive HTML map (<state>_cricket_observations_map.html) viewable in a browser. 
