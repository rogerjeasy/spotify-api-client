import os
import logging
import argparse
from spotify_api import SpotifyDataFetcher
from lastfm_api import LastFmDataFetcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_fetcher_main.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main function to orchestrate data fetching from Spotify and Last.fm"""
    
    parser = argparse.ArgumentParser(description='Fetch data from Spotify and Last.fm APIs')
    parser.add_argument('--spotify-only', action='store_true', help='Fetch only Spotify data')
    parser.add_argument('--lastfm-only', action='store_true', help='Fetch only Last.fm data')
    parser.add_argument('--csv-file', default='10000_artists_NbiggerThan500.csv', 
                        help='Input CSV file with artist IDs')
    args = parser.parse_args()
    
    try:
        # Fetch Spotify data
        if not args.lastfm_only:
            logging.info("=== Starting Data Fetching Process ===")
        
        # Fetch Spotify data
        if not args.lastfm_only:
            logging.info("--- Fetching Spotify data ---")
            try:
                spotify_fetcher = SpotifyDataFetcher()
                spotify_fetcher.fetch_artists_from_csv(args.csv_file)
                logging.info("Spotify data fetching completed")
            except Exception as e:
                logging.error(f"Error during Spotify data fetching: {e}")
                if not args.spotify_only:
                    logging.info("Continuing with Last.fm data...")
        
        # Fetch Last.fm data
        if not args.spotify_only:
            logging.info("--- Fetching Last.fm data ---")
            try:
                if os.path.exists('spotify_artist_data.csv'):
                    lastfm_fetcher = LastFmDataFetcher()
                    lastfm_fetcher.fetch_artists_from_spotify_data('spotify_artist_data.csv')
                    logging.info("Last.fm data fetching completed")
                else:
                    logging.warning("No Spotify data file found. Cannot fetch Last.fm data.")
            except Exception as e:
                logging.error(f"Error during Last.fm data fetching: {e}")
        
        logging.info("=== Data Fetching Process Completed ===")
        
        # Summary
        if os.path.exists('spotify_artist_data.csv'):
            with open('spotify_artist_data.csv', 'r') as f:
                spotify_count = sum(1 for line in f) - 1  # Subtract header
                logging.info(f"Spotify data: {spotify_count} artists")
        
        if os.path.exists('lastfm_artist_data.csv'):
            with open('lastfm_artist_data.csv', 'r') as f:
                lastfm_count = sum(1 for line in f) - 1  # Subtract header
                logging.info(f"Last.fm data: {lastfm_count} artists")
        
    except KeyboardInterrupt:
        logging.info("\nProcess interrupted by user. Progress has been saved.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()