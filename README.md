# Spotify & Last.fm API Integration

This project provides a Python wrapper for Spotify and Last.fm APIs to gather music data for analysis. It includes classes for interacting with both APIs and handling common tasks such as authentication, rate limiting, and error handling.

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
pip install requests python-dotenv
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

## Usage

### Spotify API

```bash
# Run the Spotify API example
python data_acquisation/spotify_api.py
```

This will:
- Verify your Spotify API credentials
- Get metadata for example tracks and artists
- Attempt to get audio features for tracks (Note: Audio Features endpoint is deprecated)

### Last.fm API

```bash
# Run the Last.fm API example
python data_acquisation/lastfm_api.py
```

This will:
- Get track information for "Do I Wanna Know?" by Arctic Monkeys
- Get artist information for Arctic Monkeys
- Get top 5 tracks for Arctic Monkeys

## Notes on Spotify Audio Features

The Spotify Audio Features endpoint is now deprecated. As an alternative, consider:

1. Using the Audio Analysis endpoint: `/v1/audio-analysis/{id}`
2. Supplementing with Last.fm tag data for genre information
3. Relying on artist, track, and playlist metadata for trend analysis

## Troubleshooting

If you encounter issues:

1. **Authentication Errors**:
   - Verify your API credentials in the `.env` file
   - Check if your Spotify app is properly configured

2. **Rate Limiting**:
   - The code includes rate limiting, but you may still hit limits with large requests
   - Implement exponential backoff for repeated failures

3. **Missing Environment Variables**:
   - Ensure your `.env` file is in the correct location
   - Make sure you've activated the virtual environment

## Requirements.txt

All requirements are listed in the `requirements.txt` file. You can install them using:

```bash
pip install -r requirements.txt
```