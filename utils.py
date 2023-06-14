"""
File: utils.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains utility functions for the program,
    such as configuring the program, getting pairings of local videos and match data, and getting the result of a match.
"""

import time
from timeUtils import utc_to_unix
from valorant_api import get_matchlist, get_match
from schemas.valorantData import ValorantData
from dotenv import load_dotenv


def configure():
    """Configure the program by laoding the .env file variables and saving percistent data to data.json"""
    load_dotenv()
    data = ValorantData()
    if not data.valid():
        gameName = input("Enter your Valorant account name: ")
        tagLine = input("Enter your Valorant account tagline: ")
        valRegion = input("Enter your Valorant region (NA, EU, AP, BR, KR, LATAM): ")
        data.update(gameName=gameName, tagLine=tagLine, reigon=valRegion)
        data.writeToDisk()


def compare_matchlist_with_video_dates(matchlist, localVideoDates, time_threshold=60 * 5):
    """Compare the matchlist with the video dates

    Args:
        matchlist (list[dict]): Matchlist to compare
        localVideoTimes (dict[str, int]): Dictionary of video paths and their creation dates
        time_threshold (int, optional): Time threshold for comparing video creation time with match start time in seconds. Defaults to 60 * 5 (5 minutes).

    Returns:
        list[dict]: List of pairings of local videos and match data in the following schema: {"video_path": str, "match_data": dist}"}
    """
    # Initialize a list to store the matches that were found
    found_pairings = []

    # Loop through the matches in the matchlist
    for match in matchlist:
        # Get match ID
        match_id = match["meta"]["id"]
        # Get the match date
        match_date = utc_to_unix(match["meta"]["started_at"])

        # Loop through the local videos
        for video_path, video_date in localVideoDates.items():
            # Check if the video date is close to the match date (within 5 minute)
            if abs(video_date - match_date) < time_threshold:
                pairEntry = {"video_path": video_path, "match_data": match}
                # Add the match to the found matches
                found_pairings.append(pairEntry)

    # Return the found matches
    return found_pairings


def get_pairings(localVideoDates, gameMode=None, pageSize=10, time_threshold=60 * 5):
    """Get the pairings of local videos and corresponding match data from Valorant API

    Args:
        localVideoDates (dict[str, int]): Dictionary of video paths and their creation dates\n
        gameMode (str, optional): Game mode to get matches from. Defaults to None.\n
        time_threshold (int, optional): Time threshold for comparing video creation time with match start time in seconds. Defaults to 60 * 5 (5 minutes).\n
    
    Returns:
        list[dict]: List of pairings of local videos and match data in the following schema: {"video_path": str, "match_data": dist}"}
    """
    total_pairings = []

    # Get saved player data
    valData = ValorantData()
    
    oldest_local_video_date = min(localVideoDates.values())
    oldest_match_date = time.time()
    page = 1

    # While the oldest local video date is older than the oldest match date -> keep requesting matchlist
    while oldest_local_video_date < oldest_match_date:
        # Request the matchlist from the API
        matchlist = get_matchlist(valData.gameName, valData.tagLine, valData.region, size=pageSize, page=page, game_mode=gameMode)
        page += 1
        if matchlist is None:
            # API error, cannot continue execution
            print("Error: Matchlist not found")
            exit()
        # print("\t### Matches from API Call ###")
        # print(matchlist)
        
        # get the oldest match date from the matchlist (last match in the list)
        returnedEntries = matchlist["results"]["returned"]
        oldest_match_date = utc_to_unix(matchlist["data"][returnedEntries - 1]["meta"]["started_at"])
        
        # Compare the matchlist with the video dates
        pairings = compare_matchlist_with_video_dates(matchlist["data"], localVideoDates, time_threshold=time_threshold)

        # Add the pairings to the total pairings
        total_pairings.extend(pairings)

        # Check if API reached the end of available matches
        if returnedEntries == matchlist["results"]["after"]:
            # Reached the end of available matches
            break
    
    return total_pairings


def getGameResult(match_data):
    """Get the result of the match from the match data

    Args:
        match_data (dict): Match data from the API

    Returns:
        tuple: Result of the match and score. 
        Schema: ("result": str, "score": str) where result is in {"Win", "Loss", "Draw"} and score is in format "13-4" where the first number is the player team score and the second number is the enemy team score.
    """
    # Read player's team from the match data
    player_team = match_data["stats"]["team"]

    if player_team == "Red":
        # Player is on the red team
        # Read the score from the match data
        player_score = match_data["teams"]["red"]
        enemy_score = match_data["teams"]["blue"]
    else:
        # Player is on the blue team
        # Read the score from the match data
        player_score = match_data["teams"]["blue"]
        enemy_score = match_data["teams"]["red"]

    # Check if the player won
    if player_score > enemy_score:
        # Player won
        result = "Win"
    elif player_score < enemy_score:
        # Player lost
        result = "Loss"
    else:
        # Draw
        result = "Draw"

    score = f"{player_score}-{enemy_score}"
    return (result, score)


def getRankBeforeMatch(match_id : str):
    """Get the rank of the player before specified match using Valorant API

    Args:
        match_id (str): ID of the match to get the rank from

    Returns:
        str: Rank of the player before the match
    """
    # Get the match data
    match_data = get_match(match_id)
    if match_data is None:
        # API error, cannot continue execution
        print(f"Error: MatchID: {match_id} - Match data not found")
        exit()
    
    # Retrive player's name and tagline from the saved data
    valData = ValorantData()

    # Get the player's rank before the match
    for player in match_data["data"]["players"]["all_players"]:
        if player["name"] == valData.gameName and player["tag"] == valData.tagLine:
            # Found the player
            return player["currenttier_patched"]
    
    # Player not found in the match data
    return None

