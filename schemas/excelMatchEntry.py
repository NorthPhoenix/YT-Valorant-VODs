"""
File: excelMatchEntry.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains the ExcelMatchEntry class which is used to store the data for a single match for later use in writing data to an Excel spreadsheet.
"""

from enum import Enum

class ExcelMatchEntryOrder(Enum):
    """Order of columns in the Excel spreadsheet."""
    matchId = 0
    date = 1
    matchResult = 2
    score = 3
    agent = 4
    map = 5
    rank = 6
    YTLink = 7
    localPath = 8

# This is used to print the titles of the columns in the Excel spreadsheet
printableTitles = {
    "matchId" : "Riot Match ID", 
    "date" : "Date", 
    "matchResult" : "Match Result", 
    "score" : "Score", 
    "agent" : "Agent", 
    "map" : "Map", 
    "rank" : "Rank", 
    "YTLink" : "YouTube Link", 
    "localPath" : "Local Path"
    }

class ExcelMatchEntry:
    def __init__(self, matchId : int, date : str, matchResult : str, score : str, agent : str, map : str, rank : str, YTLink : str = None, localPath : str = None):
        self.matchId = matchId
        self.date = date
        self.matchResult = matchResult
        self.score = score
        self.agent = agent
        self.map = map
        self.rank = rank
        self.YTLink = YTLink
        self.localPath = localPath

    def asTuple(self) -> tuple:
        """Return the ExcelMatchEntry as a tuple in the order of ExcelMatchEntryOrder"""
        result = ()
        for i in range(len(ExcelMatchEntryOrder)):
            result += tuple([self.__dict__[ExcelMatchEntryOrder(i).name]])
        return result
    
    def getPrintableTitlesInOrder() -> list[str]:
        """Return a list of titles of the columns in the Excel spreadsheet in the order of ExcelMatchEntryOrder"""
        result = []
        for i in range(len(ExcelMatchEntryOrder)):
            result.append(printableTitles[ExcelMatchEntryOrder(i).name])
        return result
    

# Testing
# if __name__ == "__main__":
#     matchEntry = ExcelMatchEntry(1, "2021-05-15", "Win", "13-4", "Brimstone", "Bind", "Gold", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "C:\\Users\\user\\Desktop\\test.mp4")
#     print(matchEntry.asTuple())
#     print(ExcelMatchEntry.getPrintableTitlesInOrder())