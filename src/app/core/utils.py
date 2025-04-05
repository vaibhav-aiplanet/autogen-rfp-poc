import datetime


def utc_now():
    """
    Return a timezone aware datetime object
    """
    tz = datetime.timezone.utc
    return datetime.datetime.now(tz)


async def get_user_from_request():
    """
    Function to get the current active user from the authenticated request.

    Returns:
        dict: The user data if user is active.
    """
    return {
        "sub": "97ac7304-009f-4a50-91f8-d9dd79209dad",
        "max_folder": 3,
    }
