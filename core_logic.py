"""
core_logic.py
-------------
All the "thinking" of the travel agent lives here:
  - splitting the total budget into transit / stay / food / misc
  - searching the MySQL database for destinations that fit the budget
  - saving and loading favourites for a user

The GUI file (main.py) calls these functions -- it does not talk to
MySQL directly. This keeps the database logic and the screen logic
separate, which makes the program much easier to read and debug.
"""

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, DEFAULT_BUDGET_SPLIT
from api_utils import convert_to_inr


def connect_db():
    """
    Opens a connection to the travel_agent_db database.
    Raises a friendly error if MySQL is not reachable, so the caller
    can show a message box instead of the program crashing.
    """
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as error:
        raise ConnectionError(
            f"Could not connect to MySQL. Is the server running and are "
            f"the details in config.py correct?\nDetails: {error}"
        )


# ---------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------

def get_or_create_user(cursor, connection, username):
    """
    Looks up a username. If it doesn't exist yet, creates it.
    Returns the user_id either way.
    """
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty.")

    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
    connection.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------
# BUDGET SPLITTING
# ---------------------------------------------------------------------

def calculate_budget_split(total_budget, transit_pct=None, stay_pct=None,
                            food_pct=None, misc_pct=None):
    """
    Splits total_budget into 4 amounts (transit, stay, food, misc).
    If the user does not provide percentages, DEFAULT_BUDGET_SPLIT is used.
    All 4 percentages, if given, must add up to 100.
    Returns a dictionary, e.g. {"transit": 50000, "stay": 60000, ...}
    """
    if total_budget <= 0:
        raise ValueError("Total budget must be a positive number.")

    if transit_pct is None and stay_pct is None and food_pct is None and misc_pct is None:
        split_pct = DEFAULT_BUDGET_SPLIT
    else:
        # If the user customised the split, every field must be given.
        if None in (transit_pct, stay_pct, food_pct, misc_pct):
            raise ValueError("If customising the split, all four percentages are required.")
        total_pct = transit_pct + stay_pct + food_pct + misc_pct
        if abs(total_pct - 100) > 0.01:
            raise ValueError(f"Percentages must add up to 100 (got {total_pct}).")
        split_pct = {"transit": transit_pct, "stay": stay_pct,
                     "food": food_pct, "misc": misc_pct}

    return {
        "transit": total_budget * split_pct["transit"] / 100,
        "stay": total_budget * split_pct["stay"] / 100,
        "food": total_budget * split_pct["food"] / 100,
        "misc": total_budget * split_pct["misc"] / 100,
    }


# ---------------------------------------------------------------------
# DESTINATION SEARCH
# ---------------------------------------------------------------------

def search_destinations(cursor, days, travellers, budget_split,
                         region=None, dest_type=None):
    """
    Finds every destination that fits inside the user's budget split,
    for the given number of days and travellers.

    Cost model (kept deliberately simple for a school project):
      - transit_total = transit_cost_per_person * travellers
      - stay_total     = stay_cost_per_night * days
                          (one hotel room is assumed to sleep 2 travellers)
      - food_total     = food_cost_per_day * days * travellers
      - misc_total     = misc_cost_per_day * days * travellers

    Each of these 4 totals must fit inside the matching slice of the
    user's budget split (transit_total <= budget_split['transit'], etc).
    All destination costs are already stored in INR, so no currency conversion is needed here.

    Returns a list of dictionaries, one per matching destination, sorted
    by total cost (cheapest first). Each dictionary also contains the
    destination's hotels, local sight-seeing spots and "why recommended"
    reasons.
    """
    # All destination, hotel and sightseeing prices are now stored in INR.
    # Currency conversion is therefore not needed during destination search.
    usd_to_inr_rate = 1.0
    is_live_rate = None

    query = "SELECT * FROM destinations WHERE 1=1"
    params = []
    if region:
        query += " AND region = %s"
        params.append(region)
    if dest_type:
        query += " AND dest_type = %s"
        params.append(dest_type)

    cursor.execute(query, tuple(params))
    columns = [col[0] for col in cursor.description]
    all_destinations = [dict(zip(columns, row)) for row in cursor.fetchall()]

    rooms_needed = max(1, -(-travellers // 2))  # ceiling division, 2 travellers per room

    matches = []
    for dest in all_destinations:
        rate = usd_to_inr_rate
        transit_total = convert_to_inr(dest["transit_cost_per_person"] * travellers, dest["currency"], rate)
        stay_total = convert_to_inr(dest["stay_cost_per_night"] * days * rooms_needed, dest["currency"], rate)
        food_total = convert_to_inr(dest["food_cost_per_day"] * days * travellers, dest["currency"], rate)
        misc_total = convert_to_inr(dest["misc_cost_per_day"] * days * travellers, dest["currency"], rate)

        fits = (transit_total <= budget_split["transit"] and
                stay_total <= budget_split["stay"] and
                food_total <= budget_split["food"] and
                misc_total <= budget_split["misc"])

        if fits:
            dest["transit_total_inr"] = round(transit_total, 2)
            dest["stay_total_inr"] = round(stay_total, 2)
            dest["food_total_inr"] = round(food_total, 2)
            dest["misc_total_inr"] = round(misc_total, 2)
            dest["grand_total_inr"] = round(
                transit_total + stay_total + food_total + misc_total, 2)
            dest["exchange_rate_is_live"] = is_live_rate

            cursor.execute(
                "SELECT hotel_name, price_per_night, rating FROM hotels WHERE dest_id = %s",
                (dest["dest_id"],))
            dest["hotels"] = cursor.fetchall()

            cursor.execute(
                "SELECT spot_name, local_travel_cost FROM local_spots WHERE dest_id = %s",
                (dest["dest_id"],))
            dest["local_spots"] = cursor.fetchall()

            dest["why_recommended"] = get_recommendation_reasons(dest)

            matches.append(dest)

    matches.sort(key=lambda d: d["grand_total_inr"])

    return matches


def get_all_regions(cursor):
    """Returns a sorted list of every distinct region in the database (for a dropdown)."""
    cursor.execute("SELECT DISTINCT region FROM destinations ORDER BY region")
    return [row[0] for row in cursor.fetchall()]


def get_recommendation_reasons(dest):
    """
    Builds a short list of plain-English reasons explaining why a
    destination was recommended. This is rule-based only (no AI) --
    every reason below comes from a simple, explainable check.
    """
    reasons = ["Fits your budget"]

    hotels = dest.get("hotels") or []
    if hotels:
        average_rating = sum(hotel[2] for hotel in hotels) / len(hotels)
        if average_rating >= 4.0:
            reasons.append("Excellent hotel ratings")

    if dest.get("dest_type") == "domestic":
        reasons.append("Popular domestic getaway")
    else:
        reasons.append("Popular international destination")

    return reasons


# ---------------------------------------------------------------------
# HOTEL RECOMMENDATION ENGINE
# ---------------------------------------------------------------------

def recommend_hotels(hotels):
    """
    Scores the hotels for one destination and picks out a small set of
    "badges" to highlight before showing the complete hotel list.

    hotels: list of (hotel_name, price_per_night, rating) tuples, exactly
    as already returned by the 'hotels' table query in search_destinations.

    Two simple, explainable scores are used:
      - overall_score = (rating * 25) - (price / 150)   -- rating-led,
        used for "Best Overall": a great hotel that doesn't ignore price.
      - value_score    = (rating * 15) - (price / 50)    -- price-led,
        used for "Best Value": how much rating you get per rupee/dollar.

    Returns a dict of badge -> hotel tuple:
        "Best Overall", "Best Budget", "Highest Rated", "Best Value"
    or an empty dict if the destination has no hotels at all. If a
    destination only has 1-2 hotels, the same hotel can legitimately win
    more than one badge -- the GUI decides how to display that.
    """
    if not hotels:
        return {}

    def overall_score(hotel):
        _, price, rating = hotel
        return (rating * 25) - (price / 150)

    def value_score(hotel):
        _, price, rating = hotel
        return (rating * 15) - (price / 50)

    return {
        "Best Overall": max(hotels, key=overall_score),
        "Best Budget": min(hotels, key=lambda h: h[1]),
        "Highest Rated": max(hotels, key=lambda h: h[2]),
        "Best Value": max(hotels, key=value_score),
    }


# ---------------------------------------------------------------------
# FAVOURITES
# ---------------------------------------------------------------------

def add_favourite(cursor, connection, user_id, destination):
    """
    Saves a destination (with the exact prices the user was shown) as a
    favourite for this user, so they can revisit the whole package later.
    """
    cursor.execute("""
        INSERT INTO favourites
            (user_id, dest_id, days, travellers, total_budget,
             transit_cost, stay_cost, food_cost, misc_cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id, destination["dest_id"], destination["days"], destination["travellers"],
        destination["grand_total_inr"], destination["transit_total_inr"],
        destination["stay_total_inr"], destination["food_total_inr"], destination["misc_total_inr"]
    ))
    connection.commit()


def get_favourites(cursor, user_id):
    """Returns every favourite package saved by this user, most recent first."""
    cursor.execute("""
        SELECT f.fav_id, d.name, f.days, f.travellers, f.total_budget,
               f.transit_cost, f.stay_cost, f.food_cost, f.misc_cost, f.saved_on
        FROM favourites f
        JOIN destinations d ON f.dest_id = d.dest_id
        WHERE f.user_id = %s
        ORDER BY f.saved_on DESC
    """, (user_id,))
    return cursor.fetchall()


def remove_favourite(cursor, connection, fav_id):
    """Deletes one saved favourite by its id."""
    cursor.execute("DELETE FROM favourites WHERE fav_id = %s", (fav_id,))
    connection.commit()
