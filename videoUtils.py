"""
File: videoUtils.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains functions for working with videos.
"""

import os
import cv2


def search_for_mp4_files(directory):
    """Search for MP4 files in the specified directory and its subdirectories"""
    # Define the file extension to search for
    extension = '.mp4'

    # Initialize a list to store the paths of the MP4 files
    mp4_files = []

    # Walk the directory tree
    for dirpath, dirnames, filenames in os.walk(directory):
        # Loop through the filenames
        for filename in filenames:
            # Check if the file has the desired extension
            if filename.endswith(extension):
                # Construct the full path of the file
                file_path = os.path.join(dirpath, filename)
                
                # Add the file path to the list of MP4 files
                mp4_files.append(file_path)

    # Print the list of MP4 files
    # print(mp4_files)
    return mp4_files

def filter_out_short_videos(mp4_files, minDuration : int):
    """Filter out short videos from the specified list of MP4 files"""
    # Initialize a list to store the paths of the long videos
    long_videos = []

    # Loop through the MP4 files
    for video_path in mp4_files:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print('Unable to open:' + video_path)
            continue

        # Get the frames per second of the video
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Get the duration of the video in seconds
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

        if duration < minDuration:
            # Skip the video
            # print(f'Skipped {video_name}')
            continue

        # Add the video path to the list of long videos
        long_videos.append(video_path)

        # Release the video capture
        cap.release()

    # Return the list of long videos
    return long_videos


def filter_out_old_videos(mp4_files, minCreationDate : int):
    """Filter out old videos from the specified list of MP4 files
    
    Args:
        mp4_files (list[str]): List of paths to the MP4 files
        minCreationDate (int): Minimum creation date of the videos in UNIX time
        
        Returns:
            list[str]: List of paths to the videos that were created after the specified date"""
    # Initialize a list to store the paths of the new videos
    filtered_videos = []

    # Loop through the MP4 files
    for video_path in mp4_files:
        # Get the creation date of the video
        creation_date = int(os.path.getctime(video_path))

        if creation_date < minCreationDate:
            # Skip the video
            # print(f'Skipped {video_name}')
            continue

        # Add the video path to the list of new videos
        filtered_videos.append(video_path)

    # Return the list of new videos
    return filtered_videos


def make_screenshots(mp4_files, timestamps : list[int]) -> None:
    """Make screenshots of the specified MP4 files at specified timestamps, and place them in ./screenshots directory"""
    # Check if screenshots directory exists
    if not os.path.exists('screenshots'):
        # Create the screenshots directory
        os.mkdir('screenshots')
    else:
        # Clear the screenshots directory
        clear_screenshots()

    # Loop through the MP4 files
    for video_path in mp4_files:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print('Unable to open:' + video_path)
            continue

        # Get video name
        video_name = os.path.basename(video_path)

        # Get the frames per second of the video
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Take screenshots at the specified timestamps
        for t in timestamps:
            try:
                # Set the position of the video to the specified timestamp
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
                
                # Read the next frame from the video
                ret, frame = cap.read()
                
                # Save the screenshot
                cv2.imwrite(rf'screenshots\{video_name}_screenshot_at_{t}_seconds.png', frame)
                print(f'Saved {video_name}_screenshot_at_{t}_seconds.png')
            except Exception as e:
                print(f"Could not save screenshot for {video_name} at {t} seconds")

        # Release the video capture
        cap.release()


def clear_screenshots():
    """Clears the screenshots directory
    """
    # Check if screenshots directory exists
    if os.path.exists('screenshots'):
        # Clear the screenshots directory
        for file in os.listdir('screenshots'):
            os.remove(os.path.join('screenshots', file))


def get_video_creation_dates(videos : list[str]) -> dict[str, int]:
    """Get the creation dates of the specified videos

    Args:
        videos (list[str]): List of paths to the videos

    Returns:
        dict[str, int]: Dictionary of video paths and their creation dates
    """
    # Initialize a dictionary to store the video paths and their creation dates
    video_creation_dates = {}

    # Loop through the videos
    for video in videos:
        # Get the creation date of the video
        creation_date = int(os.path.getctime(video))

        # Add the video path and its creation date to the dictionary
        video_creation_dates[video] = creation_date

    # Return the dictionary
    return video_creation_dates