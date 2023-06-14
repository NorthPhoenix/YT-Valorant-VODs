"""
File: valorantData.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains the ValorantData class which is used to store the name, tag, and region of the user.
"""

import json

class ValorantData():
    def __init__(self,):
        self.filename = "data.json"
        self.loadFromDisk()

    def writeToDisk(self):
        """Save name, tag, and region to the data.json file"""
        # Open the data.json file for writing
        with open(self.filename, 'w') as f:
            # Write the data back to the file
            data = {"gameName": self.gameName, "tagLine": self.tagLine, "valRegion": self.region}
            json.dump(data, f)

    def loadFromDisk(self):
        """Load name, tag, and region from the data.json file"""
        # Open the data.json file for reading
        try:
            with open(self.filename, 'r') as f:
                # Load the data from the file
                data = json.load(f)
                self.gameName = data["gameName"]
                self.tagLine = data["tagLine"]
                self.region = data["valRegion"]
        except Exception:
            self.gameName = None
            self.tagLine = None
            self.region = None
    
    def update(self, gameName:str=None, tagLine:str=None, reigon:str=None):
        """Update the passed name, tag, or region"""
        if gameName is not None:
            self.gameName = gameName
        if tagLine is not None:
            self.tagLine = tagLine
        if reigon is not None:
            self.region = reigon


    def valid(self):
        """Check if loaded name, tag, and region are not None"""
        if self.gameName is None or self.tagLine is None or self.region is None:
            return False
        return True