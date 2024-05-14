# Sample from blah.csv
# id,Kaliningradcol,hex,type,flight,r,t,desc1,ownOp,alt_baro,alt_geom,gs,tas,track,roll,baro_rate,squawk,emergency,category,nav_qnh,nav_altitude_mcp,lat,lon,nic,rc,seen_pos,version,nic_baro,nac_p,nac_v,sil,sil_type,gva,sda,alert,spi,messages,seen,rssi,dst,dir,timestamp
# 340899,NULL,4acaa1,adsb_icao,SAS4621,SE-RUA,A20N,"AIRBUS A-320neo","Scandinavian Airlines",39000,39600,435.3,430,203.56,-0.35,64,3522,none,A3,1012.8,39008,53.910873,6.049151,8,186,0.044,2,1,9,1,3,perhour,2,3,0,0,14743,0.0,-16.6,496.39,269.4,"2024-05-12 08:00:23"
# 340900,NULL,400a5b,adsb_icao,BAW790,G-DBCA,A319,"AIRBUS A-319","British Airways",37000,37675,447.9,444,55.92,0.88,64,1442,none,A3,1012.8,36992,55.740829,6.517473,8,186,0.137,2,1,9,1,3,perhour,2,2,0,0,13682,0.0,-21.9,469.456,282.2,"2024-05-12 08:00:23"

# Wayne Metcalf 2024

import scipy.spatial
import pandas as pd
import numpy as np
from scipy.stats import norm, zscore
from scipy.spatial import Delaunay
from sklearn.preprocessing import normalize, KBinsDiscretizer, StandardScaler
from scipy.signal import bessel, filtfilt

# Load ADS-B data
adsb_data = pd.read_csv('blah.csv')

# Keep a copy of the original data
adsb_data_original = adsb_data.copy()

# Only keep rows where 'timestamp', 'lat', 'lon', 'alt_geom' columns have no missing values
adsb_data = adsb_data.dropna(subset=['timestamp', 'lat', 'lon', 'alt_geom'])

# Convert timestamp column to numeric type and parse the datetime string
adsb_data['timestamp'] = pd.to_datetime(adsb_data['timestamp'])
adsb_data['timestamp'] = (adsb_data['timestamp'] - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')

# Remove duplicates
adsb_data.drop_duplicates(inplace=True)

# Define the number of bins
n_bins = 512

# Initialize the KBinsDiscretizer
kb = KBinsDiscretizer(n_bins=n_bins, encode='ordinal', strategy='uniform')

# Perform the binning on 'lat' and 'lon'
adsb_data[['lat', 'lon']] = kb.fit_transform(adsb_data[['lat', 'lon']])

# Normalize 'lat' and 'lon' using Z-score normalization
adsb_data[['lat', 'lon']] = adsb_data[['lat', 'lon']].apply(zscore)

# Handle missing values by imputation
# Select only numeric columns
numeric_adsb_data = adsb_data.select_dtypes(include=[np.number])

# calculate the mean
numeric_adsb_data.fillna(numeric_adsb_data.mean(), inplace=True)

# 'lat' and 'lon' are binned into 10 equal width bins and normalized

# Define GPS signal model and generate synthetic data
f0 = 1.57542e9  # GPS L1 frequency (Hz)
noise_std = 10  # Noise standard deviation (Hz)
timestep = 1  # Time step for signal simulation (s)

gps_signal = pd.Series(np.sin(2 * np.pi * f0 * adsb_data['timestamp'] / timestep) + noise_std * np.random.randn(len(adsb_data)))

# Define the order of the filter and the critical frequency 'Wn'
N = 3  # Order of the filter
Wn = 0.1  # Critical frequency

# Create a Bessel filter
b, a = bessel(N, Wn)

# Apply the filter to the GPS signal data
gps_signal_filtered = filtfilt(b, a, gps_signal)

# Convert the filtered signal back to a pandas Series
gps_signal = pd.Series(gps_signal_filtered)

# Ensure gps_signal has the same index as adsb_data
gps_signal.index = adsb_data.index

# Data Cleaning
Q1 = gps_signal.quantile(0.25)
Q3 = gps_signal.quantile(0.75)
IQR = Q3 - Q1

# Create a mask for the values that are NOT outliers
mask = ~((gps_signal < (Q1 - 1.5 * IQR)) | (gps_signal > (Q3 + 1.5 * IQR)))

# Apply the mask to both gps_signal and adsb_data
gps_signal = gps_signal[mask]
adsb_data = adsb_data[mask]

# Feature Engineering
gps_signal_diff = gps_signal.diff()
adsb_data['gps_signal_diff'] = gps_signal_diff

# Define the size of the rolling window
window_size = 100

# Calculate rolling standard deviation for GPS signal characteristics
rolling_std = gps_signal.rolling(window=window_size).std()

# Define jammer detection threshold (2-3 SDs)
threshold_multiplier = 2.5
threshold_freq = threshold_multiplier * rolling_std

# Use Median
median = gps_signal.median()

# Identify potential jamming activity using statistical analysis
jammed_data = adsb_data[(np.abs(gps_signal - median) > threshold_freq)].copy()

# 'rssi' column  represents the signal strength of the jammed data points
jammed_data.loc[:, 'weights'] = 1 / jammed_data['rssi']

jammed_data[['lat', 'lon']] = adsb_data_original[['lat', 'lon']]

# Check if there are enough points for triangulation
if len(jammed_data) >= 4:
    # Include altitude in the triangulation process
    triangulation = scipy.spatial.Delaunay(jammed_data[['lat', 'lon', 'alt_geom']].values)
    
    # Calculate the average signal strength for each tetrahedron 
    tetrahedron_weights = []
    for tetrahedron in triangulation.simplices:
        # Get the vertices of the tetrahedron
        vertices = jammed_data.iloc[tetrahedron]
        # Calculate the average signal strength of the vertices
        avg_signal_strength = vertices['weights'].mean()
        tetrahedron_weights.append(avg_signal_strength)
    
    # Set the fixed altitude of the jammer (in meters)
    jammer_alt = 50

    # Localize the jammer using spatial analysis
    jammed_tetrahedrons = triangulation.points[triangulation.simplices]
    centroids = np.mean(jammed_tetrahedrons, axis=1)
    jammer_lat, jammer_lon, _ = np.average(centroids, axis=0, weights=tetrahedron_weights)
    
    # Calculate the distance between the jammer and each receiver
    jammed_data['distance'] = np.sqrt((jammed_data['lat'] - jammer_lat)**2 + (jammed_data['lon'] - jammer_lon)**2 + (jammed_data['alt_geom'] - jammer_alt)**2)
    
    # Calculate the weights using the inverse square law
    jammed_data['weights'] = 1 / (jammed_data['distance']**2)

    # Define the direction of the main lobe of the jammer's antenna (in degrees)
    main_lobe_direction = 90  #  actual direction

    # Define the half-power beamwidth of the main lobe (in degrees)
    main_lobe_beamwidth = 30  # actual beamwidth

    # Calculate the direction from each receiver to the jammer
    jammed_data['direction'] = np.arctan2(jammed_data['lon'] - jammer_lon, jammed_data['lat'] - jammer_lat) * 180 / np.pi

    # Calculate the difference between the direction of the main lobe and the direction to each receiver
    jammed_data['direction_diff'] = np.abs(jammed_data['direction'] - main_lobe_direction)

    # Calculate the gain of the antenna in the direction of each receiver
    jammed_data['gain'] = np.where(jammed_data['direction_diff'] <= main_lobe_beamwidth / 2, 1, 0.5)  # gain of the side lobes

    # Adjust the weights using the gain of the antenna
    jammed_data['weights'] *= jammed_data['gain']

    # Normalize the weights so they sum up to 1
    jammed_data['weights'] = normalize(jammed_data['weights'].values.reshape(1, -1), norm='l1').ravel()

    # Calculate the radio horizon for the jammer
    R = 6371  # Radius of the Earth in kilometers
    h_jammer = 0.1  # Height of the jammer in kilometers (100 meters)
    d_jammer = np.sqrt(2 * h_jammer * R)  # Radio horizon of the jammer in kilometers

    # Convert the distances in the 'distance' column from meters to kilometers
    jammed_data['distance'] = jammed_data['distance'] / 1000

    # Only consider aircraft that are within the jammer's radio horizon
    jammed_data = jammed_data[jammed_data['distance'] <= d_jammer]
    
    print("Estimated GPS Jammer Location:", (jammer_lat, jammer_lon, jammer_alt))
else:
    print("Not enough data points for triangulation.")
    print("Number of data points needed for triangulation: 4")
    print("Number of data points in jammed_data: ", len(jammed_data))
