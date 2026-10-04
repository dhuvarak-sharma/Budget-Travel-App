"""
db_setup.py
-----------
Sets up the travel_agent_db database from scratch.

IMPORTANT (changed behaviour): running this file now ALWAYS wipes every
table and rebuilds them, then reseeds all sample data. This is
intentional so the project always starts from a clean, fully-seeded
database. It means any usernames / favourites saved earlier will be
deleted -- that is expected every time this script runs.
"""

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


def get_connection(with_database=True):
    """
    Opens and returns a connection to MySQL.
    with_database=False is used only the very first time, before the
    'travel_agent_db' database itself exists.
    """
    config = DB_CONFIG.copy()
    if not with_database:
        config.pop("database")
    return mysql.connector.connect(**config)


def create_database():
    """Creates the travel_agent_db database if it does not already exist."""
    connection = get_connection(with_database=False)
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cursor.close()
    connection.close()
    print(f"Database '{DB_CONFIG['database']}' is ready.")


def drop_tables(cursor):
    """
    Removes all existing tables from the project database before rebuilding it.

    Foreign-key checks are temporarily disabled so an old/obsolete table
    left behind by an earlier version of the project cannot prevent its
    parent table from being removed. This also makes the setup script
    resilient to future schema changes.
    """
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        # Table names come directly from SHOW TABLES, not user input.
        cursor.execute(f"DROP TABLE IF EXISTS `{table}`")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("Old database tables dropped (if they existed).")


def create_tables(cursor):
    """Creates every table the travel agent needs, from a clean slate."""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinations (
            dest_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            region VARCHAR(50) NOT NULL,
            dest_type VARCHAR(20) NOT NULL,        -- 'domestic' or 'international'
            currency VARCHAR(10) NOT NULL,         -- 'INR' or 'USD'
            transit_cost_per_person FLOAT NOT NULL,-- one-time round trip cost, per traveller
            stay_cost_per_night FLOAT NOT NULL,    -- per room, per night
            food_cost_per_day FLOAT NOT NULL,      -- per person, per day
            misc_cost_per_day FLOAT NOT NULL,      -- per person, per day
            description VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            hotel_id INT AUTO_INCREMENT PRIMARY KEY,
            dest_id INT NOT NULL,
            hotel_name VARCHAR(100) NOT NULL,
            price_per_night FLOAT NOT NULL,
            rating FLOAT NOT NULL,
            FOREIGN KEY (dest_id) REFERENCES destinations(dest_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_spots (
            spot_id INT AUTO_INCREMENT PRIMARY KEY,
            dest_id INT NOT NULL,
            spot_name VARCHAR(100) NOT NULL,
            local_travel_cost FLOAT NOT NULL,   -- approx local transport/entry cost, per person
            FOREIGN KEY (dest_id) REFERENCES destinations(dest_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favourites (
            fav_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            dest_id INT NOT NULL,
            days INT NOT NULL,
            travellers INT NOT NULL,
            total_budget FLOAT NOT NULL,
            transit_cost FLOAT NOT NULL,
            stay_cost FLOAT NOT NULL,
            food_cost FLOAT NOT NULL,
            misc_cost FLOAT NOT NULL,
            saved_on DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (dest_id) REFERENCES destinations(dest_id) ON DELETE CASCADE
        )
    """)

    print("All tables created.")


# ---------------------------------------------------------------------
# SAMPLE DATA
# All destination, hotel, food, transit, misc and sightseeing prices are stored in INR.
# International USD sample prices were converted to INR using 1 USD = 95.75 INR
# for the current dataset, so the application displays all travel prices in INR.
# These remain approximate mid-range travel estimates, not live booking prices.
# ---------------------------------------------------------------------

DESTINATIONS = [
    # (name, region, dest_type, currency, transit_per_person, stay_per_night, food_per_day, misc_per_day, description)
    ("Rajasthan", "North India", "domestic", "INR", 4500, 2500, 700, 400,
     "Forts, palaces and deserts of Jaipur, Udaipur and Jodhpur."),
    ("Jammu & Kashmir", "North India", "domestic", "INR", 7000, 3000, 800, 400,
     "Snow-capped valleys, houseboats in Srinagar and Gulmarg's slopes."),
    ("Kerala", "South India", "domestic", "INR", 5500, 2800, 750, 400,
     "Backwaters, houseboats and tea gardens of Munnar and Alleppey."),
    ("Goa", "West India", "domestic", "INR", 4000, 2200, 700, 500,
     "Beaches, nightlife and Portuguese heritage."),
    ("Himachal Pradesh", "North India", "domestic", "INR", 4800, 2000, 600, 350,
     "Hill stations of Manali, Shimla and Spiti valley."),
    ("Andaman Islands", "South India", "domestic", "INR", 9000, 3500, 900, 500,
     "White sand beaches, coral reefs and scuba diving."),
    ("Ladakh", "North India", "domestic", "INR", 8000, 2600, 700, 500,
     "High-altitude passes, Buddhist monasteries and Pangong Lake."),
    ("Pondicherry", "South India", "domestic", "INR", 3500, 2400, 650, 400,
     "French quarter charm, beaches and yoga retreats."),
    ("Thailand", "Southeast Asia", "international", "INR", 33512.5, 3830, 1915, 1436.25,
     "Temples of Bangkok, islands of Phuket and Krabi."),
    ("Sri Lanka", "South Asia", "international", "INR", 21065, 2872.5, 1436.25, 957.5,
     "Beaches, tea plantations and ancient cities."),
    ("Dubai, UAE", "Middle East", "international", "INR", 28725, 6702.5, 3351.25, 2393.75,
     "Skyscrapers, desert safaris and luxury shopping."),
    ("Singapore", "Southeast Asia", "international", "INR", 38300, 7660, 2872.5, 1915,
     "Gardens by the Bay, Sentosa Island and street food."),
    ("Nepal", "South Asia", "international", "INR", 19150, 1915, 1149, 766,
     "Himalayan treks, Kathmandu and Pokhara."),
    ("Bali, Indonesia", "Southeast Asia", "international", "INR", 36385, 3351.25, 1723.5, 1436.25,
     "Rice terraces, temples and surfing beaches."),
    ("Vietnam", "Southeast Asia", "international", "INR", 40215, 2872.5, 1436.25, 1149,
     "Halong Bay cruises, street food and ancient towns."),
    ("Maldives", "South Asia", "international", "INR", 47875, 14362.5, 3830, 2872.5,
     "Overwater villas, coral reefs and private island escapes."),

    # --- NEW: 20 additional destinations ---
    ("Uttarakhand", "North India", "domestic", "INR", 4200, 2000, 600, 350,
     "Rishikesh's rapids, Nainital's lakes and the Char Dham pilgrimage circuit."),
    ("Sikkim", "North India", "domestic", "INR", 6500, 2400, 650, 400,
     "Himalayan monasteries, Gangtok's markets and views of Kanchenjunga."),
    ("Meghalaya", "Northeast India", "domestic", "INR", 7500, 2200, 600, 400,
     "Living root bridges, waterfalls and the wettest place on earth, Cherrapunji."),
    ("Assam", "Northeast India", "domestic", "INR", 7000, 2000, 550, 350,
     "Kaziranga's rhinos, tea gardens and the mighty Brahmaputra."),
    ("Karnataka", "South India", "domestic", "INR", 4500, 2300, 650, 400,
     "Coorg's coffee estates and Hampi's ancient ruins."),
    ("Tamil Nadu", "South India", "domestic", "INR", 4300, 2100, 600, 350,
     "Ooty's hills, Mahabalipuram's shore temples and Chettinad cuisine."),
    ("Maharashtra", "West India", "domestic", "INR", 3800, 2500, 700, 450,
     "Mumbai's energy, Lonavala's hills and Mahabaleshwar's strawberry farms."),
    ("Gujarat", "West India", "domestic", "INR", 4000, 2100, 550, 350,
     "The white salt desert of Rann of Kutch and Gir's Asiatic lions."),
    ("Odisha", "East India", "domestic", "INR", 5000, 1900, 550, 350,
     "Puri's Jagannath Temple, Konark's Sun Temple and golden beaches."),
    ("West Bengal", "East India", "domestic", "INR", 5200, 2200, 600, 400,
     "Darjeeling's tea gardens, toy train and Himalayan views."),
    ("Japan", "East Asia", "international", "INR", 67025, 8617.5, 3830, 2393.75,
     "Neon Tokyo, temples of Kyoto and Mount Fuji views."),
    ("Switzerland", "Europe", "international", "INR", 76600, 14362.5, 5745, 3830,
     "Alpine peaks, pristine lakes and scenic train journeys."),
    ("Paris, France", "Europe", "international", "INR", 62237.5, 12447.5, 5266.25, 3351.25,
     "The Eiffel Tower, world class art and Seine river cruises."),
    ("London, UK", "Europe", "international", "INR", 57450, 13405, 5266.25, 3351.25,
     "Royal palaces, West End theatre and centuries of history."),
    ("New York, USA", "North America", "international", "INR", 71812.5, 15320, 5745, 3830,
     "Skyscrapers, Broadway shows and Central Park."),
    ("Bhutan", "South Asia", "international", "INR", 28725, 5745, 2393.75, 1436.25,
     "Himalayan monasteries, the Tiger's Nest and pristine valleys."),
    ("Turkey", "Middle East", "international", "INR", 43087.5, 5266.25, 2393.75, 1723.5,
     "Istanbul's bazaars and hot air balloons over Cappadocia."),
    ("Greece", "Europe", "international", "INR", 52662.5, 9575, 3830, 2393.75,
     "Whitewashed cliffside villages and Aegean sunsets."),
    ("Egypt", "Africa", "international", "INR", 47875, 4787.5, 1915, 1436.25,
     "Pyramids of Giza, the Nile and ancient temples of Luxor."),
    ("South Africa", "Africa", "international", "INR", 62237.5, 6702.5, 2872.5, 1915,
     "Safari game drives, Table Mountain and Cape wine estates."),
]

HOTELS = {
    # destination name -> list of (hotel_name, price_per_night, rating)
    "Rajasthan": [("Heritage Haveli", 2800, 4.3), ("Budget Rajwada Inn", 1500, 3.6)],
    "Jammu & Kashmir": [("Dal Lake Houseboat", 3200, 4.6), ("Gulmarg Cottage", 2400, 4.0)],
    "Kerala": [("Backwater Resort", 3000, 4.5), ("Munnar Tea Homestay", 1900, 4.1)],
    "Goa": [("Beachside Resort", 2600, 4.2), ("North Goa Budget Stay", 1400, 3.5)],
    "Himachal Pradesh": [("Manali Pine Cottage", 2100, 4.2), ("Shimla Ridge Hotel", 1800, 3.9)],
    "Andaman Islands": [("Havelock Beach Resort", 3800, 4.4), ("Port Blair City Hotel", 2200, 3.7)],
    "Ladakh": [("Leh Palace View Hotel", 2400, 4.2), ("Pangong Lakeside Camp", 3200, 4.5)],
    "Pondicherry": [("French Quarter Boutique Stay", 2600, 4.4), ("Promenade Budget Inn", 1500, 3.7)],
    "Thailand": [("Bangkok City Hotel", 4308.75, 4.1), ("Phuket Beach Resort", 5745, 4.4)],
    "Sri Lanka": [("Colombo Comfort Inn", 2681, 3.9), ("Kandy Hill Resort", 3638.5, 4.2)],
    "Dubai, UAE": [("Downtown Dubai Hotel", 8617.5, 4.3), ("Budget Deira Inn", 5266.25, 3.6)],
    "Singapore": [("Marina Bay View Hotel", 10532.5, 4.5), ("Chinatown Budget Hotel", 6223.75, 3.8)],
    "Nepal": [("Kathmandu Valley Inn", 1723.5, 3.9), ("Pokhara Lakeside Hotel", 2393.75, 4.2)],
    "Bali, Indonesia": [("Ubud Rice-View Villa", 3830, 4.4), ("Kuta Beach Hotel", 3064, 3.9)],
    "Vietnam": [("Hanoi Old Quarter Hotel", 3351.25, 4.1), ("Halong Bay Cruise Cabin", 5266.25, 4.5)],
    "Maldives": [("Overwater Villa Resort", 21065, 4.7), ("Budget Island Guesthouse", 8617.5, 3.8)],

    # --- NEW: hotels for the 20 additional destinations ---
    "Uttarakhand": [("Rishikesh Ganga View Resort", 2400, 4.3), ("Nainital Lake Homestay", 1600, 3.8)],
    "Sikkim": [("Gangtok Mountain View Hotel", 2800, 4.4), ("Pelling Budget Stay", 1700, 3.7)],
    "Meghalaya": [("Shillong Pine Resort", 2500, 4.2), ("Cherrapunji Cottage", 1800, 3.9)],
    "Assam": [("Kaziranga Jungle Resort", 2600, 4.3), ("Guwahati City Hotel", 1700, 3.6)],
    "Karnataka": [("Coorg Coffee Estate Resort", 2900, 4.5), ("Hampi Heritage Stay", 1800, 4.0)],
    "Tamil Nadu": [("Ooty Hillside Resort", 2400, 4.2), ("Mahabalipuram Beach Stay", 1900, 3.8)],
    "Maharashtra": [("Lonavala Valley Resort", 2700, 4.3), ("Mumbai City Hotel", 3200, 4.0)],
    "Gujarat": [("Rann of Kutch Tent Resort", 2600, 4.4), ("Ahmedabad Budget Inn", 1500, 3.6)],
    "Odisha": [("Puri Beach Resort", 2200, 4.1), ("Bhubaneswar City Hotel", 1600, 3.7)],
    "West Bengal": [("Darjeeling Tea View Hotel", 2500, 4.3), ("Kolkata Heritage Stay", 1900, 3.9)],
    "Japan": [("Tokyo Shinjuku Hotel", 12447.5, 4.4), ("Kyoto Ryokan Stay", 9575, 4.6)],
    "Switzerland": [("Interlaken Alpine Hotel", 17235, 4.6), ("Zurich Budget Inn", 10532.5, 3.9)],
    "Paris, France": [("Le Marais Boutique Hotel", 14362.5, 4.4), ("Montmartre Budget Stay", 8617.5, 3.8)],
    "London, UK": [("Westminster City Hotel", 15320, 4.3), ("Camden Budget Inn", 9096.25, 3.7)],
    "New York, USA": [("Manhattan Midtown Hotel", 18192.5, 4.4), ("Brooklyn Budget Stay", 11490, 3.8)],
    "Bhutan": [("Thimphu Valley Resort", 6702.5, 4.5), ("Paro Heritage Homestay", 4308.75, 4.0)],
    "Turkey": [("Istanbul Bosphorus Hotel", 6223.75, 4.3), ("Cappadocia Cave Suite", 7660, 4.6)],
    "Greece": [("Santorini Cliffside Villa", 13405, 4.7), ("Athens Budget Hotel", 5745, 3.8)],
    "Egypt": [("Cairo Nile View Hotel", 5266.25, 4.1), ("Luxor Budget Inn", 3351.25, 3.7)],
    "South Africa": [("Cape Town Waterfront Hotel", 8138.75, 4.4), ("Kruger Safari Lodge", 12447.5, 4.6)],
}

LOCAL_SPOTS = {
    "Rajasthan": [("Amber Fort", 200), ("City Palace Udaipur", 300), ("Jaisalmer Desert Safari", 800)],
    "Jammu & Kashmir": [("Gulmarg Gondola Ride", 900), ("Shikara Ride Dal Lake", 500)],
    "Kerala": [("Alleppey Houseboat Day Trip", 1500), ("Munnar Tea Garden Tour", 400)],
    "Goa": [("Dudhsagar Falls Trip", 600), ("Water Sports Baga Beach", 1000)],
    "Himachal Pradesh": [("Solang Valley Adventure", 700), ("Rohtang Pass Trip", 900)],
    "Andaman Islands": [("Scuba Diving Havelock", 3500), ("Radhanagar Beach Trip", 300)],
    "Ladakh": [("Pangong Lake Visit", 1200), ("Thiksey Monastery", 100)],
    "Pondicherry": [("Auroville Visit", 100), ("French Quarter Walking Tour", 50)],
    "Thailand": [("Grand Palace Entry", 1436.25), ("Phi Phi Island Tour", 4308.75)],
    "Sri Lanka": [("Sigiriya Rock Fortress", 2872.5), ("Kandy Temple Tour", 957.5)],
    "Dubai, UAE": [("Burj Khalifa Entry", 3830), ("Desert Safari", 5266.25)],
    "Singapore": [("Gardens by the Bay Entry", 1915), ("Sentosa Island Pass", 3351.25)],
    "Nepal": [("Kathmandu Durbar Square", 957.5), ("Everest View Day Hike", 2393.75)],
    "Bali, Indonesia": [("Tegallalang Rice Terrace", 478.75), ("Uluwatu Temple Sunset Tour", 1436.25)],
    "Vietnam": [("Halong Bay Cruise", 3830), ("Old Quarter Food Tour", 1149)],
    "Maldives": [("Snorkelling House Reef", 1915), ("Island Hopping Tour", 7660)],

    # --- NEW: local spots for the 20 additional destinations ---
    "Uttarakhand": [("Rishikesh River Rafting", 900), ("Nainital Boat Ride", 300)],
    "Sikkim": [("Tsomgo Lake Excursion", 1000), ("Rumtek Monastery Visit", 100)],
    "Meghalaya": [("Living Root Bridge Trek", 500), ("Nohkalikai Falls Visit", 100)],
    "Assam": [("Kaziranga Jeep Safari", 1500), ("Kamakhya Temple Visit", 100)],
    "Karnataka": [("Coffee Estate Tour", 400), ("Hampi Ruins Cycling Tour", 300)],
    "Tamil Nadu": [("Ooty Tea Garden Visit", 200), ("Shore Temple Entry", 100)],
    "Maharashtra": [("Lonavala Caves Trek", 300), ("Gateway of India Tour", 200)],
    "Gujarat": [("Rann of Kutch White Desert Tour", 800), ("Gir National Park Safari", 1500)],
    "Odisha": [("Konark Sun Temple Entry", 200), ("Puri Beach Sunrise Walk", 100)],
    "West Bengal": [("Darjeeling Toy Train Ride", 700), ("Tiger Hill Sunrise Tour", 300)],
    "Japan": [("Fushimi Inari Shrine Visit", 0), ("Mount Fuji Day Trip", 5745)],
    "Switzerland": [("Jungfraujoch Train Excursion", 21065), ("Lake Geneva Cruise", 3830)],
    "Paris, France": [("Eiffel Tower Entry", 2872.5), ("Louvre Museum Tour", 1915)],
    "London, UK": [("London Eye Ride", 3351.25), ("Tower of London Entry", 2872.5)],
    "New York, USA": [("Statue of Liberty Ferry", 2393.75), ("Empire State Building Entry", 3830)],
    "Bhutan": [("Tiger's Nest Monastery Hike", 1915), ("Punakha Dzong Visit", 957.5)],
    "Turkey": [("Cappadocia Hot Air Balloon", 17235), ("Hagia Sophia Visit", 957.5)],
    "Greece": [("Oia Sunset Viewpoint", 0), ("Acropolis Entry", 1915)],
    "Egypt": [("Pyramids of Giza Entry", 2393.75), ("Nile Felucca Ride", 1436.25)],
    "South Africa": [("Table Mountain Cable Car", 2872.5), ("Kruger Safari Game Drive", 11490)],
}


def seed_data(cursor, connection):
    """
    Inserts every destination along with its hotels and local spots.
    Since drop_tables() always runs first, this always starts from
    empty tables -- no "already seeded" check is needed any more.
    """
    for (name, region, dest_type, currency, transit, stay, food, misc, desc) in DESTINATIONS:
        cursor.execute("""
            INSERT INTO destinations
                (name, region, dest_type, currency, transit_cost_per_person,
                 stay_cost_per_night, food_cost_per_day, misc_cost_per_day, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, region, dest_type, currency, transit, stay, food, misc, desc))

        dest_id = cursor.lastrowid

        for (hotel_name, price, rating) in HOTELS.get(name, []):
            cursor.execute("""
                INSERT INTO hotels (dest_id, hotel_name, price_per_night, rating)
                VALUES (%s, %s, %s, %s)
            """, (dest_id, hotel_name, price, rating))

        for (spot_name, cost) in LOCAL_SPOTS.get(name, []):
            cursor.execute("""
                INSERT INTO local_spots (dest_id, spot_name, local_travel_cost)
                VALUES (%s, %s, %s)
            """, (dest_id, spot_name, cost))

    connection.commit()
    print(f"Inserted {len(DESTINATIONS)} destinations with their hotels and local spots.")


def main():
    try:
        create_database()
        connection = get_connection(with_database=True)
        cursor = connection.cursor()
        drop_tables(cursor)
        connection.commit()
        create_tables(cursor)
        connection.commit()
        seed_data(cursor, connection)
        cursor.close()
        connection.close()
        print("\nDatabase setup complete. You can now run main.py")
    except Error as error:
        print(f"[DATABASE ERROR] Could not set up the database: {error}")
        print("Check that MySQL is running and your config.py details are correct.")


if __name__ == "__main__":
    main()
