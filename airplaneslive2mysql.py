import requests
import json
import mysql.connector
import time

while True:
    # Establish a database connection
    mydb = mysql.connector.connect(
      host="localhost",
      user="username",
      password="password",
      database="ADS-B_db"
    )

    mycursor = mydb.cursor()

    # Define the API endpoint
    url = "https://api.airplanes.live/v2/point/54.833480/20.178089/500"

    # Send a GET request to the API
    response = requests.get(url)

    # Convert the response to JSON
    data = response.json()

    # Iterate over the aircraft data in the response
    for ac in data["ac"]:
        # Prepare the SQL query
        sql = "INSERT INTO Kaliningrad (hex, type, flight, r, t, desc1, ownOp, alt_baro, alt_geom, gs, tas, track, roll, baro_rate, squawk, emergency, category, nav_qnh, nav_altitude_mcp, lat, lon, nic, rc, seen_pos, version, nic_baro, nac_p, nac_v, sil, sil_type, gva, sda, alert, spi, messages, seen, rssi, dst, dir) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        
        # Prepare the data for insertion
        val = (
            ac.get("hex"), ac.get("type"), ac.get("flight").strip() if ac.get("flight") else None, ac.get("r"), ac.get("t"), ac.get("desc"), ac.get("ownOp"), ac.get("alt_baro"), ac.get("alt_geom"), ac.get("gs"), ac.get("tas"), ac.get("track"), ac.get("roll"), ac.get("baro_rate"), ac.get("squawk"), ac.get("emergency"), ac.get("category"), ac.get("nav_qnh"), ac.get("nav_altitude_mcp"), ac.get("lat"), ac.get("lon"), ac.get("nic"), ac.get("rc"), ac.get("seen_pos"), ac.get("version"), ac.get("nic_baro"), ac.get("nac_p"), ac.get("nac_v"), ac.get("sil"), ac.get("sil_type"), ac.get("gva"), ac.get("sda"), ac.get("alert"), ac.get("spi"), ac.get("messages"), ac.get("seen"), ac.get("rssi"), ac.get("dst"), ac.get("dir")
        )
        
        # Execute the SQL query
        mycursor.execute(sql, val)

    # Commit the transaction
    mydb.commit()

    print(mycursor.rowcount, "record(s) inserted.")
    
    # Sleep for 60 seconds
    time.sleep(60)
