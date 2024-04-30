import csv
import math

def calculate_radio_horizon(altitude):
    return 1.23 * math.sqrt(altitude)

def process_csv(input_file_name, output_file_name):
    with open(input_file_name, 'r') as file:
        csv_reader = csv.DictReader(file)
        fieldnames = ['lat', 'lon', 'radio_horizon']
        with open(output_file_name, 'w', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in csv_reader:
                # Skip rows with the word 'ground'
                if 'ground' in row.values():
                    continue
                # Only process rows with valid altitude, latitude, and longitude
                if row['alt_baro'] and row['lat'] and row['lon']:
                    altitude = float(row['alt_baro'])
                    lat = float(row['lat'])
                    lon = float(row['lon'])
                    radio_horizon = calculate_radio_horizon(altitude)
                    writer.writerow({'lat': lat, 'lon': lon, 'radio_horizon': radio_horizon})


process_csv('csv_raw.csv', 'output_horizons.csv')
