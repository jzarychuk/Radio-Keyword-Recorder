import schedule
import time
from datetime import datetime, timedelta
import subprocess
import sys
import os
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


# Load constants globally
config = load_config("config.json")
SCHEDULED_TIMES = config["scheduled_times"]
PRIMARY_URL = config["primary_url"]
FALLBACK_URL = config["fallback_url"]
FULL_DURATION_SECONDS = config["full_duration_seconds"]
FULL_DURATION_MINUTES = FULL_DURATION_SECONDS // 60
FFMPEG_PATH = config["ffmpeg_path"]
MIN_RETRY_DURATION = config["min_retry_duration"]
EMAIL_SENDER = config["email_sender"]
EMAIL_RECIPIENTS = config["email_recipients"]
EMAIL_SUBJECT = config["email_subject"]
EMAIL_CONTENT = config["email_content"]


def send_email(filename):

    # Set the API key
    api_key = os.environ.get("SENDGRID_API_KEY")

    # Create the email message
    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=EMAIL_RECIPIENTS,
        subject=EMAIL_SUBJECT,
        plain_text_content=EMAIL_CONTENT
    )

    # Read and encode the file in Base64
    with open(filename, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode()

    # Create the email attachment
    attachment = Attachment(
        FileContent(file_data),
        FileName(filename),
        FileType("audio/mpeg"),
        Disposition("attachment")
    )

    # Add the attachment to the email
    message.add_attachment(attachment)

    # Send the email
    try:
        SendGridAPIClient(api_key).send(message)
        print(f"Email sent to recipients: {EMAIL_RECIPIENTS}")
    except Exception as e:
        print(f"Error sending email: {e}", file=sys.stderr)


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

    send_email(filename)


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