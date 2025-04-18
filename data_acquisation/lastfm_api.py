import requests
import time
import urllib.parse

class LastFmAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 5 requests per second max
        
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
            
        # Add required parameters
        params['method'] = method
        params['api_key'] = self.api_key
        params['format'] = 'json'
        
        # Respect rate limiting
        self._respect_rate_limit()
        
        # Make the request
        response = requests.get(self.base_url, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
            
        return response.json()
        
    def get_track_info(self, artist, track):
        """Get information about a track"""
        params = {
            'artist': artist,
            'track': track
        }
        return self.make_request('track.getInfo', params)
        
    def get_artist_info(self, artist):
        """Get information about an artist"""
        params = {
            'artist': artist
        }
        return self.make_request('artist.getInfo', params)
        
    def get_top_tracks(self, artist, limit=10):
        """Get top tracks for an artist"""
        params = {
            'artist': artist,
            'limit': limit
        }
        return self.make_request('artist.getTopTracks', params)
        
    def search_track(self, track, limit=10):
        """Search for a track"""
        params = {
            'track': track,
            'limit': limit
        }
        return self.make_request('track.search', params)
        
    def get_similar_tracks(self, artist, track, limit=10):
        """Get similar tracks"""
        params = {
            'artist': artist,
            'track': track,
            'limit': limit
        }
        return self.make_request('track.getSimilar', params)

# Usage example
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("LASTFM_API_KEY")
    lastfm = LastFmAPI(api_key)
    
    # Get track info
    track_info = lastfm.get_track_info("Arctic Monkeys", "Do I Wanna Know?")
    if track_info and 'track' in track_info:
        print(f"Track listeners: {track_info['track'].get('listeners')}")
        print(f"Track play count: {track_info['track'].get('playcount')}")
    
    # Get artist info
    artist_info = lastfm.get_artist_info("Arctic Monkeys")
    if artist_info and 'artist' in artist_info:
        print(f"Artist listeners: {artist_info['artist'].get('stats', {}).get('listeners')}")
        print(f"Artist play count: {artist_info['artist'].get('stats', {}).get('playcount')}")
    
    # Get top tracks for an artist
    top_tracks = lastfm.get_top_tracks("Arctic Monkeys", 5)
    if top_tracks and 'toptracks' in top_tracks and 'track' in top_tracks['toptracks']:
        print("\nTop 5 tracks:")
        for i, track in enumerate(top_tracks['toptracks']['track'][:5], 1):
            print(f"{i}. {track['name']} - Listeners: {track['listeners']}")