import requests
import base64
import json
import time
import random
import os
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SpotifyAPI:
    def __init__(self, client_id=None, client_secret=None):
        """Initialize Spotify API client with client ID and secret"""
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify client ID and secret must be provided either as parameters or environment variables")
        
        print(f"Client ID found: {'Yes' if self.client_id else 'No'}")
        print(f"Client Secret found: {'Yes' if self.client_secret else 'No'}")
        
        self.token = None
        self.token_expiry = 0
        self.last_request_time = 0
        self.min_request_interval = 0.05  # Limit to 20 requests per second to be safe
        self.retry_wait = 1  # Initial wait time for retries in seconds
        
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
        
        print("Requesting access token...")
        
        try:
            # Make the token request directly without retry logic for better error visibility
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            token_data = response.json()
            self.token = token_data["access_token"]
            self.token_expiry = time.time() + token_data["expires_in"] - 60  # Buffer of 60 seconds
            print("Successfully obtained access token")
            return self.token
            
        except Exception as e:
            print(f"Error obtaining access token: {e}")
            if hasattr(response, 'text'):
                print(f"Response text: {response.text}")
            raise
    
    def get_headers(self):
        """Get headers for API requests"""
        token = self.get_token()
        print(f"Using token: {token[:5]}...{token[-5:]}")
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
                
                # Print response status and headers for debugging
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 429:  # Too Many Requests
                    # Get retry-after header, or use exponential backoff
                    retry_after = int(response.headers.get('Retry-After', wait_time))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    retry_count += 1
                    wait_time *= 2  # Exponential backoff
                    continue
                    
                if response.status_code >= 500:  # Server errors
                    print(f"Server error {response.status_code}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retry_count += 1
                    wait_time *= 2  # Exponential backoff
                    continue
                
                if response.status_code == 403:  # Forbidden
                    print(f"Forbidden error. Response: {response.text}")
                    # If this is a token issue, try to get a new token
                    if "token" in response.text.lower() or "access" in response.text.lower():
                        print("Token might be invalid. Attempting to get a new token...")
                        # Invalidate current token
                        self.token = None
                        # Update headers with new token
                        if 'headers' in kwargs:
                            kwargs['headers'] = self.get_headers()
                        retry_count += 1
                        continue
                
                # Success or client error (not retryable)
                response.raise_for_status()  # Raise exception for 4xx errors except those handled above
                return response
                
            except RequestException as e:
                print(f"Request failed: {e}")
                if hasattr(e.response, 'text'):
                    print(f"Error response: {e.response.text}")
                
                if retry_count >= max_retries:
                    raise
                
                # Add jitter to avoid thundering herd problem
                jitter = random.uniform(0, 0.5)
                sleep_time = wait_time + jitter
                print(f"Retrying in {sleep_time:.2f} seconds... (Attempt {retry_count+1}/{max_retries})")
                time.sleep(sleep_time)
                retry_count += 1
                wait_time *= 2  # Exponential backoff
    
    def get_audio_features(self, track_ids):
        """Get audio features for multiple tracks"""
        if not track_ids:
            print("No track IDs provided")
            return []
            
        # Split IDs into chunks of 100 (API limit)
        results = []
        for i in range(0, len(track_ids), 100):
            chunk = track_ids[i:i+100]
            ids_param = ",".join(chunk)
            url = f"https://api.spotify.com/v1/audio-features?ids={ids_param}"
            
            try:
                headers = self.get_headers()
                print(f"Making request to {url}")
                print(f"Headers: Authorization: Bearer {headers['Authorization'][7:15]}...")
                
                response = self._make_request_with_retry(
                    method="get",
                    url=url,
                    headers=headers
                )
                
                data = response.json()
                
                if "audio_features" not in data:
                    print(f"Unexpected response format: {data}")
                    continue
                    
                features = data["audio_features"]
                results.extend(features)
                print(f"Retrieved audio features for {len(chunk)} tracks")
            except Exception as e:
                print(f"Error getting audio features: {e}")
                continue
                
        return results
    
    def get_artists(self, artist_ids):
        """Get metadata for multiple artists"""
        if not artist_ids:
            print("No artist IDs provided")
            return []
            
        results = []
        for i in range(0, len(artist_ids), 50):
            chunk = artist_ids[i:i+50]
            ids_param = ",".join(chunk)
            url = f"https://api.spotify.com/v1/artists?ids={ids_param}"
            
            try:
                response = self._make_request_with_retry(
                    method="get",
                    url=url,
                    headers=self.get_headers()
                )
                
                data = response.json()
                
                if "artists" not in data:
                    print(f"Unexpected response format: {data}")
                    continue
                    
                artists = data["artists"]
                results.extend(artists)
                print(f"Retrieved metadata for {len(chunk)} artists")
            except Exception as e:
                print(f"Error getting artists: {e}")
                continue
                
        return results
    
    def get_tracks(self, track_ids):
        """Get metadata for multiple tracks"""
        if not track_ids:
            print("No track IDs provided")
            return []
            
        results = []
        for i in range(0, len(track_ids), 50):
            chunk = track_ids[i:i+50]
            ids_param = ",".join(chunk)
            url = f"https://api.spotify.com/v1/tracks?ids={ids_param}"
            
            try:
                response = self._make_request_with_retry(
                    method="get",
                    url=url,
                    headers=self.get_headers()
                )
                
                data = response.json()
                
                if "tracks" not in data:
                    print(f"Unexpected response format: {data}")
                    continue
                    
                tracks = data["tracks"]
                results.extend(tracks)
                print(f"Retrieved metadata for {len(chunk)} tracks")
            except Exception as e:
                print(f"Error getting tracks: {e}")
                continue
                
        return results

def test_env_variables():
    """Test if environment variables are properly loaded"""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    print("\nEnvironment Variables Check:")
    print(f"SPOTIFY_CLIENT_ID exists: {'Yes' if client_id else 'No'}")
    print(f"SPOTIFY_CLIENT_SECRET exists: {'Yes' if client_secret else 'No'}")
    
    if not client_id or not client_secret:
        print("\nPlease create a .env file in the same directory with the following content:")
        print("SPOTIFY_CLIENT_ID=your_client_id_here")
        print("SPOTIFY_CLIENT_SECRET=your_client_secret_here")
        print("\nYou can obtain these credentials from your Spotify Developer Dashboard:")
        print("https://developer.spotify.com/dashboard/")
    else:
        print("Environment variables loaded successfully!")
    
    return bool(client_id and client_secret)

# Helper function for safe JSON printing
def safe_print_json(data, indent=2):
    """Safely print JSON data with error handling"""
    if not data:
        print("No data to display")
        return
        
    if isinstance(data, list) and not data:
        print("Empty list")
        return
        
    try:
        if isinstance(data, list) and data:
            print(json.dumps(data[0], indent=indent))
        else:
            print(json.dumps(data, indent=indent))
    except Exception as e:
        print(f"Error printing JSON: {e}")
        print(f"Raw data: {data}")

# Usage example
if __name__ == "__main__":
    # First verify environment variables
    if not test_env_variables():
        print("Exiting due to missing environment variables.")
        exit(1)
    
    try:
        spotify = SpotifyAPI()
        
        # Example track IDs (These are Spotify's track IDs)
        track_ids = [
            "11dFghVXANMlKmJXsNCbNl",  # "Shape of You" by Ed Sheeran
            "20I6sIOMTCkB6w7ryavxtO",  # "Blinding Lights" by The Weeknd
            "7xGfFoTpQ2E7fRF5lN10tr"   # "Someone You Loved" by Lewis Capaldi
        ]
        
        # Example artist IDs
        artist_ids = [
            "0TnOYISbd1XYRBk9myaseg",  # Pitbull
            "6qqNVTkY8uBg9cP3Jd7DAH",  # Billie Eilish
            "3TVXtAsR1Inumwj472S9r4"   # Drake
        ]
        
        # Try getting a token first to verify authentication
        print("\nTesting authentication...")
        token = spotify.get_token()
        print(f"Authentication successful: {'Yes' if token else 'No'}")
        
        # Fetch and print data
        print("\nAUDIO FEATURES:")
        features = spotify.get_audio_features(track_ids)
        if features:
            safe_print_json(features[0])
        else:
            print("No audio features returned")
        
        print("\nARTIST METADATA:")
        artists = spotify.get_artists(artist_ids)
        if artists:
            safe_print_json(artists[0])
        else:
            print("No artist metadata returned")
        
        print("\nTRACK METADATA:")
        tracks = spotify.get_tracks(track_ids)
        if tracks:
            safe_print_json(tracks[0])
        else:
            print("No track metadata returned")
            
    except Exception as e:
        print(f"An error occurred: {e}")