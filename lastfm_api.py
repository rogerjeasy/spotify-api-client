import requests
import time
import urllib.parse
import csv
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lastfm_fetcher.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

class LastFmDataFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("LASTFM_API_KEY")
        if not self.api_key:
            raise ValueError("Last.fm API key must be provided")
            
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.last_request_time = 0
        self.min_request_interval = 0.25  # 4 requests per second max
        
        # For progress tracking
        self.fetched_artists = set()
        self.progress_file = 'lastfm_fetched_artists.json'
        self.output_file = 'lastfm_artist_data.csv'
        
        # Load previous progress if exists
        self.load_progress()
    
    def load_progress(self):
        """Load previously fetched artist IDs"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    self.fetched_artists = set(json.load(f))
                logging.info(f"Loaded {len(self.fetched_artists)} previously fetched artists")
            except Exception as e:
                logging.error(f"Error loading progress: {e}")
                
    def save_progress(self):
        """Save progress to disk"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(list(self.fetched_artists), f)
        except Exception as e:
            logging.error(f"Error saving progress: {e}")
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits by adding delays between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
                
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
                    
        self.last_request_time = time.time()
             
    def make_request(self, method, params=None):
        """Make a request to the Last.fm API"""
        if params is None:
            params = {}
                    
        params['method'] = method
        params['api_key'] = self.api_key
        params['format'] = 'json'
                
        self._respect_rate_limit()
                
        try:
            response = requests.get(self.base_url, params=params)
            
            if response.status_code != 200:
                logging.error(f"Error: {response.status_code} - {response.text}")
                return None
                    
            return response.json()
        except Exception as e:
            logging.error(f"Request failed: {e}")
            return None
    
    def get_artist_data(self, artist_name):
        """Get comprehensive artist data from Last.fm"""
        artist_data = {}
        
        # Get basic artist info
        params = {
            'artist': artist_name
        }
        result = self.make_request('artist.getInfo', params)
        
        if result and 'artist' in result:
            artist_data['artist_info'] = {
                'listeners': result['artist'].get('stats', {}).get('listeners'),
                'playcount': result['artist'].get('stats', {}).get('playcount'),
                'tags': [tag['name'] for tag in result['artist'].get('tags', {}).get('tag', [])],
                'url': result['artist'].get('url'),
                'mbid': result['artist'].get('mbid'),
                'bio': result['artist'].get('bio', {}).get('summary', ''),
                'streamable': result['artist'].get('streamable', ''),
                'ontour': result['artist'].get('ontour', '')
            }
        else:
            logging.warning(f"No basic info found for artist {artist_name}")
            return None
        
        # Get top tracks
        result = self.make_request('artist.getTopTracks', params={'artist': artist_name, 'limit': 10})
        if result and 'toptracks' in result and 'track' in result['toptracks']:
            artist_data['top_tracks'] = [{
                'name': track['name'],
                'listeners': track.get('listeners', ''),
                'playcount': track.get('playcount', ''),
                'mbid': track.get('mbid', ''),
                'url': track.get('url', '')
            } for track in result['toptracks']['track']]
        else:
            artist_data['top_tracks'] = []
        
        # Get top albums
        result = self.make_request('artist.getTopAlbums', params={'artist': artist_name, 'limit': 10})
        if result and 'topalbums' in result and 'album' in result['topalbums']:
            artist_data['top_albums'] = [{
                'name': album['name'],
                'playcount': album.get('playcount', ''),
                'mbid': album.get('mbid', ''),
                'url': album.get('url', '')
            } for album in result['topalbums']['album']]
        else:
            artist_data['top_albums'] = []
        
        # Get similar artists
        result = self.make_request('artist.getSimilar', params={'artist': artist_name, 'limit': 10})
        if result and 'similarartists' in result and 'artist' in result['similarartists']:
            artist_data['similar_artists'] = [{
                'name': artist['name'],
                'match': artist.get('match', ''),
                'mbid': artist.get('mbid', ''),
                'url': artist.get('url', '')
            } for artist in result['similarartists']['artist']]
        else:
            artist_data['similar_artists'] = []
        
        return artist_data
    
    def write_csv_header(self):
        """Write CSV header if file doesn't exist"""
        if not os.path.exists(self.output_file):
            header = [
                'artist_id', 'artist_name', 'listeners', 'playcount', 'tags',
                'top_tracks', 'top_albums', 'similar_artists', 'lastfm_url',
                'mbid', 'bio_summary', 'streamable', 'on_tour', 'timestamp'
            ]
            
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
    
    def save_artist_data(self, artist_id, artist_name, data):
        """Save artist data to CSV"""
        self.write_csv_header()
        
        try:
            artist_info = data.get('artist_info', {})
            top_tracks = data.get('top_tracks', [])
            top_albums = data.get('top_albums', [])
            similar_artists = data.get('similar_artists', [])
            
            row = [
                artist_id,
                artist_name,
                artist_info.get('listeners', ''),
                artist_info.get('playcount', ''),
                '|'.join(artist_info.get('tags', [])),
                json.dumps(top_tracks),
                json.dumps(top_albums),
                json.dumps(similar_artists),
                artist_info.get('url', ''),
                artist_info.get('mbid', ''),
                artist_info.get('bio', ''),
                artist_info.get('streamable', ''),
                artist_info.get('ontour', ''),
                datetime.now().isoformat()
            ]
            
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
            self.fetched_artists.add(artist_id)
            self.save_progress()
            
        except Exception as e:
            logging.error(f"Error saving data for artist {artist_id}: {e}")
    
    def fetch_artists_from_spotify_data(self, spotify_data_file):
        """Fetch Last.fm data for artists based on Spotify data file"""
        
        # Read artist names from Spotify data file
        artists = []
        try:
            with open(spotify_data_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    artist_id = row.get('artist_id', '')
                    artist_name = row.get('artist_name', '')
                    if artist_id and artist_name and artist_id not in self.fetched_artists:
                        artists.append({'id': artist_id, 'name': artist_name})
                        
        except Exception as e:
            logging.error(f"Error reading Spotify data file: {e}")
            return
        
        logging.info(f"Found {len(artists)} artists to fetch from Last.fm")
        
        # Fetch data for each artist
        for i, artist in enumerate(artists):
            try:
                logging.info(f"Fetching Last.fm data for {i+1}/{len(artists)}: {artist['name']}")
                data = self.get_artist_data(artist['name'])
                
                if data:
                    self.save_artist_data(artist['id'], artist['name'], data)
                    logging.info(f"Successfully saved Last.fm data for {artist['name']}")
                else:
                    logging.warning(f"No Last.fm data returned for {artist['name']}")
                    
                # Progress checkpoint every 20 artists
                if (i + 1) % 20 == 0:
                    logging.info(f"Progress: {i+1}/{len(artists)} artists completed")
                    
            except Exception as e:
                logging.error(f"Error processing artist {artist['name']}: {e}")
                # Continue with next artist
                continue
        
        logging.info("Finished fetching all Last.fm artist data")

# Usage example
if __name__ == "__main__":
    try:
        fetcher = LastFmDataFetcher()
        
        # First check if Spotify data exists
        if os.path.exists('spotify_artist_data.csv'):
            fetcher.fetch_artists_from_spotify_data('spotify_artist_data.csv')
        else:
            logging.error("Spotify data file not found. Please run the Spotify fetcher first.")
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")