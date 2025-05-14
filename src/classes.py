import numpy as np
import osmnx as ox
import pandas as pd
import math

class Meetpoint():
    def __init__(self, orig_points: dict, distance: int, tags: dict):
        """class aimed to create a searching of pois in similar distances of orig points of reference

        Args:
            orig_points (dict): dict of coordinate points in tuples
            distance (int): distance to rearch pois around of
            tags (dict): dict with the tag description to search
        """
        self.orig_points = orig_points.copy()
        self.coordinates = orig_points
        self.number = len(orig_points)
        self.distance = distance
        self.tags = tags
        self.tries_list = []
        
    def calculate(self):
        self.coordinates['meetpoint'] = self.mean_point()
        self.pois = self.get_pois()
        self.tries = max(self.tries_list)
        self.distances = self.get_distances()
        self.fairness = self.inquity()
        
    
    def get_distances(self):
        
        distances = pd.DataFrame()
        distances['name'] = self.pois['name']
        
        self.distance_columns = []  # columns of every distance metric
    
        for k, v in self.coordinates.items():
            distance_pois_orig_aux = []  # distance from each pois to each pois
            for i, row in enumerate(self.pois.iterrows()):
                distance_pois_orig_aux.append(int(ox.distance.great_circle(self.coordinates[k]['Latitude'], self.coordinates[k]['Longitude'],self.pois['Latitude'][i], self.pois['Longitude'][i])))
            distances[f'Dist-{k}(m)'] = distance_pois_orig_aux 
            self.distance_columns.append(f'Dist-{k}(m)')
            
        distances.sort_values(by='Dist-meetpoint(m)', inplace=True)
        
        return distances
    
    def mean_point(self):
        mp = self._mean_location(pd.DataFrame(self.coordinates).transpose())
        return {"Latitude": mp[0], "Longitude": mp[1], "colour":"#B200ED"}
        
    def _mean_location(self, coords_df):
        x = 0.0
        y = 0.0
        z = 0.0

        for i, coord in coords_df.iterrows():
            latitude = math.radians(coord['Latitude'])
            longitude = math.radians(coord['Longitude'])

            x += math.cos(latitude) * math.cos(longitude)
            y += math.cos(latitude) * math.sin(longitude)
            z += math.sin(latitude)

        total = len(coords_df)

        x = x / total
        y = y / total
        z = z / total

        central_longitude = math.atan2(y, x)
        central_square_root = math.sqrt(x * x + y * y)
        central_latitude = math.atan2(z, central_square_root)

        mean_location_ = {
            'latitude': math.degrees(central_latitude),
            'longitude': math.degrees(central_longitude)
            }
        
        return (mean_location_['latitude'], mean_location_['longitude'])
    
    def get_pois(self, count=0):
        center_point = (self.coordinates['meetpoint']['Latitude'], self.coordinates['meetpoint']['Longitude'])
        if count > 10:
            print(f'{self.tags} not found!')
            return None
        try:
            gdf_pois = ox.features_from_point(center_point, tags=self.tags, dist=self.distance)[['geometry','name']]
            pois = gdf_pois[gdf_pois['name'].notna()].loc[('node',)]
            coords = pois.get_coordinates(ignore_index=True)
            names = pois['name'].values
            coords['name'] = names
            
            result = coords.rename(columns={'x':'Longitude', 'y': 'Latitude'})
            
        except Exception: # KeyError or osmnx._errors.InsufficientResponseError:
            self.distance = self.distance + 1000
            result = self.get_pois(count=count+1)
            self.tries_list.append(count)
            
        return result
    
    def inquity(self):
        
        fairness = pd.DataFrame()
        fairness['name'] = self.distances['name']
        
        distances = self.distances[(c for c in self.distances.columns if ('meet' not in c) and ('name' not in c))]
        N = len(distances.columns)
        inquity = []
        
        for k in list(self.orig_points.keys()):
            fairness[f'Balance_{k}'] = ''
    
        for row in distances.iterrows():

            total = np.sum(row[1])
            
            fairness.iloc[row[0],1:] = (total-row[1].values)/total

            inquity.append(np.var(row[1]/total))
             
        fairness['Inquity'] = inquity   
        return fairness

    