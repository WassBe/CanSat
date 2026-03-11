import tkinter as tk
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from tkinter import filedialog
from datetime import datetime
from scipy.interpolate import interp1d
from mpl_toolkits.mplot3d import Axes3D

# ---------------- FILE SELECTION ----------------
tk.Tk().withdraw()

file_path = filedialog.askopenfilename(
    title="Select data file",
    filetypes=(("CanSat Files", "*.can"), ("All files", "*.*"))
)

print(f"Selected file: {Path(file_path).name}")

with open(file_path, "r") as f:
    records = [json.loads(line) for line in f if line.strip()]  # one JSON object per line

# ---------------- DATA EXTRACTION ----------------
times = []
altitude = []
temperature = []
pressure = []
humidity = []
latitude = []
longitude = []

for r in records:
    times.append(int(r["time"]))
    altitude.append(r["altitude"])
    temperature.append(r["temperature"])
    pressure.append(r["pressure"])
    humidity.append(r["humidity"])
    latitude.append(r["latitude"])
    longitude.append(r["longitude"])

times = np.array(times)
altitude = np.array(altitude)
temperature = np.array(temperature)
pressure = np.array(pressure)
humidity = np.array(humidity)
latitude = np.array(latitude)
longitude = np.array(longitude)

# ---------------- TIME NORMALIZATION ----------------
t0 = times[0]
time_s = times - t0

# ---------------- INTERPOLATION ----------------
DT = (time_s[-1] - time_s[0]) / (len(time_s) - 1)  # adapts to actual recording interval
t_new = np.arange(time_s[0], time_s[-1] + 1, DT)

interp_lon = interp1d(time_s, longitude, kind="linear", fill_value="extrapolate")
interp_lat = interp1d(time_s, latitude, kind="linear", fill_value="extrapolate")
interp_alt = interp1d(time_s, altitude, kind="linear", fill_value="extrapolate")

lon_new = interp_lon(t_new)
lat_new = interp_lat(t_new)
alt_new = interp_alt(t_new)

# ---------------- GRAPHS ----------------

# 1) Altitude over time
plt.figure()
plt.plot(time_s, altitude, color="tab:blue")
plt.xlabel("Time (s)")
plt.ylabel("Altitude (m)")
plt.title("Altitude over time")
plt.grid(True)

# 2) Temperature vs altitude (vertical profile)
plt.figure(figsize=(3, 6))
sc = plt.scatter(
    np.zeros_like(altitude),
    altitude,
    c=temperature,
    cmap="coolwarm",
    s=120
)
plt.ylabel("Altitude (m)")
plt.title("Vertical temperature profile")
plt.colorbar(sc, label="Temperature (°C)")
plt.xticks([])
plt.grid(True)

# 3) Pressure vs altitude (scaled)
plt.figure()
plt.plot(altitude, pressure, color="tab:green")
plt.fill_between(altitude, pressure, alpha=0.3, color="tab:green")

p_range = pressure.max() - pressure.min()
p_min = pressure.min() - p_range
p_max = pressure.max() + p_range
plt.ylim(p_min, p_max)

plt.xlabel("Altitude (m)")
plt.ylabel("Pressure (hPa)")
plt.title("Pressure vs altitude")
plt.grid(True)

# 4) Humidity vs altitude
plt.figure()
sizes = humidity * 1.5
plt.scatter(
    altitude,
    humidity,
    s=sizes,
    color="tab:purple",
    alpha=0.7
)
plt.xlabel("Altitude (m)")
plt.ylabel("Relative humidity (%)")
plt.title("Humidity vs altitude")
plt.grid(True)

# 5) 2D GPS map (interpolated)
plt.figure()
plt.plot(lon_new, lat_new, linestyle="--", color="gray", alpha=0.5)
sc = plt.scatter(
    lon_new,
    lat_new,
    c=alt_new,
    cmap="viridis",
    s=80
)
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.title("GPS trajectory (interpolated)")
plt.colorbar(sc, label="Altitude (m)")
plt.axis("equal")
plt.grid(True)

# 6) 3D GPS map (altitude on Z axis)
R = 6371000
lat0 = np.deg2rad(lat_new[0])

x_m = np.deg2rad(lon_new - lon_new[0]) * R * np.cos(lat0)
y_m = np.deg2rad(lat_new - lat_new[0]) * R
z_m = alt_new

fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection="3d")

ax.plot(x_m, y_m, z_m, color="gray", alpha=0.6, linewidth=1)
sc = ax.scatter(x_m, y_m, z_m, c=z_m, cmap="viridis", s=60)

ax.set_xlabel("East-West displacement (m)")
ax.set_ylabel("North-South displacement (m)")
ax.set_zlabel("Altitude (m)")
ax.set_title("3D GPS trajectory")

x_range = np.ptp(x_m) if np.ptp(x_m) > 0 else 1.0
y_range = np.ptp(y_m) if np.ptp(y_m) > 0 else 1.0
z_range = np.ptp(z_m) if np.ptp(z_m) > 0 else 1.0
ax.set_box_aspect([x_range, y_range, z_range])

fig.colorbar(sc, ax=ax, label="Altitude (m)")

# ---------------- FLOOD RISK ESTIMATION ----------------

RH_n = humidity / 100.0
P_n = (1013.0 - pressure) / 1013.0
T_n = (20.0 - temperature) / 20.0

w_h, w_p, w_t = 0.5, 0.3, 0.2

FRI = w_h * RH_n + w_p * P_n + w_t * T_n
FRI_ground = FRI * np.exp(-altitude / 1000)

FRI_max = FRI_ground.max()
FRI_mean = FRI_ground.mean()

# ---------------- RISK GRAPH ----------------
plt.figure()
plt.plot(time_s, FRI_ground, color="tab:red", linewidth=2)
plt.fill_between(time_s, FRI_ground, alpha=0.3, color="tab:red")
plt.xlabel("Time (s)")
plt.ylabel("Flood risk index")
plt.title("Flood risk index over time")
plt.grid(True)

# ---------------- INTERPRETATION ----------------
# PENDING METHOD

# ---------------- TERMINAL OUTPUT ----------------
print("\n--- Flood risk estimation ---\n")
print("PENDING METHOD")

# ---------------- TEXT REPORT ----------------
report_text = f"""
FLOOD RISK ESTIMATION
=====================

PENDING METHOD
"""

with open("report.txt", "w", encoding="utf-8") as f:
    f.write(report_text.strip())

print("\nReport saved: report.txt")

# ---------------- DISPLAY GRAPHS ----------------
plt.show()