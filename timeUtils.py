"""
File: timeUtils.py
Author: Nikita Istomin
Creatin Date: 6/13/2023
Description: This file contains functions for converting between Unix timestamps and ISO 8601 time strings.
"""

from datetime import datetime
import pytz


def utc_to_unix(time: str) -> float:
    """Converts an ISO 8601 time string to a Unix timestamp

    Args:
        time (str): ISO 8601 time string in UTC

    Returns:
        int: Unix timestamp
    """
    # Parse the ISO 8601 time string

    # Convert the parsed time to a Unix timestamp
    unix_time = datetime.fromisoformat(time).timestamp()

    # Return the Unix timestamp
    return unix_time

def unix_to_utc(time: float) -> str:
    """Converts a Unix timestamp to an ISO 8601 time string

    Args:
        time (int): Unix timestamp

    Returns:
        str: ISO 8601 time string in UTC
    """
    # Convert the Unix timestamp to a datetime object
    dt = datetime.fromtimestamp(time, tz=pytz.UTC)

    # Convert the datetime object to an ISO 8601 time string
    iso_time = dt.isoformat()

    # Return the ISO 8601 time string
    return iso_time

def unix_to_cst(time: float) -> str:
    """Converts a Unix timestamp to a CST time string

    Args:
        time (int): Unix timestamp

    Returns:
        str: CST time string
    """

    # Create a datetime object from the Unix timestamp in UTC timezone
    dt_utc = datetime.fromtimestamp(time, tz=pytz.UTC)

    # Convert the datetime object to CST timezone
    cst_timezone = pytz.timezone('US/Central')
    dt_cst = dt_utc.astimezone(cst_timezone)

    # Format the CST datetime as a string
    cst_time = dt_cst.isoformat()

    # Return the CST time string
    return cst_time


def utc_to_date(time: str) -> str:
    """Converts an ISO 8601 time string to a date string

    Args:
        time (str): ISO 8601 time string in UTC

    Returns:
        str: Date string
    """
    # Parse the ISO 8601 time string
    date_d = datetime.fromisoformat(time).date()

    # Return the date string
    return date_d.strftime("%b %d, %Y")

# Testing
# if __name__ == "__main__":
#     # Testing iso_to_unix and unix_to_cst
#     # iso_time = "2023-05-17T08:54:58.101Z"
#     # print(f"{iso_time} to ", end="")
#     # unix_time = iso_to_unix(iso_time)
#     # print(f"{unix_time} to ", end="")
#     # cst_time = unix_to_cst(unix_time)
#     # print(cst_time)

#     unix_ts = 1684314203
#     print(f"UNIX: {unix_ts}")
#     print(f"ISO UTC: {unix_to_utc(unix_ts)}")
#     print(f"ISO CST: {unix_to_cst(unix_ts)}")