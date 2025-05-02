import requests
import base64
import json
import time
import random
import os
import csv
import logging
from datetime import datetime
from requests.exceptions import RequestException
from dotenv import load_dotenv
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotify_fetcher.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables from .env file
load_dotenv()

class SpotifyDataFetcher:
    def __init__(self, client_id=None, client_secret=None):
        """Initialize Spotify API client with client ID and secret"""
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify client ID and secret must be provided either as parameters or environment variables")
        
        self.token = None
        self.token_expiry = 0
        self.last_request_time = 0
        self.min_request_interval = 0.05  # Limit to 20 requests per second to be safe
        self.retry_wait = 1  # Initial wait time for retries in seconds
        
        # For progress tracking
        self.fetched_artists = set()
        self.progress_file = 'spotify_fetched_artists.json'
        self.output_file = 'spotify_artist_data.csv'
        
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
            
    def get_token(self):
        """Get Spotify API access token using client credentials flow"""
        if self.token and time.time() < self.token_expiry:
            return self.token
            
        # Prepare authorization header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        # Token endpoint
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        logging.info("Requesting access token...")
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data["access_token"]
            self.token_expiry = time.time() + token_data["expires_in"] - 60  # Buffer of 60 seconds
            logging.info("Successfully obtained access token")
            return self.token
            
        except Exception as e:
            logging.error(f"Error obtaining access token: {e}")
            if hasattr(response, 'text'):
                logging.error(f"Response text: {response.text}")
            raise
    
    def get_headers(self):
        """Get headers for API requests"""
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits by adding delays between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _make_request_with_retry(self, method, url, max_retries=5, **kwargs):
        """Make a request with exponential backoff retry logic"""
        retry_count = 0
        wait_time = self.retry_wait
        
        while retry_count <= max_retries:
            self._respect_rate_limit()
            
            try:
                if method.lower() == "get":
                    response = requests.get(url, **kwargs)
                elif method.lower() == "post":
                    response = requests.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', wait_time))
                    logging.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    retry_count += 1
                    wait_time *= 2  # Exponential backoff
                    continue
                    
                if response.status_code >= 500:  # Server errors
                    logging.warning(f"Server error {response.status_code}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retry_count += 1
                    wait_time *= 2  # Exponential backoff
                    continue
                
                if response.status_code == 403:  # Forbidden
                    logging.error(f"Forbidden error. Response: {response.text}")
                    if "token" in response.text.lower() or "access" in response.text.lower():
                        logging.info("Token might be invalid. Attempting to get a new token...")
                        self.token = None
                        if 'headers' in kwargs:
                            kwargs['headers'] = self.get_headers()
                        retry_count += 1
                        continue
                
                response.raise_for_status()
                return response
                
            except RequestException as e:
                logging.error(f"Request failed: {e}")
                if hasattr(e.response, 'text'):
                    logging.error(f"Error response: {e.response.text}")
                
                if retry_count >= max_retries:
                    raise
                
                jitter = random.uniform(0, 0.5)
                sleep_time = wait_time + jitter
                logging.info(f"Retrying in {sleep_time:.2f} seconds... (Attempt {retry_count+1}/{max_retries})")
                time.sleep(sleep_time)
                retry_count += 1
                wait_time *= 2
    
    def get_artist_data(self, artist_id):
        """Get comprehensive artist data from Spotify"""
        artist_data = {}
        
        # Get basic artist info
        try:
            url = f"https://api.spotify.com/v1/artists/{artist_id}"
            response = self._make_request_with_retry(
                method="get",
                url=url,
                headers=self.get_headers()
            )
            
            artist_info = response.json()
            artist_data['artist_info'] = artist_info
            
        except Exception as e:
            logging.error(f"Error getting artist info for {artist_id}: {e}")
            return None
        
        # Get artist's top tracks
        try:
            url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US"
            response = self._make_request_with_retry(
                method="get",
                url=url,
                headers=self.get_headers()
            )
            
            top_tracks = response.json()
            artist_data['top_tracks'] = top_tracks.get('tracks', [])
            
        except Exception as e:
            logging.error(f"Error getting top tracks for {artist_id}: {e}")
            artist_data['top_tracks'] = []
        
        # Get audio analysis for top tracks
        # if artist_data.get('top_tracks'):
        #     audio_analysis_data = []
        #     for track in artist_data['top_tracks'][:5]:  # Limit to top 5 tracks to avoid too many requests
        #         try:
        #             track_id = track.get('id')
        #             if track_id:
        #                 url = f"https://api.spotify.com/v1/audio-analysis/{track_id}"
        #                 response = self._make_request_with_retry(
        #                     method="get",
        #                     url=url,
        #                     headers=self.get_headers()
        #                 )
        #                 
        #                 analysis = response.json()
        #                 # Extract key metrics from the analysis
        #                 simplified_analysis = {
        #                     'track_id': track_id,
        #                     'track_name': track.get('name', ''),
        #                     'duration': track.get('duration_ms', 0) / 1000,  # Convert to seconds
        #                     'tempo': analysis.get('track', {}).get('tempo', 0),
        #                     'time_signature': analysis.get('track', {}).get('time_signature', 4),
        #                     'key': analysis.get('track', {}).get('key', -1),
        #                     'mode': analysis.get('track', {}).get('mode', -1),
        #                     'loudness': analysis.get('track', {}).get('loudness', 0),
        #                     'sections_count': len(analysis.get('sections', [])),
        #                     'segments_count': len(analysis.get('segments', [])),
        #                     'tatums_count': len(analysis.get('tatums', [])),
        #                     'beats_count': len(analysis.get('beats', [])),
        #                     'bars_count': len(analysis.get('bars', []))
        #                 }
        #                 
        #                 # Add track-level audio features if available
        #                 track_data = analysis.get('track', {})
        #                 if 'analysis_channels' in track_data:
        #                     simplified_analysis['analysis_channels'] = track_data['analysis_channels']
        #                 if 'analysis_sample_rate' in track_data:
        #                     simplified_analysis['analysis_sample_rate'] = track_data['analysis_sample_rate']
        #                 
        #                 audio_analysis_data.append(simplified_analysis)
        #                 
        #         except Exception as e:
        #             logging.error(f"Error getting audio analysis for track {track.get('id', '')} of artist {artist_id}: {e}")
        #             continue
        #     
        #     artist_data['audio_analysis'] = audio_analysis_data
        artist_data['audio_analysis'] = []  # Empty list when audio analysis is commented out
        
        # Get related artists
        # try:
        #     url = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"
        #     response = self._make_request_with_retry(
        #         method="get",
        #         url=url,
        #         headers=self.get_headers()
        #     )
        #     
        #     related_artists = response.json()
        #     artist_data['related_artists'] = [
        #         {
        #             'id': artist.get('id'),
        #             'name': artist.get('name'),
        #             'popularity': artist.get('popularity', 0)
        #         }
        #         for artist in related_artists.get('artists', [])
        #     ]
        #     
        # except Exception as e:
        #     logging.error(f"Error getting related artists for {artist_id}: {e}")
        #     artist_data['related_artists'] = []
        artist_data['related_artists'] = []  # Empty list when related artists is commented out
        
        # Get artist's albums
        try:
            url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?market=US&limit=50"
            response = self._make_request_with_retry(
                method="get",
                url=url,
                headers=self.get_headers()
            )
            
            albums = response.json()
            artist_data['albums'] = [{
                'id': album.get('id'),
                'name': album.get('name'),
                'release_date': album.get('release_date'),
                'total_tracks': album.get('total_tracks', 0),
                'type': album.get('album_type')
            } for album in albums.get('items', [])]
            
        except Exception as e:
            logging.error(f"Error getting albums for {artist_id}: {e}")
            artist_data['albums'] = []
        
        return artist_data
    
    def write_csv_header(self):
        """Write CSV header if file doesn't exist"""
        if not os.path.exists(self.output_file):
            header = [
                'artist_id', 'artist_name', 'followers', 'popularity', 'genres',
                'top_tracks', 'audio_analysis', 'related_artists',  # Changed from top_tracks_audio_features to audio_analysis
                'albums_count', 'external_urls', 'spotify_url', 'timestamp'
            ]
            
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
    
    def save_artist_data(self, artist_id, data):
        """Save artist data to CSV"""
        self.write_csv_header()
        
        try:
            artist_info = data.get('artist_info', {})
            top_tracks = data.get('top_tracks', [])
            audio_analysis = data.get('audio_analysis', [])
            related_artists = data.get('related_artists', [])
            albums = data.get('albums', [])
            
            # Format top tracks data
            top_tracks_info = []
            for i, track in enumerate(top_tracks):
                track_info = {
                    'id': track.get('id', ''),
                    'name': track.get('name', ''),
                    'popularity': track.get('popularity', 0),
                    'explicit': track.get('explicit', False),
                    'duration_ms': track.get('duration_ms', 0)
                }
                top_tracks_info.append(track_info)
            
            row = [
                artist_id,
                artist_info.get('name', ''),
                artist_info.get('followers', {}).get('total', ''),
                artist_info.get('popularity', ''),
                '|'.join(artist_info.get('genres', [])),
                json.dumps(top_tracks_info),
                '',  # Audio analysis commented out
                '',  # Related artists commented out
                len(albums),
                json.dumps(artist_info.get('external_urls', {})),
                artist_info.get('external_urls', {}).get('spotify', ''),
                datetime.now().isoformat()
            ]
            
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
            self.fetched_artists.add(artist_id)
            self.save_progress()
            
        except Exception as e:
            logging.error(f"Error saving data for artist {artist_id}: {e}")
    
    def fetch_artists_from_csv(self, input_csv_path, artist_id_column='artist_uri 3'):
        """Fetch data for artists from CSV file"""

        total_count = 0
        remaining_artists = []
        try:
            with open(input_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    artist_uri = row.get(artist_id_column, '')
                    if artist_uri.startswith('spotify:artist:'):
                        artist_id = artist_uri.split(':')[-1]
                    else:
                        artist_id = artist_uri

                    total_count += 1
                    if artist_id in self.fetched_artists:
                        continue

                    remaining_artists.append(artist_id)
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
            return

        logging.info(f"Found {total_count} entries, {len(remaining_artists)} unique values appended for API call")

        # Fetch data for each artist
        for i, artist_id in enumerate(tqdm(remaining_artists, desc="Fetching artists", unit="artist")):
            try:
                logging.info(f"Fetching data for artist {i+1}/{len(remaining_artists)} (ID: {artist_id})")
                data = self.get_artist_data(artist_id)

                if data:
                    self.save_artist_data(artist_id, data)
                    logging.info(f"Successfully saved data for artist {artist_id}")
                else:
                    logging.warning(f"No data returned for artist {artist_id}")

                # Progress checkpoint every 10 artists
                if (i + 1) % 10 == 0:
                    logging.info(f"Progress: {i+1}/{len(remaining_artists)} artists completed")

            except Exception as e:
                logging.error(f"Error processing artist {artist_id}: {e}")
                # Continue with next artist
                continue

        logging.info("Finished fetching all artist data")

# Usage example
if __name__ == "__main__":
    try:
        fetcher = SpotifyDataFetcher()
        fetcher.fetch_artists_from_csv('10000_artists_NbiggerThan500.csv')
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")