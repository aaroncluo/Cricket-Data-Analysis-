# Cricket Data Analysis
This project analyzes iNaturalist cricket observations for U.S. states, filtering non-urban, research-grade data using the 2020 U.S. Census urban area shapefile. To start, download cricket data by state from iNaturalist as a csv (e.g., california_observations.csv) and save it to your project folder as statename_observations.csv. Get urban area data from the 2020 US Census link provided. Install dependencies with pip install pandas matplotlib seaborn folium geopandas shapely. 


The script generates a text report (<state>_cricket_data_analysis.txt), a monthly observation graph (<state>_cricket_observations_by_month.png), and an interactive HTML map (<state>_cricket_observations_map.html) viewable in a browser. 

5/3 - Created project. Added data for Utah, Wyoming, Oregon and Nevada, US 2020 Census data and script

5/20 - Added 13 more states: Washington, California, Idaho, Arizona, New Mexico, Texas, Oklahoma, Kansas, Colorodo, South Dakota, North Dakota, Nebraska, and Montana. That's the 17 western states combined with the previous ones added on 5/3. 
Modified code to be able to handle two word names for New Mexico, South Dakota, and North Dakota
Modified code to handle multiple states at once

