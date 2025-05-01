# Spotify & Last.fm API Data Collection

This project provides Python scripts for collecting music data from Spotify and Last.fm APIs. It includes comprehensive fetchers for gathering artist information, track data, and analytics from both platforms.

## Features

- **Spotify Data Collection**:
  - Artist information (followers, popularity, genres)
  - Top tracks
  - Albums and discography
  - Progress tracking and resume capability
  - Rate limiting and error handling
  - Optional: Audio analysis (currently commented out)
  - Optional: Related artists (currently commented out)

- **Last.fm Data Collection**:
  - Artist statistics (listeners, play counts)
  - Top tracks and albums
  - Similar artists
  - Tags and biographical information

## Prerequisites

- Python 3.10+
- Spotify Developer account with API credentials
- Last.fm API key

## Setup

### 1. Create a Virtual Environment

```bash
# Create a virtual environment
python -m venv spotify_api_env

# Activate the virtual environment
# On Windows
spotify_api_env\Scripts\activate
# On macOS/Linux
source spotify_api_env/bin/activate
```

### 2. Install Dependencies

```bash
# Install required packages
pip install requests python-dotenv pandas
```

Or use the requirements.txt file:

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root directory with your API credentials:

```
# Spotify API credentials
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Last.fm API credentials
LASTFM_API_KEY=your_lastfm_api_key
```

## Input Data Format

The Spotify fetcher expects a CSV file with artist URIs. The CSV should have a column named `artist_uri 3` containing Spotify URIs in just artist IDs.

Example CSV structure:
```
artist_uri 3
1vCWHaC5f2uS3yhpwWbIA6
3TVXtAsR1Inumwj472S9r4
```

## Usage

### Running the Spotify Fetcher

```bash
python spotify_api.py
```

This script will:
1. Read artist IDs from `10000_artists_NbiggerThan500.csv` (default filename)
2. Fetch comprehensive artist data for each artist
3. Save progress to `spotify_fetched_artists.json`
4. Output data to `spotify_artist_data.csv`

### Running the Last.fm Fetcher

```bash
python lastfm_api.py
```

This script will:
1. Read artist names from the Spotify data CSV (`spotify_artist_data.csv`)
2. Fetch Last.fm data for each artist
3. Save progress to `lastfm_fetched_artists.json`
4. Output data to `lastfm_artist_data.csv`

### Running Main Orchestrator

```bash
# Fetch both Spotify and Last.fm data
python data_fetcher_main.py

# Fetch only Spotify data
python data_fetcher_main.py --spotify-only

# Fetch only Last.fm data
python data_fetcher_main.py --lastfm-only

# Use a custom CSV file
python data_fetcher_main.py --csv-file custom_artists.csv
```

## Output Data

### Spotify CSV Output

The `spotify_artist_data.csv` contains:
- `artist_id`: Spotify artist ID
- `artist_name`: Artist name
- `followers`: Number of followers
- `popularity`: Spotify popularity score (0-100)
- `genres`: Pipe-separated list of genres
- `top_tracks`: JSON array of top tracks with details
- `albums_count`: Number of albums
- `external_urls`: JSON of external URLs
- `spotify_url`: Direct link to artist on Spotify
- `timestamp`: Data collection timestamp

### Last.fm CSV Output

The `lastfm_artist_data.csv` contains:
- `artist_id`: Artist ID (from Spotify)
- `artist_name`: Artist name
- `listeners`: Number of Last.fm listeners
- `playcount`: Total play count
- `tags`: Pipe-separated list of tags
- `top_tracks`: JSON array of top tracks
- `top_albums`: JSON array of top albums
- `similar_artists`: JSON array of similar artists
- `lastfm_url`: Last.fm artist page URL
- `mbid`: MusicBrainz ID
- `bio_summary`: Artist biography summary
- `streamable`: Whether the artist is streamable
- `on_tour`: Whether the artist is on tour
- `timestamp`: Data collection timestamp

<!-- ## Data Analysis

### Reading Data in Jupyter Notebook

Use the following code to load and analyze the collected data:

```python
import pandas as pd
import json

# Read CSV files
spotify_df = pd.read_csv('spotify_artist_data.csv')
lastfm_df = pd.read_csv('lastfm_artist_data.csv')

# Parse JSON fields
spotify_df['top_tracks_parsed'] = spotify_df['top_tracks'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '' else [])
spotify_df['genres_list'] = spotify_df['genres'].apply(lambda x: x.split('|') if pd.notna(x) and x != '' else [])

# Basic analysis
print(f"Total artists: {len(spotify_df)}")
print(f"Average popularity: {spotify_df['popularity'].mean():.2f}")
print(f"Total followers: {spotify_df['followers'].sum():,}")
``` -->

## Progress Tracking

Both fetchers include progress tracking features:
- Progress is saved after each successful fetch
- Fetchers can resume from where they left off if interrupted
- Progress files: `spotify_fetched_artists.json` and `lastfm_fetched_artists.json`

## Rate Limiting

- Spotify: Limited to 20 requests per second (configurable)
- Last.fm: Limited to 4 requests per second (as per API guidelines)
- Both include exponential backoff for rate limit errors

## Error Handling

- Comprehensive error logging
- Automatic retries with exponential backoff
- Graceful handling of missing or malformed data
- Progress preservation on unexpected errors

## Troubleshooting

1. **Authentication Errors**:
   - Verify your API credentials in the `.env` file
   - Ensure your Spotify app has the correct permissions

2. **Rate Limiting**:
   - Default rate limits are configured conservatively
   - Adjust `min_request_interval` if needed

3. **Missing Data**:
   - Some artists may not be available on both platforms
   - Check log files for specific errors

4. **Progress Recovery**:
   - Delete progress JSON files to start fresh
   - Manual editing of progress files may be needed for specific artists

## Commented Out Features

The following features are currently commented out but can be re-enabled:
- **Spotify Audio Analysis**: Uncomment the audio analysis section in `spotify_api.py`
- **Spotify Related Artists**: Uncomment the related artists section in `spotify_api.py`

These features were commented out because they are deprecated and are returning 403 error message.

## Requirements.txt

```
requests==2.31.0
python-dotenv==1.0.0
pandas==2.1.3
```

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
Feel free to reach out if you have any questions or suggestions.