import tkinter as tk
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from tkinter import filedialog
from scipy.interpolate import interp1d
from mpl_toolkits.mplot3d import Axes3D

# ---------------- FILE SELECTION ----------------
tk.Tk().withdraw()

file_path = filedialog.askopenfilename(
    title="Select data file",
    filetypes=(("All files", "*.*"),)
)

print(f"Selected file: {Path(file_path).name}")

with open(file_path, "r") as f:
    records = [json.loads(line) for line in f if line.strip()]

# ---------------- DATA EXTRACTION ----------------
times = []
altitude = []
temperature = []
pressure = []
humidity = []

gps_times = []
latitude = []
longitude = []

for r in records:
    times.append(r["time"])
    altitude.append(r["altitude"])
    temperature.append(r["temperature"])
    pressure.append(r["pressure"])
    humidity.append(r["humidity"])
    if r["latitude"] != 0 and r["longitude"] != 0:
        gps_times.append(r["time"])
        latitude.append(r["latitude"])
        longitude.append(r["longitude"])

times = np.array(times)
altitude = np.array(altitude)
temperature = np.array(temperature)
pressure = np.array(pressure)
humidity = np.array(humidity)
gps_times = np.array(gps_times)
latitude = np.array(latitude)
longitude = np.array(longitude)

# ---------------- TIME NORMALIZATION ----------------
t0 = times[0]
time_s = times - t0

# ---------------- INTERPOLATION ----------------
DT = (time_s[-1] - time_s[0]) / (len(time_s) - 1)

has_gps = len(gps_times) >= 2

if has_gps:
    t_new = np.arange(gps_times[0], gps_times[-1] + 1, DT)

    interp_lon = interp1d(gps_times, longitude, kind="linear", fill_value="extrapolate")
    interp_lat = interp1d(gps_times, latitude, kind="linear", fill_value="extrapolate")
    interp_alt = interp1d(gps_times, altitude[np.isin(times, gps_times)], kind="linear", fill_value="extrapolate")

    lon_new = interp_lon(t_new)
    lat_new = interp_lat(t_new)
    alt_new = interp_alt(t_new)

# ---------------- ANALYSIS ----------------

# --- Pressure correction (altitude effect) ---
# Avoids confusing a variation caused by descent with actual weather change
pressure_corrected = pressure * np.exp(altitude / 8434.5)

# --- Pressure trend (derivative) ---
pressure_trend = np.gradient(pressure_corrected)

# --- Dew point approximation ---
dew_point = temperature - ((100 - humidity) / 5)
dew_diff = np.abs(temperature - dew_point)

# --- Improved score based on physical contributions ---
risk = np.zeros_like(altitude, dtype=float)

# Humidity (high weight)
risk += 0.4 * (humidity / 100)

# Pressure drop (only if negative = bad sign)
risk += 0.4 * np.clip(-pressure_trend * 5, 0, 1)

# Air saturation (dew point proximity)
risk += 0.2 * np.clip((2 - dew_diff) / 2, 0, 1)

# --- Bonus if dangerous combination ---
danger_mask = (humidity > 80) & (pressure_trend < -0.05)
risk[danger_mask] += 0.2

# Clamp between 0 and 1
risk = np.clip(risk, 0, 1)

# --- Terrain factor (final altitude) ---
ground_altitude = altitude[-1]

if ground_altitude < 50:
    risk += 0.1
    risk = np.clip(risk, 0, 1)

# --- Final statistics ---
risk_max = np.max(risk)
risk_mean = np.mean(risk)

# --- Classification ---
if risk_max > 0.7:
    interpretation = "HIGH RISK of flooding"
elif risk_max > 0.4:
    interpretation = "MODERATE RISK of flooding"
else:
    interpretation = "LOW RISK of flooding"


# ---------------- TERMINAL OUTPUT ----------------
print("\n--- Flood risk estimation ---\n")
print(f"Estimated ground altitude: {ground_altitude:.1f} m")
print(f"Max risk: {risk_max:.2f}")
print(f"Mean risk: {risk_mean:.2f}")
print(f"Conclusion: {interpretation}")


# ---------------- TEXT REPORT ----------------
report_text = f"""
FLOOD RISK ESTIMATION
=====================

Estimated ground altitude: {ground_altitude:.1f} m

Factor analysis:
- Average humidity: {np.mean(humidity):.1f} %
- Pressure trend: {'dropping' if np.mean(pressure_trend) < 0 else 'stable/rising'}
- Dew point proximity: {np.mean(dew_diff):.2f} °C

Indicators:
- Maximum risk: {risk_max:.2f}
- Mean risk: {risk_mean:.2f}

Conclusion:
{interpretation}

Method:
Risk is estimated from:
- relative humidity (water vapor presence)
- pressure variation (disturbance detection)
- air saturation (dew point)
- terrain altitude adjustment

Contributions are weighted and combined to produce an overall index.
"""

with open("report.txt", "w") as f:
    f.write(report_text)

# ---------------- CHARTS ----------------

# Altitude over time
plt.figure()
plt.plot(time_s, altitude, color="tab:blue")
plt.xlabel("Time (s)")
plt.ylabel("Altitude (m)")
plt.title("Altitude over time")
plt.grid(True)

# Temperature vs altitude (vertical profile)
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

# Pressure vs altitude (scaled)
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

# Humidity vs altitude
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

# Interpolated 2D GPS map
if has_gps:
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
    plt.title("GPS trajectory (12 s steps)")
    plt.colorbar(sc, label="Altitude (m)")
    plt.axis("equal")
    plt.grid(True)

# 3D GPS map (altitude as Z axis)
if has_gps:
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

# ---------------- DISPLAY CHARTS ----------------
plt.show(block=True)
