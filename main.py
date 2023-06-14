"""
File: main.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains the main function of the program.
    Running this file will search for Valorant VODs in the directory specified in VOD_DIR, filter out short videos, filter out videos that are more than a week old, 
    filter out videos that are already in the excel file, get the match data for each match, upload the videos to YouTube, and write the matches to the excel file.
"""

from utils import configure, getGameResult, getRankBeforeMatch, get_pairings
from videoUtils import search_for_mp4_files, filter_out_short_videos, filter_out_old_videos, get_video_creation_dates
from timeUtils import utc_to_unix, utc_to_date, unix_to_cst
from excelSpreadsheet import ExcelSpreadsheet
from youtube_api import uploadGamesToYoutube
from schemas.excelMatchEntry import ExcelMatchEntry
import os
import time

VOD_DIR = r"C:\Users\Nikita\Videos\Overwolf\Outplayed\Valorant"
PATH_TO_EXCEL_FILE = os.path.dirname(os.path.abspath(__file__)) + "\\matches.xlsx"

def main():
    # Configure the program
    configure()

    # Search for MP4 files in the directory
    mp4_files = search_for_mp4_files(VOD_DIR)

    # Filter out short videos for comp matches
    minVideoLength = 20 * 60 # 20 minutes
    mp4_files = filter_out_short_videos(mp4_files, minVideoLength)

    # Filter out videos that are more than a week old
    minCreationDate = time.time() - (60 * 60 * 24 * 7) # 7 days
    mp4_files = filter_out_old_videos(mp4_files, minCreationDate)

    # Filter out videos already accounted for(in the excel file)
    excelFile = ExcelSpreadsheet(PATH_TO_EXCEL_FILE)
    excelFile.open()
    mp4_files = excelFile.filterOutProcessedMatches(mp4_files)

    # Check if there are any videos left to process
    if len(mp4_files) == 0:
        print("No videos left to process")
        exit()
    
    videoDates = get_video_creation_dates(mp4_files)
    print("###################\n### VIDEO DATES ###\n###################")
    print(videoDates)
    print()

    pairings = get_pairings(videoDates, gameMode="competitive")

    print("#################################\n### Matches with local videos ###\n#################################")
    for pair in pairings:
        print(f"Match ID: {pair['match_data']['meta']['id']}")
        print(f"Video path: {pair['video_path']}")
        print(f"Match date in UNIX: {utc_to_unix(pair['match_data']['meta']['started_at'])}")
        print(f"Match date in UTC: {pair['match_data']['meta']['started_at']}")
        print(f"Match date in CST: {unix_to_cst(utc_to_unix(pair['match_data']['meta']['started_at']))}")
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    # Get the match data for each match
    matches = []
    for pair in pairings:
        matchId = pair["match_data"]["meta"]["id"]
        date = utc_to_date(pair['match_data']['meta']['started_at'])
        matchResult, score = getGameResult(pair["match_data"])
        agent = pair["match_data"]["stats"]["character"]["name"]
        gameMap = pair["match_data"]["meta"]["map"]["name"]
        rank = getRankBeforeMatch(pair["match_data"]["meta"]["id"])
        YTLink = None
        localPath = pair['video_path']
        matchEntry = ExcelMatchEntry(matchId, date, matchResult, score, agent, gameMap, rank, YTLink, localPath)
        matches.append(matchEntry)

    
    # Upload the videos to YouTube
    print()
    print("Uploading videos to YouTube...")
    matches = uploadGamesToYoutube(matches)
    
    # Write the matches to the excel file
    excelFile.writeMatchesToExcel(matches)

if __name__ == "__main__":
    main()
