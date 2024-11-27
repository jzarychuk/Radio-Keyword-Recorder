import schedule
import time
from datetime import datetime, timedelta
import subprocess
import sys
import os


SCHEDULED_TIMES = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]
PRIMARY_URL = "https://18313.live.streamtheworld.com/CHQMFM_ADP/HLS/playlist.m3u8"
FALLBACK_URL = "https://25083.live.streamtheworld.com/CHQMFM_ADP/HLS/playlist.m3u8"
FULL_DURATION_SECONDS = 600
FULL_DURATION_MINUTES = FULL_DURATION_SECONDS // 60
FFMPEG_PATH = "/usr/bin/ffmpeg"
MIN_RETRY_DURATION = 10


def record_for_duration(url, duration, attempt_type):

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.mp3"

    # FFmpeg command
    command = [FFMPEG_PATH, "-i", url, "-t", str(duration), filename]

    print(f"Starting {attempt_type} recording for {duration} seconds...")

    # Run the command
    with open(os.devnull, 'w') as devnull:
        subprocess.run(command, check=True, stdout=devnull, stderr=devnull)

    print(f"{attempt_type.capitalize()} recording completed: {filename}")


def retry_recording(remaining_time):
    if remaining_time <= 0:
        print("No remaining time to retry.")
        return
    if remaining_time > MIN_RETRY_DURATION:
        print(f"Retrying for remaining duration: {remaining_time} seconds")
        try:
            record_for_duration(FALLBACK_URL, remaining_time, "retry")
        except subprocess.CalledProcessError as e:
            print(f"Retry also failed: {e}", file=sys.stderr)
    else:
         print("Not enough time remaining to retry.")


def job():

    # Calculate the target end time
    target_end_time = datetime.now() + timedelta(minutes=FULL_DURATION_MINUTES)

    # Record the stream
    try:
        record_for_duration(PRIMARY_URL, FULL_DURATION_SECONDS, "full")
    except subprocess.CalledProcessError as e:
        print(f"Error recording stream: {e}", file=sys.stderr)
        remaining_time = int((target_end_time - datetime.now()).total_seconds())
        retry_recording(remaining_time)


def main():

    # Add jobs to the schedule
    for scheduled_time in SCHEDULED_TIMES:
        schedule.every().day.at(scheduled_time).do(job)

    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()