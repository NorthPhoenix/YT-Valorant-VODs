"""
File: valorant_api.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains functions for calling the Valorant API.
"""

import requests

VALORANT_API_URL_MATCHLIST = "https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{region}/{name}/{tag}"
VALORANT_API_URL_MATCH = "https://api.henrikdev.xyz/valorant/v2/match/{matchId}"


def get_matchlist(name : str, tag : str, valRegion : str, size=None, page=None, game_mode=None):
    """Call api to get the matchlist of the Valorant account py its name and tagline

    Args:
        name (str): name of the Riot account\n
        tag (str): tagline of the Riot account\n
        size (int, optional): Number of matches to get. Defaults to 1.\n
        game_mode (str, optional): Game mode to get matches from. Defaults to None.\n
    """
    print("### API CALL | Getting matchlist ###")

    # Contstruct URL
    url = VALORANT_API_URL_MATCHLIST.format(region=valRegion, name=name, tag=tag)

    # Add query parameters
    params = {}
    if size is not None:
        params["size"] = size
    if page is not None:
        params["page"] = page
    if game_mode is not None:
        params["mode"] = game_mode


    # Make the request
    response = requests.get(url, params=params)

    # Check if the request was successful
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return None
    
    # Return the response
    return response.json()


def get_match(match_id : str):
    """Get the match data from the API

    Args:
        match_id (str): ID of the match to get

    Returns:
        dict: Match data
    """
    print("### API CALL | Getting match ###")

    # Contstruct URL
    url = VALORANT_API_URL_MATCH.format(matchId=match_id)

    # Make the request
    response = requests.get(url)

    # Check if the request was successful
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return None
    
    # Return the response
    return response.json()



# Testing
# if __name__ == "__main__":
#     name = "Yukia"
#     tag = "SNOW"
#     valRegion = "NA"

#     matchlist = get_matchlist(name=name, tag=tag, valRegion=valRegion, size=10, page=11)
#     if matchlist is None:
#         # API error, cannot continue execution
#         print("Error: Matchlist not found")
#         exit()
    
#     print(matchlist)