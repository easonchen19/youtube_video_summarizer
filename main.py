import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import openai
from dotenv import load_dotenv
import logging
import requests
import re
import os

# Load API keys from .env file
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize APIs
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY is missing. Please check your .env file.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing. Please check your .env file.")

try:
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Failed to initialize YouTube API: {e}")

openai.api_key = OPENAI_API_KEY

# --- STEP 1: Fetch Latest Videos from a YouTube Channel ---
def get_latest_videos(channel_id, max_results=1):
    """Fetch the latest videos from a YouTube channel."""
    request = youtube.search().list(
        channelId=channel_id,
        order="date",
        part="id,snippet",
        maxResults=max_results
    )
    response = request.execute()
    videos = []
    for item in response['items']:
        if item['id']['kind'] == 'youtube#video':
            videos.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'url': f"https://youtube.com/watch?v={item['id']['videoId']}"
            })
            print(videos[-1])  # Print the latest video details
    return videos

# --- STEP 2: Get Video Transcript ---
def get_video_transcript(video_id):
    """Fetch video transcript using YouTubeTranscriptApi."""
    # try:
    #     transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
    #     text = " ".join([entry['text'] for entry in transcript])
    #     return text
    # except Exception as e:
    #     print(f"Error fetching transcript: {e}")
    #     return None

    """
    Download the transcript and return as a string.
    Args:
        video_id (str): The YouTube video ID.
    Returns:
        str: The transcript text or an empty string if an error occurs.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_generated_transcript(['en'])

        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript.fetch())

        # Remove timecodes and speaker names
        transcript_text = re.sub(r'\[\d+:\d+:\d+\]', '', transcript_text)
        transcript_text = re.sub(r'<\w+>', '', transcript_text)
        return transcript_text
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return ""

# --- STEP 3: Summarize Transcript with OpenAI ---
def summarize_text(text, model="gpt-3.5-turbo"):
    """Generate a summary using OpenAI GPT."""
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "Summarize this video transcript in 10 bullet points:"},
                {"role": "user", "content": text}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing: {e}")
        return None

# --- STEP 4: Save Results to a File ---
def save_results(video_title, video_url, summary):
    """Save video details and summary to a text file."""
    with open("video_summaries.txt", "a", encoding="utf-8") as f:
        f.write(f"Title: {video_title}\n")
        f.write(f"URL: {video_url}\n")
        f.write(f"Summary:\n{summary}\n")
        f.write("-" * 50 + "\n\n")

# --- MAIN EXECUTION ---
if __name__ == "__main__":

    # Get the channel ID
    channel_name = "BloombergTechnology"
    request = youtube.search().list(q=channel_name, type='channel', part='id', maxResults=1)
    response = request.execute()
    channel_id = response['items'][0]['id']['channelId']

    # Replace with your target YouTube channel ID
    # CHANNEL_ID = "UCrM7B7SL_g1edFOnmj-SDKg"  # Example: bloomberg technology
    
    print("Fetching latest video...")
    videos = get_latest_videos(channel_id)
    
    if videos:
        video = videos[0]  # Get the latest video
        print(f"Found video: {video['title']}")
        
        print("Fetching transcript...")
        transcript = get_video_transcript(video['video_id'])
        # transcript = "this is a test transcript"  # Placeholder for testing
        
        if transcript:
            print("Summarizing...")
            summary = summarize_text(transcript)
            
            if summary:
                print("Saving results...")
                save_results(video['title'], video['url'], summary)
                print("Done! Check 'video_summaries.txt'.")
            else:
                print("Failed to summarize.")
        else:
            print("No transcript available.")
    else:
        print("No videos found.")
