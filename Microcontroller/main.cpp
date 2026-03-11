#include <SPI.h>
#include <SD.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

// BASICS ---------------------------------------------------------------

const int masterLED = 13;
const int issueLED = 9;
const int dataLED = 12;

const int contact = 7;

const int sdCard = 10;
char fileName[24];
int timeCounter = 0;

Adafruit_BME280 bme;
const int SLP_PARIS_HPA = 1021; // SEA LEVEL PRESSURE Paris (hPa)

TinyGPSPlus gps;
SoftwareSerial gpsSerial(4, 3); // RX, TX

bool isParachuteActive;

String genFileName();

// FILE NAME ------------------------------------------------------------
String genFileName() {
  String hex = "";
  for (int i = 0; i < 8; i++) {
    hex += String(random(0, 16), HEX);
  }
  return hex;
}

void setup() {
  Serial.begin(9600);
  gpsSerial.begin(9600);
  randomSeed(analogRead(A0));

  // SETUP LEDS -----------------------------------------------------------
  pinMode(masterLED, OUTPUT);
  pinMode(issueLED, OUTPUT);
  pinMode(dataLED, OUTPUT);

  pinMode(contact, INPUT_PULLUP);

  digitalWrite(masterLED, HIGH);
  digitalWrite(issueLED, LOW);
  digitalWrite(dataLED, LOW);

  snprintf(fileName, sizeof(fileName), "record-%s.can", genFileName().c_str());

  // SETUP SD -------------------------------------------------------------
  if (SD.begin(sdCard)) {
    Serial.println(F("SD card initialized successfully."));
  } else {
    digitalWrite(issueLED, HIGH);
    Serial.println(F("ERROR: SD card initialization failed."));
    while (true);
  }

  // SETUP BME280 ---------------------------------------------------------
  if (bme.begin(0x76)) {
    Serial.println(F("Barometer ready."));
  } else {
    digitalWrite(issueLED, HIGH);
    Serial.println(F("ERROR: BME280 module not found."));
    while (true);
  }
}

void loop() {
  // PARACHUTE CHECK ------------------------------------------------------
  isParachuteActive = (digitalRead(contact) == HIGH);

  if (isParachuteActive) {
    digitalWrite(dataLED, HIGH);

    // BAROMETER DATA ACQUISITION -----------------------------------------
    float temperature = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;
    float altitudeBaro = bme.readAltitude(SLP_PARIS_HPA);

    // GPS DATA ACQUISITION -----------------------------------------------
    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }

    double latitude = gps.location.lat();
    double longitude = gps.location.lng();
    double altitudeGPS = gps.altitude.meters();

    // FILE PREPARATION ---------------------------------------------------
    float finalTemperature = temperature;
    float finalHumidity = humidity;
    float finalPressure = pressure;
    float finalAltitude = (altitudeBaro + altitudeGPS) / 2;
    double finalLatitude = latitude;
    double finalLongitude = longitude;

    char jsonRow[128];
    snprintf(jsonRow, sizeof(jsonRow),
      "{\"time\":%d,\"temperature\":%.2f,\"humidity\":%.2f,\"pressure\":%.2f,\"altitude\":%.2f,\"latitude\":%.6f,\"longitude\":%.6f}",
      timeCounter, finalTemperature, finalHumidity, finalPressure, finalAltitude, finalLatitude, finalLongitude);

    timeCounter++;

    File file = SD.open(fileName, O_WRITE | O_CREAT | O_APPEND);

    // FILE CHECK AND WRITE -----------------------------------------------
    if (file) {
      file.println(jsonRow);
      file.close();
      Serial.println(jsonRow);
    } else {
      digitalWrite(issueLED, HIGH);
      Serial.println(F("ERROR: Unable to open file."));
    }

  } else {
    digitalWrite(dataLED, LOW);
  }

  delay(1000);
}