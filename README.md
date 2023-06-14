# YouTube Valorant VODs
## Summary
This program is created to automate the process of uploading game recordings for ranked Valorant matches to YouTube for personal use.

This program will search for videos in the directory specified in `VOD_DIR`, filter out short videos and videos that are more than a week old, get the associated Valorant game data for each video according to video creation time, upload the videos to YouTube, and write the game data to the excel file.

## How to run
1) Install pip requirements.
```
pip install -r "requirements.txt"
```
2) Create Google OAuth 2.0 Desktop Credentials and add them to the project at `\client_secrets.json`
   - Go to [console.cloud.google.com/apis/credentials](console.cloud.google.com/apis/credentials) and click on "Create Credentials" -> "OAuth client ID"
   - After credentials are created, download credentials file, rename it to "client_secrets.json", and place it in the root of the project.
3) Run `main.py` script.
