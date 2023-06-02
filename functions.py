# Import dependencies
import os
import pandas as pd
import numpy as np
import csv
import json
from time import sleep

# Credentials and custom functions
from auth import *
from countries_list import countries

# API dependencies
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Set up the spotipy functions to work with any client ID and secret to use the API

ccm = SpotifyClientCredentials(client_id = cid, client_secret = secret)
sp = spotipy.Spotify(client_credentials_manager = ccm)

# Function to get the top playlist for each country
# Get the country names from the data dictionary file "countries.py"

def get_top_playlists(country_codes):
    country_names = []

    for i,t in enumerate(countries):
        for c in country_codes:
            if c in t:
                country_names.insert(list(country_codes).index(c), sorted(t)[1])
    pl_names = []
    pl_ids = []

    for c in country_codes:
        response = sp.featured_playlists(country = c)

        while response:
            playlists = response['playlists']
            for i, item in enumerate(playlists['items']):
                pl_names.append(item['name'])
                pl_ids.append(item['id'])

            if playlists['next']:
                response = sp.next(playlists)
            else:
                response = None

    keys = ['country_name','pl_name','pl_id']
    top_pl = {}

    for i in range(len(country_codes)):
        sub_dict = {keys[0]: country_names[i], keys[1]: pl_names[i], keys[2]: pl_ids[i]}
        top_pl[country_codes[i]] = sub_dict

    return top_pl

# Function to extract tracks from a playlist thats longer than 100 songs
def get_playlist_tracks(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

# Pulls the playlist tracks metadata 
def get_spotify_dataframes(playlist_name, playlist_id):
        
    # Make lists for the relevant data
    artist_name, track_name, popularity, track_id = [], [], [], []

    track_results = sp.playlist_tracks(playlist_id, limit=10)
    
    for t in track_results['items']:
        try: 
            artist = t['track']['artists'][0]['name']
            artist_name.append(artist)
            track_name.append(t['track']['name'])
            track_id.append(t['track']['id'])
            popularity.append(t['track']['popularity'])
        except:
            artist_name.append("")
            track_name.append("")
            track_id.append("")
            popularity.append("")
            
    # Make a dataframe with the basic song information and popularity
    tracks_df = pd.DataFrame({'artist': artist_name, 
                              'track_name':track_name,
                                    'track_id':track_id,
                                    'popularity':popularity})
    
    # Set up empty dictionary to hold the audio features
    audio_features = {}

    # Put all the ids in a list for the spotipy object to look up the audio features
    for idd in tracks_df['track_id'].tolist():
        audio_features[idd] = sp.audio_features(idd)[0]

    feature_list = ['key', 'tempo', 'time_signature', 'valence', 'liveness', 'energy', 'danceability', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']

    # For each audio feature, add it to the tracks dataframe
    for feature in feature_list:
        tracks_df[feature] = tracks_df['track_id'].apply(lambda idd: audio_features[idd][feature])

    # Define column to normalize
    x = tracks_df.iloc[:,4]

    # Normalize the tempo variable 
    tracks_df['tempo_normalized'] = round((x-x.min())/ (x.max() - x.min()), 2)
    
    # Sort by popularity
    sorted_df = tracks_df.sort_values('popularity', ascending = False)
    sorted_df.insert(0, 'playlist_id', playlist_id)
    sorted_df.insert(1, 'top_playlist_name', playlist_name)

    return sorted_df

# Combine the dataframes into one dataset to export to CSV or JSON
def make_sp_dataset(country_codes):
    
    top_pl = get_top_playlists(country_codes)

    df = pd.DataFrame()

    # Loop through the dictionary that has the selected country and their top playlist and id
    for k, v in top_pl.items():
        print(f"Making dataframe for {k}: {v['country_name']}")
        new_df = get_spotify_dataframes(v['pl_name'], v['pl_id'])
        new_df.insert(0,'country_code', k, True)
        new_df.insert(1, 'country', v['country_name'], True)

        df = pd.concat([df, new_df])
    
    # Drop the index column from the Spotipy search
    df.reset_index(drop = True, inplace = True)
    
    print("Done!")
    return df

 
# Function to convert a CSV to JSON
# Takes the file paths as arguments
     
from collections import OrderedDict

def make_json(csvFilePath, jsonFilePath):
    csv_rows = []
    with open(csvFilePath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        title = reader.fieldnames
        for row in reader:
            entry = OrderedDict()
            for field in title:
                entry[field] = row[field]
            csv_rows.append(entry)

    with open(jsonFilePath, 'w') as f:
        json.dump(csv_rows, f, sort_keys=True, indent=4, ensure_ascii=False)
        f.write('\n')
