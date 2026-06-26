
#define BLYNK_TEMPLATE_ID "..."
#define BLYNK_TEMPLATE_NAME "..."
#define BLYNK_AUTH_TOKEN "..."

#include <WiFi.h>
#include <WiFiClient.h>
#include <BlynkSimpleEsp32.h>
#include <DHT.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>


char auth[] = "...";
char ssid[] = "..."; 
char pass[] = "";


#define LED_PIN 2       // V1: Lompe
#define DHT_PIN 15      // V4, V5: Hum et Temp
#define TRIG_PIN 5      // V3: Approximiter(Traget)
#define ECHO_PIN 18     // V3: Approximiter (Echo)

#define DHTTYPE DHT22


DHT dht(DHT_PIN, DHTTYPE);
Adafruit_MPU6050 mpu;
BlynkTimer timer;

void setup() {
 
  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  dht.begin();
  Wire.begin();


  if (!mpu.begin()) {
    Serial.println("❌ MPU6050 not found!");
    while (1) delay(10);
  }

 
  Blynk.begin(auth, ssid, pass);

  
  timer.setInterval(1000L, sendAllSensorData);
}


BLYNK_WRITE(V1) {
  int pixelValue = param.asInt();
  digitalWrite(LED_PIN, pixelValue);
}


void loop() {
  Blynk.run();
  timer.run();
}


void sendAllSensorData() {
  
 
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  float distanceCm = duration * 0.034 / 2;
  
  Blynk.virtualWrite(V3, distanceCm); 

 
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (!isnan(h) && !isnan(t)) {
    Blynk.virtualWrite(V4, h); 
    Blynk.virtualWrite(V5, t); 
  }

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

 
  float total_accel = sqrt(pow(a.acceleration.x, 2) + 
                           pow(a.acceleration.y, 2) + 
                           pow(a.acceleration.z, 2));

  
  Blynk.virtualWrite(V6, total_accel); 
  
  
}