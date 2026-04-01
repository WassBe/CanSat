#include <SPI.h>
#include <SD.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <TinyGPS++.h>
#include <SoftwareSerial.h>

const byte masterLED = 2;
const byte issueLED = 9;
const byte dataLED = 6;
const byte contact1 = 7;
const byte contact2 = 8;
const byte sdCard = 10;

uint16_t timeCounter = 0;
const uint16_t SLP_PARIS_HPA = 1021;

Adafruit_BME280 bme;
TinyGPSPlus gps;
SoftwareSerial gpsSerial(4, 3);

bool isParachuteActive = false;
byte inactiveCounter = 0;

void writeFixed(File &f, float val) {
  f.print((int)val);
  f.print('.');
  int dec = abs((int)(val * 100) % 100);
  if (dec < 10) f.print('0');
  f.print(dec);
}

void setup() {
  Serial.begin(9600);
  gpsSerial.begin(9600);
  randomSeed(analogRead(A0));

  pinMode(masterLED, OUTPUT);
  pinMode(issueLED,  OUTPUT);
  pinMode(dataLED,   OUTPUT);
  pinMode(contact1,  OUTPUT);
  pinMode(contact2,  INPUT_PULLUP);

  digitalWrite(contact1,  LOW);
  digitalWrite(masterLED, HIGH);
  digitalWrite(issueLED,  LOW);
  digitalWrite(dataLED,   LOW);

  while (!SD.begin(sdCard)) {
    digitalWrite(issueLED, !digitalRead(issueLED));
    Serial.println(F("ERROR: SD card not found, retrying..."));
    delay(500);
  }
  digitalWrite(issueLED, LOW);
  Serial.println(F("SD card initialized successfully."));

  while (!bme.begin(0x76)) {
    digitalWrite(issueLED, !digitalRead(issueLED));
    Serial.println(F("ERROR: BME280 not found, retrying..."));
    delay(500);
  }
  digitalWrite(issueLED, LOW);
  Serial.println(F("Barometer ready."));
}

void loop() {
  bool contactState = (digitalRead(contact2) == LOW);

  if (contactState)  inactiveCounter = 0;
  if (contactState  && !isParachuteActive) isParachuteActive = true;
  if (!contactState &&  isParachuteActive) inactiveCounter++;
  if (inactiveCounter >= 5) isParachuteActive = false;

  if (isParachuteActive) {
    digitalWrite(dataLED, HIGH);

    float temperature = bme.readTemperature();
    float humidity = bme.readHumidity();
    float pressure = bme.readPressure() / 100.0F;
    float altitude = bme.readAltitude(SLP_PARIS_HPA);

    while (gpsSerial.available()) gps.encode(gpsSerial.read());

    double latitude  = gps.location.isValid() ? gps.location.lat()     : 0.0;
    double longitude = gps.location.isValid() ? gps.location.lng()     : 0.0;
    double altitudeGPS = gps.altitude.isValid()  ? gps.altitude.meters() : 0.0;

    Serial.println(inactiveCounter);

    File file = SD.open("data.txt", FILE_WRITE);
    if (file) {
      file.print(F("{\"time\":")); file.print(timeCounter);
      file.print(F(",\"temperature\":")); writeFixed(file, temperature);
      file.print(F(",\"humidity\":")); writeFixed(file, humidity);
      file.print(F(",\"pressure\":")); writeFixed(file, pressure);
      file.print(F(",\"altitude\":")); writeFixed(file, altitude);
      file.print(F(",\"altitudeGPS\":")); writeFixed(file, (float)altitudeGPS);
      file.print(F(",\"latitude\":")); file.print(latitude,  6);
      file.print(F(",\"longitude\":")); file.print(longitude, 6);
      file.println('}');
      file.flush();
      file.close();
      Serial.println(F("Data write: OK"));
    } else {
      Serial.println(F("Data write: FAIL"));
    }

    timeCounter++;
  } else {
    digitalWrite(dataLED, LOW);
  }

  delay(1000);
}
