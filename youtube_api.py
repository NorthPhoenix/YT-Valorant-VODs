"""
File: youtube_api.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains functions for working with the YouTube API.
"""

# Standard Imports
import os
import pprint
import json
from time import sleep
from typing import Literal
from random import random
from copy import copy
from multiprocessing.pool import AsyncResult
from multiprocessing.managers import BaseManager
from multiprocessing.managers import BaseProxy
import multiprocessing as mp

# Internal Imports
from schemas.excelMatchEntry import ExcelMatchEntry

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

# Errors and Exceptions
from google.auth.exceptions import RefreshError
from oauthlib.oauth2.rfc6749.errors import AccessDeniedError
from googleapiclient.errors import HttpError

class ExceptionHistory(Exception):
    """Exception to store a list of exceptions"""
    def __init__(self, message:str, exceptions:list[Exception]):
        super().__init__(message)
        self.history = exceptions

# Constants
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = "client_secrets.json"

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

VODs_playlist_name = "Valorant VODs"

# Multiprocessing manager for writing to the excel file from multiple processes
# custom manager to support custom classes
class CustomManager(BaseManager):
    # nothing
    pass



#####################
#### DECORATORS #####
#####################

def retryAPIWithDelay(runs:int, delay:int):
    """Decorator to run the api function `runs` total times if it fails with a server error.
    
    Args:
        `runs` (`int`): The number of times to run the api function if it fails.
        `delay` (`int`): The delay in milliseconds between each run of the api function.
        
    Returns:
        `function`: The decorated function
    
    Raises:
        `ExceptionHistory`: If the api function fails `runs` times in a row with a server error (err.resp.status >= 500).
        `googleapiclient.errors.HttpError`: If the api function fails for non server related reasons (err.resp.status < 500)"""
    def decorator(apiFunc):
        def wrapper(*args, **kwargs):
            errorHistory = []
            for i in range(runs):
                try:
                    return apiFunc(*args, **kwargs)
                except HttpError as e:
                    if e.resp.status < 500:
                        raise e # Don't retry if the error is not a server error
                    errorHistory.append(e)
                sleep(delay / 1000) # Convert millisecond delay to seconds
                if i != runs - 1:
                    print(f"Retrying {apiFunc.__name__}...")
            raise ExceptionHistory("Failed after " + str(runs) +" runs", errorHistory)
        return wrapper
    return decorator




#####################
#### CREDENTIALS ####
#####################

def saveCredentials(credentials:Credentials):
    """Save the credentials to the credentials.json file
    
    Args:
        `credentials` (`google.oauth2.credentials.Credentials`): The credentials to save"""
    # Open the credentials.json file for writing
    with open('credentials.json', 'w') as f:
        # Write the credentials to the file
        json.dump(json.loads(credentials.to_json()), f)


def requestCredentials(scopes : list[str], secrets_file : str):
    """Request credentials from the user by opening a browser window and prompting the user to login to their google account
    
    Args:
        `scopes` (`list[str]`): Google API scopes to request from the user
        `secrets_file` (`str`): Path to the client_secrets_file file
    
    Returns:
        `google.oauth2.credentials.Credentials`: The credentials object
        
    Raises:
        `oauthlib.oauth2.rfc6749.errors.AccessDeniedError`: If the user denies access to the requested scopes
        """
    # Create the flow using the client_secrets_file file
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        secrets_file, scopes)
    # Request credentials from the user
    credentials = flow.run_local_server() # Might raise an AccessDeniedError
    return credentials


def refreshCredentials(credentials : Credentials):
    """Refresh the credentials

    Args:
        `credentials` (`google.oauth2.credentials.Credentials`): The credentials to refresh

    Raises `google.auth.exceptions.RefreshError` if the credentials don't have a refresh token
    """
    if credentials.refresh_token:
        print("Refreshing credentials")
        credentials.refresh(Request())
    else:
        raise Exception("Credentials don't have a refresh token")


def getAndSaveCredentials(scopes : list[str], client_secrets_file : str):
    """Get the correct credentials from the credentials.json file or request them from the user if they don't exist.
        Save the credentials to the credentials.json file if they are requested from the user.
    
    Args:
        `scopes` (`list[str]`): Google API scopes to request from the user
        `secrets_file` (`str`): Path to the client_secrets_file file
        
    Returns:
        `google.oauth2.credentials.Credentials`: The credentials object
        
    Raises:
        `oauthlib.oauth2.rfc6749.errors.AccessDeniedError`: If the user denies access to the requested scopes"""
    # Check if there are no saved credentials
    if not os.path.exists('credentials.json'):
        # Request new credentials
        print("No saved credentials. Requesting new credentials")
        credentials = requestCredentials(scopes, client_secrets_file)
        # Save the credentials
        saveCredentials(credentials)
        return credentials
    # Get the saved credentials
    with open('credentials.json', 'r') as f:
        credentials = Credentials.from_authorized_user_info(json.load(f))
    # Check if scopes are valid
    if not all(scope in credentials.scopes for scope in scopes):
        print("Invalid saved credentials. Requesting new credentials")
        credentials = requestCredentials(scopes, client_secrets_file)
        # Save the credentials
        saveCredentials(credentials)
        return credentials
    # Check if saved credentials are valid
    if not credentials.valid:
        # Refresh the credentials if possible
        try:
            refreshCredentials(credentials)
            return credentials
        except RefreshError as e:
            print("Refresh error. Requesting new credentials")
            credentials = requestCredentials(scopes, client_secrets_file)
            # Save the credentials
            saveCredentials(credentials)
            return credentials
        except Exception as e:
            print(f"Error: {e}. Requesting new credentials")
            credentials = requestCredentials(scopes, client_secrets_file)
            # Save the credentials
            saveCredentials(credentials)
            return credentials
    return credentials




#####################
#### API QUERIES ####
#####################

@retryAPIWithDelay(runs=3, delay=300)
def queryPlaylistsList(part:list[Literal["contentDetails", "id", "localizations", "player", "snippet", "status"]]=["snippet"], 
                        mine:bool=None, 
                        channelId:str=None, 
                        id:list[str]=None, 
                        hl:str=None,
                        maxResults:int=5, 
                        onBehalfOfContentOwner:str=None,
                        onBehalfOfContentOwnerChannel:str=None,
                        pageToken:str=None,) -> dict | None:
    """Returns a collection of playlists that match the API request parameters. 
    For example, you can retrieve all playlists that the authenticated user owns, or you can retrieve one or more playlists by their unique IDs.
    
    Args:
        Required parameters:
            `part` (`list[Literal["contentDetails", "id", "localizations", "player", "snippet", "status"]]`): 
                The part parameter specifies a list of one or more playlist resource properties that the API response will include. 
                Defaults to ["snippet"].
        Filters (specify exactly one of the following parameters):
            `mine` (`bool`): 
                This parameter can only be used in a properly authorized request. 
                Set this parameter's value to true to retrieve a feed of the authenticated user's playlists. 
                Defaults to None.
            `channelId` (`str`): 
                The channelId parameter specifies a unique YouTube channel ID. The API will then return a list of that channel's playlists. 
                Defaults to None.
            `id` (`list[str]`): 
                The id parameter specifies a list of the YouTube playlist ID(s) for the resource(s) that are being retrieved. In a playlist resource, 
                the id property specifies the playlist's YouTube playlist ID. 
                Defaults to None.
        Optional parameters:
            `hl` (`str`): 
                The hl parameter instructs the API to retrieve localized resource metadata for a specific application language that the YouTube website supports. 
                The parameter value must be a language code included in the list returned by the i18nLanguages.list method. 
                Defaults to None.
            `maxResults` (`int`):
                The maxResults parameter specifies the maximum number of items that should be returned in the result set. 
                Acceptable values are 0 to 50, inclusive. 
                Defaults to 5.
            `onBehalfOfContentOwner` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwner parameter indicates that the request's authorization credentials identify a YouTube CMS user who is acting on behalf of the content owner specified in the parameter value. 
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and get access to all their video and channel data, without having to provide authentication credentials for each individual channel. 
                The CMS account that the user authenticates with must be linked to the specified YouTube content owner.
                Defaults to None.
            `onBehalfOfContentOwnerChannel` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwnerChannel parameter specifies the YouTube channel ID of the channel to which a video is being added. 
                This parameter is required when a request specifies a value for the onBehalfOfContentOwner parameter, and it can only be used in conjunction with that parameter. 
                In addition, the request must be authorized using a CMS account that is linked to the content owner that the onBehalfOfContentOwner parameter specifies. 
                Finally, the channel that the onBehalfOfContentOwnerChannel parameter value specifies must be linked to the content owner that the onBehalfOfContentOwner parameter specifies.
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and perform actions on behalf of the channel specified in the parameter value, without having to provide authentication credentials for each separate channel.
                Defaults to None.
            `pageToken` (`str`):
                The pageToken parameter identifies a specific page in the result set that should be returned. 
                In an API response, the nextPageToken and prevPageToken properties identify other pages that could be retrieved.
                Defaults to None.
            
        Returns:
            `dict` | `None`: The API response if the request was successful. None if access denied by the user.
            
        Raises:
            `googleapiclient.errors.HttpError`: If the API request failed for non server related reasons (err.resp.status < 500).
            `ExceptionHistory`: If the API request failed for server related reasons (err.resp.status >= 500)."""
    # Get credentials
    try:
        credentials = getAndSaveCredentials(SCOPES, CLIENT_SECRETS_FILE)
    except AccessDeniedError as e:
        print("Access denied to requested scopes")
        return None
    # Create the youtube api client
    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    # Construct the request for the playlists
    request = youtube.playlists().list(
        part=",".join(part),
        mine=mine,
        channelId=channelId,
        id=",".join(id) if id is not None else None,
        hl=hl,
        maxResults=maxResults,
        onBehalfOfContentOwner=onBehalfOfContentOwner,
        onBehalfOfContentOwnerChannel=onBehalfOfContentOwnerChannel,
        pageToken=pageToken,
    )
    # Execute the request
    response = request.execute()
    # Return the response
    return response

@retryAPIWithDelay(runs=3, delay=300)
def queryPlaylistsInsert(requestBody : dict, 
                    part:list[Literal["contentDetails", "id", "localizations", "player", "snippet", "status"]]=["snippet", "status"],
                    onBehalfOfContentOwner:str=None,
                    onBehalfOfContentOwnerChannel:str=None,) -> dict | None:
    """Creates a playlist and adds it to the authenticated user's channel.
    
    Args:
        Required parameters:
            `requestBody` (`dict`):
                The requestBody object contains an instance of Playlist.
            `part` (`list[Literal["contentDetails", "id", "localizations", "player", "snippet", "status"]]`):
                The part parameter serves two purposes in this operation.
                It identifies the properties that the write operation will set as well as the properties that the API response will include.
                Defaults to ["snippet", "status"].
        Optional parameters:
            `onBehalfOfContentOwner` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwner parameter indicates that the request's authorization credentials identify a YouTube CMS user who is acting on behalf
                of the content owner specified in the parameter value. 
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and get access to all their video and channel data, without having to provide authentication credentials for each individual channel.
                The CMS account that the user authenticates with must be linked to the specified YouTube content owner.
                Defaults to None.
            `onBehalfOfContentOwnerChannel` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwnerChannel parameter specifies the YouTube channel ID of the channel to which a video is being added. 
                This parameter is required when a request specifies a value for the onBehalfOfContentOwner parameter, 
                and it can only be used in conjunction with that parameter. 
                In addition, the request must be authorized using a CMS account that is linked to the content owner that the onBehalfOfContentOwner parameter specifies. 
                Finally, the channel that the onBehalfOfContentOwnerChannel parameter value specifies must be linked to the content owner that the onBehalfOfContentOwner parameter specifies.
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and perform actions on behalf of the channel specified in the parameter value, 
                without having to provide authentication credentials for each separate channel.
                Defaults to None.
            
        Returns:
            `dict` | `None`: The API response if the request was successful. None if access denied by the user.
            
        Raises:
            `googleapiclient.errors.HttpError`: If the API request failed for non server related reasons (err.resp.status < 500).
            `ExceptionHistory`: If the API request failed for server related reasons (err.resp.status >= 500)."""
    # Get credentials
    try:
        credentials = getAndSaveCredentials(SCOPES, CLIENT_SECRETS_FILE)
    except AccessDeniedError as e:
        print("Access denied to requested scopes")
        return None
    # Create the youtube api client
    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    # Construct the request for playlist creation
    request = youtube.playlists().insert(
        body=requestBody,
        part=",".join(part),
        onBehalfOfContentOwner=onBehalfOfContentOwner,
        onBehalfOfContentOwnerChannel=onBehalfOfContentOwnerChannel,
    )
    # Execute the request
    response = request.execute()
    # Return the response
    return response


@retryAPIWithDelay(runs=3, delay=300)
def queryVideosInsert(pathToVideo:str,
                    requestBody : dict, 
                    part:list[Literal["contentDetails", "fileDetails", "id", "liveStreamingDetails", "localizations", "player", "processingDetails", "recordingDetails", "snippet", "statistics", "status", "suggestions", "topicDetails"]]=["snippet", "status"],
                    notifySubscribers:bool=False,
                    onBehalfOfContentOwner:str=None,
                    onBehalfOfContentOwnerChannel:str=None,) -> dict | None:
    """Creates a playlist and adds it to the authenticated user's channel.
    
    Args:
        Required parameters:
            `pathToVideo` (`str`):
                The path to the video to upload.
            `requestBody` (`dict`):
                The requestBody object contains an instance of Playlist.
            `part` (`list[Literal["contentDetails", "id", "localizations", "player", "snippet", "status"]]`):
                The part parameter serves two purposes in this operation.
                It identifies the properties that the write operation will set as well as the properties that the API response will include.
                Defaults to ["snippet", "status"].
        Optional parameters:
            `notifySubscribers` (`bool`):
                The notifySubscribers parameter indicates whether YouTube should send a notification about the new video to users who subscribe to the video's channel. 
                A parameter value of True indicates that subscribers will be notified of newly uploaded videos. 
                However, a channel owner who is uploading many videos might prefer to set the value to False to avoid sending a notification about each new video to the channel's subscribers. 
                Defaults to False.
            `onBehalfOfContentOwner` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwner parameter indicates that the request's authorization credentials identify a YouTube CMS user
                who is acting on behalf of the content owner specified in the parameter value. 
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and get access to all their video and channel data,
                without having to provide authentication credentials for each individual channel. 
                The CMS account that the user authenticates with must be linked to the specified YouTube content owner.
                Defaults to None.
            `onBehalfOfContentOwnerChannel` (`str`):
            This parameter can only be used in a properly authorized request. 
            Note: This parameter is intended exclusively for YouTube content partners.
            The onBehalfOfContentOwnerChannel parameter specifies the YouTube channel ID of the channel to which a video is being added. 
            This parameter is required when a request specifies a value for the onBehalfOfContentOwner parameter, 
            and it can only be used in conjunction with that parameter. 
            In addition, the request must be authorized using a CMS account that is linked to the content owner that the onBehalfOfContentOwner parameter specifies. 
            Finally, the channel that the onBehalfOfContentOwnerChannel parameter value specifies must be linked to the content owner that the onBehalfOfContentOwner parameter specifies.
            This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
            It allows content owners to authenticate once and perform actions on behalf of the channel specified in the parameter value, 
            without having to provide authentication credentials for each separate channel.
            Defaults to None.
            
        Returns:
            `dict` | `None`: The API response if the request was successful. None if access denied by the user.
            
        Raises:
            `googleapiclient.errors.HttpError`: If the API request failed for non server related reasons (err.resp.status < 500).
            `ExceptionHistory`: If the API request failed for server related reasons (err.resp.status >= 500)."""
    # Get credentials
    try:
        credentials = getAndSaveCredentials(SCOPES, CLIENT_SECRETS_FILE)
    except AccessDeniedError as e:
        print("Access denied to requested scopes")
        return None
    # Create the youtube api client
    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    # Construct the request for playlist creation
    request = youtube.videos().insert(
        body=requestBody,
        part=",".join(part),
        media_body=MediaFileUpload(pathToVideo, chunksize=-1, resumable=True),
        notifySubscribers=notifySubscribers,
        onBehalfOfContentOwner=onBehalfOfContentOwner,
        onBehalfOfContentOwnerChannel=onBehalfOfContentOwnerChannel,
    )
    # # Execute the request
    response = resumable_upload(request)
    # Return the response
    return response


def resumable_upload(request, retries=5) -> dict|None:
    """This method implements an exponential backoff strategy to resume a failed upload."""
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            response = request.execute()
            if response is not None:
                if not 'id' in response:
                    print("The upload failed with an unexpected response: %s" % response)
                    return None
                else:
                    return response
        except HttpError as e:
            if e.resp.status >= 500:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
            else:
                raise
        if error is not None:
            print(error)
            retry += 1
            if retry > retries:
                print("No longer attempting to retry.")
                return None
            max_sleep = 2 ** retry
            sleep_seconds = random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            sleep(sleep_seconds)


@retryAPIWithDelay(runs=3, delay=300)
def queryPlaylistItemsInsert(requestBody : dict,
                                part:list[Literal["contentDetails", "id", "snippet", "status"]]=["snippet"],
                                onBehalfOfContentOwner:str=None,) -> dict | None:
    """Adds a resource to a playlist.

    Args:
        Required parameters:
            `requestBody` (`dict`):
                The requestBody object contains an instance of PlaylistItem.
            `part` (`list[Literal["contentDetails", "id", "snippet", "status"]]`):
                The part parameter serves two purposes in this operation.
                It identifies the properties that the write operation will set as well as the properties that the API response will include.
                Defaults to ["snippet"].
        Optional parameters:
            `onBehalfOfContentOwner` (`str`):
                This parameter can only be used in a properly authorized request. 
                Note: This parameter is intended exclusively for YouTube content partners.
                The onBehalfOfContentOwner parameter indicates that the request's authorization credentials identify a YouTube CMS user
                who is acting on behalf of the content owner specified in the parameter value. 
                This parameter is intended for YouTube content partners that own and manage many different YouTube channels. 
                It allows content owners to authenticate once and get access to all their video and channel data, 
                without having to provide authentication credentials for each individual channel. 
                The CMS account that the user authenticates with must be linked to the specified YouTube content owner.
                Defaults to None.
            
        Returns:
            `dict` | `None`: The API response if the request was successful. None if access denied by the user.
            
        Raises:
            `googleapiclient.errors.HttpError`: If the API request failed for non server related reasons (err.resp.status < 500).
            `ExceptionHistory`: If the API request failed for server related reasons (err.resp.status >= 500)."""
    # Get credentials
    try:
        credentials = getAndSaveCredentials(SCOPES, CLIENT_SECRETS_FILE)
    except AccessDeniedError as e:
        print("Access denied to requested scopes")
        return None
    # Create the youtube api client
    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)
    # Construct the request for playlist creation
    request = youtube.playlistItems().insert(
        body=requestBody,
        part=",".join(part),
        onBehalfOfContentOwner=onBehalfOfContentOwner,
    )
    # # Execute the request
    response = request.execute()
    # Return the response
    return response


########################
#### USER FUNCTIONS ####
########################

def getPlaylistIDByName(playlistName : str) -> str | None:
    """Get the playlist ID with the given name
    
    Args:
        `playlistName` (`str`): The name of the playlist to search for
        
    Returns:
        `str | None`: The playlist ID if the playlist is found. "-1" if playlist doesn't exist. None if couldn't get the playlist ID."""
    # Hit the api for the playlists(manage pagination)
    nextPageToken = None
    while True:
        try:
            # Query the playlists
            response = queryPlaylistsList(part=["snippet"], mine=True, maxResults=10, pageToken=nextPageToken)
        except HttpError as e:
            print("Client error while querying playlists")
            pprint.pprint(e)
            return None
        except ExceptionHistory as e:
            print("Server error while querying playlists")
            pprint.pprint(e)
            return None
        if response is None:
            return None
        # Scan the playlists for the playlist with the given name. 
        for playlist in response["items"]:
            if playlist["snippet"]["title"] == playlistName:
                return playlist["id"] # Return the playlist id if the playlist is found
        # Playlist name not found in the current batch of playlists
        # Update the nextPageToken
        if not "nextPageToken" in response:
            break
        nextPageToken = response["nextPageToken"]
    return "-1" # Return "-1" if the playlist doesn't exist


def createPlaylist(playlistName:str, 
                    description:str=None, 
                    privacyStatus:Literal["private", "public", "unlisted"]="unlisted", 
                    tags:list[str]=None, 
                    defaultLanguage:str=None,) -> dict | None:
    """Create a playlist with given parameters
    
    Args:
        `playlistName` (`str`): The name of the playlist to create
        `description` (`str`, optional): The description of the playlist. Defaults to None.
        `privacyStatus` (`Literal["private", "public", "unlisted"]`, optional): The privacy status of the playlist. Defaults to "unlisted".
        `tags` (`list[str]`, optional): The tags of the playlist. Defaults to None.
        `defaultLanguage` (`str`, optional): The default language of the playlist. Defaults to None.

    Returns:
        `str | None`: The playlist ID if the playlist is created successfully. None if the playlist couldn't be created."""
    # Hit the api to create a playlist with the given name
    body = {
        "snippet": {
            "title": playlistName,
            "description": description,
            "tags": tags,
            "defaultLanguage": defaultLanguage,
        },
        "status": {
            "privacyStatus": privacyStatus,
        },
    }
    try:
        playlist = queryPlaylistsInsert(body, part=["snippet", "status"])
    except HttpError as e:
        print("Client error while querying playlists")
        pprint.pprint(e)
        return None
    except ExceptionHistory as e:
        print("Server error while querying playlists")
        pprint.pprint(e)
        return None
    if playlist is None:
        return None
    # Return the playlist id
    return playlist["id"]


def uploadVideo(pathToVideo, title:str=None, description:str=None, tags:list[str]=None, category:str="20", privacyStatus:Literal["private", "public", "unlisted"]="unlisted") -> str | None:
    """Upload a video to youtube
    
    Args:
        `pathToVideo` (`str`): Path to the video to upload
        `title` (`str`, optional): Title of the video. Defaults to None.
        `description` (`str`, optional): Description of the video. Defaults to None.
        `tags` (`list[str]`, optional): Tags of the video. Defaults to None.
        `category` (`str`): Category of the video. Defaults to "20"(Which is "Gaming").
        `privacyStatus` (`Literal["private", "public", "unlisted"]`, optional): Privacy status of the video. Defaults to "unlisted".
        
    Returns:
        `str | None`: The video ID if the video is uploaded successfully. None if the video couldn't be uploaded."""
    # Hit the api to upload the video
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacyStatus,
        },
    }
    try:
        video = queryVideosInsert(pathToVideo, body, part=["snippet", "status"])
    except HttpError as e:
        print("Client error while uploading video")
        pprint.pprint(e)
        return None
    except ExceptionHistory as e:
        print("Server error while uploading video")
        pprint.pprint(e)
        return None
    if video is None:
        return None
    # Return the video id
    return video["id"]


def addVideoToPlaylist(videoID:str, playlistID:str):
    """ Add a video to a playlist

    Args:
        `videoID` (`str`): The ID of the video to add to the playlist
        `playlistID` (`str`): The ID of the playlist to add the video to

    Returns:
        `dict | None`: The API response if the request was successful (playlistItem resource). None if access denied by the user."""
    # Hit the api to add the video to the playlist
    body = {
        "snippet": {
            "playlistId": playlistID,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": videoID,
            },
        },
    }
    try:
        response = queryPlaylistItemsInsert(body)
    except HttpError as e:
        print("Client error while adding video to playlist")
        pprint.pprint(e)
        return None
    except ExceptionHistory as e:
        print("Server error while adding video to playlist")
        pprint.ppprint.pprint(e)
        return None
    return response


def uploadGameToYoutube(game:ExcelMatchEntry, playlistID:str, sharedGames:list[ExcelMatchEntry]):
    # Upload the game to the playlist and get the link to the video
    title = f"{game.agent}, {game.map} | {game.date} | {game.matchResult} {game.score} | {game.rank}"
    print(f"Uploading {title}...")
    videoID = uploadVideo(game.localPath, title=title)
    if videoID is None:
        print(f"Couldn't upload {title}")
        return
    videoLink = f"https://www.youtube.com/watch?v={videoID}"
    print(f"Link to {title}: {videoLink}")
    # Update the game entry with the link to the video
    gameWithLink = copy(game)
    gameWithLink.YTLink = videoLink
    # Add the game to the queue of games with links
    sharedGames.append(gameWithLink)
    # Add the video to the playlist
    print("Adding video to playlist...")
    playlistItem = addVideoToPlaylist(videoID, playlistID)
    if playlistItem is None:
        print("Couldn't add video to playlist")
    else:
        print("Video added to playlist")


def uploadGamesToYoutube(games : list[ExcelMatchEntry]) -> list[ExcelMatchEntry] | None:
    """Upload the given games in parallel to youtube and return the game entries for excel file with the youtube links

    Args:
        `games` (`list[ExcelMatchEntry]`): The list of games to upload to youtube

    Returns:
        `list[ExcelMatchEntry] | None`: The list of games with youtube links if the games were uploaded successfully. None if the games couldn't be uploaded."""
    # Find Valorant VODs playlist
    print("Getting playlist ID...")
    playlistID = getPlaylistIDByName(VODs_playlist_name)
    if playlistID is None:
        # Couldn't get the playlist ID
        return None
    if playlistID == "-1":
        print("Playlist doesn't exist")
        print("Creating playlist...")
        playlistID = createPlaylist(VODs_playlist_name)
    print(f"Playlist ID: {playlistID}")
    # Upload each game to the playlist in parallel
    pool = mp.Pool(mp.cpu_count())
    # register the list with the custom manager
    CustomManager.register('games', list)
    results = [] # List of process results from the pool of processes
    gamesWithLinks = [] # List of games to return
    with CustomManager() as manager: # Create a custom manager to share the list between processes
        sharedGames:BaseProxy = manager.games() # Create a proxy to the list
        for game in games: # Upload each game to the playlist in parallel
            result = pool.apply_async(uploadGameToYoutube, args=(game, playlistID, sharedGames))
            results.append(result)
        pool.close()
        [result.get() for result in results] # Wait for all the processes to finish

        # Get the list of games with links from the shared list
        for game in sharedGames._getvalue(): 
            gamesWithLinks.append(game)
    return gamesWithLinks





# Testing

# def testMainFunctionality():
#     testPlaylistName = "########## Test Playlist ##########"
#     testVideo = r"C:\Users\Nikita\Videos\dead.mp4"
#     print("Getting playlist ID...")
#     playlistID = getPlaylistIDByName(testPlaylistName)
#     if playlistID is None:
#         # Couldn't get the playlist ID
#         return
#     if playlistID == "-1":
#         print("Playlist doesn't exist")
#         print("Creating playlist...")
#         playlistID = createPlaylist(testPlaylistName)
#     print(f"Playlist ID: {playlistID}")
#     print("Uploading video...")
#     videoID = uploadVideo(testVideo, title="Test Video")
#     if videoID is None:
#         print("Couldn't upload video")
#         return
#     print(f"Video ID: {videoID}")
#     print(f"Link: https://www.youtube.com/watch?v={videoID}")
#     print("Adding video to playlist...")
#     playlistItem = addVideoToPlaylist(videoID, playlistID)
#     if playlistItem is None:
#         print("Couldn't add video to playlist")
#     else:
#         print("Video added to playlist")

# def testSharingData():
#     testVideo = r"C:\Users\Nikita\Videos\dead.mp4"
#     testPlaylistName = "########## Test Playlist ##########"

#     print("Getting playlist ID...")
#     playlistID = getPlaylistIDByName(testPlaylistName)
#     if playlistID is None:
#         # Couldn't get the playlist ID
#         return
#     if playlistID == "-1":
#         print("Playlist doesn't exist")
#         print("Creating playlist...")
#         playlistID = createPlaylist(testPlaylistName)
#     print(f"Playlist ID: {playlistID}")
#     print("Uploading video...")
#     games = [ExcelMatchEntry("MatchID", "000-00-00", "Win/Loss", "0-0", "Agent", "Map", "Rank", localPath=testVideo),]
#     pool = mp.Pool(2)
#     # register the list with the custom manager
#     CustomManager.register('games', list)
#     results = []
#     gamesWithLinks = []
#     with CustomManager() as manager:
#         sharedGames:BaseProxy = manager.games()
#         for game in games:
#             result = pool.apply_async(uploadGameToYoutube, args=(game, playlistID, sharedGames))
#             results.append(result)
#         pool.close()
#         [result.get() for result in results]

#         for game in sharedGames._getvalue():
#             gamesWithLinks.append(game)
#     return gamesWithLinks


# if __name__ == "__main__":
#     # testMainFunctionality()

#     # def modList(list):
#     #     list.append(1)

#     # testList = []
#     # print(testList)
#     # modList(testList)
#     # print(testList)

#     games = testSharingData()
#     pprint.pprint(games)

