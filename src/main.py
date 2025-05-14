import streamlit as st
import pandas as pd
import numpy as np
import json

from utils import mean_location, distance_from_ref, get_pois

from geographiclib.geodesic import Geodesic
import osmnx as ox
import folium
from folium import plugins
from streamlit_folium import st_folium
from streamlit_folium import folium_static

from tqdm import tqdm

from streamlit_js_eval import streamlit_js_eval

from classes import Meetpoint


st.set_page_config(layout="wide")

page_width = streamlit_js_eval(js_expressions='window.innerWidth', key='WIDTH')



with st.sidebar:
    st.title("Meetpoint")

    col1, col2 = st.columns(2)

    with col1:
        # number of origin points
        number = st.number_input(
            "Number of points", value=0, placeholder="Type the number of participants...", step= 1, min_value=0)
        st.write("The current number is ", number)
    
    with col2:
        selector = st.selectbox('Type of input', ['City', 'Coordinates'])
        
        if selector == 'City':
            orig_point_text = 'City'
        elif selector == 'Coordinates':
            orig_point_text = 'Latitude, Longitude'
        
if number>0:
    st.subheader('Origin points')

# data of each origin point
orig_point = []
orig_point_name = []

col1, col2 = st.columns(2)

with col1:
    for i in range(number):
        orig_point_name.append(st.text_input(f"origin_{i+1} - name", value=None, placeholder="Name"))
    
with col2:
    for i in range(number):
        orig_point.append(st.text_input(f"origin_{i+1} - {orig_point_text}", value=None, placeholder=orig_point_text))
    

if all(orig_point) and number>0:
    
    # list of categories
    
    st.subheader('Meeting point setup')
    
    json_file = {
    "amenity": ["bar", "restaurant", "arts centre", "bus station", "casino", "car rental", "cinema", "convention centre", "events centre","gym", "hotel", "juice bar", "kiosk", "library", "park", "planetarium", "sauna", "shop", "spa", "nightclub", "pub"],
    "sport": ["climbing", "soccer", "billiards", "darts", "athletics", "basketball",
                     "beachvolleyball", "billiards", "bmx", "bowls", "boxing", "canoe", "climbing_adventure", "crossfit",
                     "cycling", "dance", "darts", "fitness", "golf", "hiking", "karting", "kitesurfing", "laser_tag",
                     "miniature_golf", "multi", "paddle_tennis", "padel", "paintball", "parachuting", "parkour",
                     "pelota", "pickleball", "pilates", "racquet", "roller_skating", "running", "scuba_diving",
                     "shooting", "skateboard", "squash", "surfing", "swimming", "table_tennis", "table_soccer",
                     "tennis", "trampoline", "ultimate", "volleyball", "water_polo", "water_ski", "windsurfing", "yoga"],
    "leisure": ["sports_centre", "sports_hall", "stadium","swimming_pool", "recreation_ground","golf_course", "fitness_centre"]}
    category_data = json_file
    
    chosen_category = st.selectbox("Select the place's category",list(category_data.keys()))
    
    for k, v in category_data.items():
        if chosen_category == k:
            list_tags = v
        
    chosen_tag = st.selectbox('Choose your tag', list_tags)
    
    # Define tags to search
    tags = {chosen_category: chosen_tag}
    
    # select distance
    #distance = st.number_input(label='Distance (m)', min_value=0, value='min', step=1)
    distance = st.slider(label='Distance (m)', min_value=100, max_value=50000, value=1000, step=100)

    # transform points into coordinates
    if selector == 'Coordinates':
        Latitude = [float(lat.split(',')[0]) for lat in orig_point]
        Longitude = [float(lon.split(',')[1]) for lon in orig_point]
    elif selector == 'City':
        Latitude = []
        Longitude = []
        for point in orig_point:
            Latitude.append(ox.geocode_to_gdf(point).centroid.get_coordinates()['y'].values[0])
            Longitude.append(ox.geocode_to_gdf(point).centroid.get_coordinates()['x'].values[0])
            
    coordinates = {}  # origin points and meetpoint
        
    for i in range(number):
        coordinates[orig_point_name[i]] = {"Latitude": Latitude[i], "Longitude": Longitude[i], "colour": "#4CBB17"}
    
    # create meetpoint clas to make the calculations
    MP = Meetpoint(orig_points=coordinates, distance=distance, tags=tags)
        
    calculate = st.button("Calculate", on_click=MP.calculate())
    
    if calculate:

        # meetpoint
        #mp1 = meetpoint([(l[0], l[1]) for l in list(zip(Latitude, Longitude))])
        #coordinates['meetpoint1'] = {"Latitude": mp1[0], "Longitude": mp1[1], "colour":"#ff0033"}
        
        MP.calculate()
        
        if MP.pois is None:
            # pois is None when not found
            st.warning(f'{chosen_tag} not found closer than {distance} from meetpoint!')
        else:
            if MP.tries > 1:
                st.text(f'{MP.tries} km added to the radius of searching to find a {MP.tags}')
            
            # Coloured map with points of interest
            st.subheader('Map with points of interest')
            
            col1, col2 = st.columns([0.7,0.3])
            
            with col1:
   
                m = folium.Map(location=[coordinates['meetpoint']['Latitude'], coordinates['meetpoint']['Longitude']], zoom_start=10)
            
                folium.Circle(location=[coordinates['meetpoint']['Latitude'], coordinates['meetpoint']['Longitude']],
                            radius=distance, opacity=0.6, fill=True).add_to(m)
                
                for i, p in tqdm(MP.pois.iterrows()):
                    folium.Marker(location=[float(p['Latitude']),float(p['Longitude'])], 
                                tooltip=folium.Tooltip(p['name'], permanent=True)).add_to(m)
                
                    for k, v in coordinates.items():
                        if 'meet' not in k:
                            color='green'
                            icon_='bookmark'
                        else:
                            color='purple'
                            icon_='flag'
                            
                        folium.Marker(location=[float(v['Latitude']), float(v['Longitude'])],
                                    tooltip=folium.Tooltip(k, permanent=True), 
                                    icon=folium.Icon(icon=icon_, color=color)).add_to(m)
                
                map_a = folium_static(m, width=int(page_width*0.8), height=800)
            
            with col2:
                st.table(MP.fairness.rename(columns={'name': chosen_tag.upper()}).set_index(chosen_tag.upper()).sort_values(by='Inquity'))
        
        with st.expander("Details"):
        
            col1, col2 = st.columns(2)
            
            # table showing data
            df = pd.DataFrame(coordinates).transpose()
            
            with col1:
                st.table(df[['Latitude','Longitude']])
                st.table(MP.distances.rename(columns={'name':chosen_tag.upper()}).set_index(chosen_tag.upper()))
            
            with col2:
                # map for coordinates points
                map1 = st.map(df, latitude='Latitude', longitude='Longitude', size=20, color='colour')
            
                print('Meetpoint spherical:')
                for k,v in coordinates.items():
                    distance_from_ref(k, (v['Latitude'], v['Longitude']), (coordinates['meetpoint']['Latitude'], coordinates['meetpoint']['Longitude']))
