"""
config.py
---------
All MySQL connection settings live here in ONE place.
If your MySQL username / password / host is different, change it here only.
Every other file imports DB_CONFIG from this file.
"""

DB_CONFIG = {
    "host": "localhost",
    "user": "your_mysql_username_here",        
    "password": "your_mysql_password_here", 
    "database": "travel_agent_db"
}

# Default budget split used ONLY when the user does not customise the split.
# These are percentages of the total budget and must add up to 100.
DEFAULT_BUDGET_SPLIT = {
    "transit": 30,   # flights / trains / buses to reach the destination
    "stay": 40,       # hotel cost
    "food": 20,       # food cost
    "misc": 10        # shopping, local sight-seeing tickets, emergencies etc.
}
