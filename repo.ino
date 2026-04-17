#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <esp_system.h>

//
// WiFi Access Point config
//

const char* ssid = "RepoRobot";
const char* password = "12345678";

//
// Servo config
//

// Update these pins to match your wiring.
#define MOUTH_PIN      15
#define LEFT_ARM_PIN   4
#define RIGHT_ARM_PIN  17
#define LEFT_EYE_PIN   21
#define RIGHT_EYE_PIN  18

const int MOUTH_CLOSED = 100;
const int MOUTH_HALF = 112;
const int MOUTH_OPEN = 125;

const int ARM_MIN = 30;
const int ARM_CENTER = 90;
const int ARM_MAX = 150;

const int LEFT_EYE_MIN = 40;
const int LEFT_EYE_MAX = 120;
const int LEFT_EYE_CENTER = 90;

const int RIGHT_EYE_MIN = 50;
const int RIGHT_EYE_MAX = 140;
const int RIGHT_EYE_CENTER = 90;

enum RobotState
{
  STATE_IDLE,
  STATE_LISTENING,
  STATE_THINKING,
  STATE_SPEAKING
};

RobotState currentState = STATE_IDLE;

struct ServoAxis
{
  Servo servo;
  int pin;
  int current;
  int target;
  uint8_t stepDelayMs; 
  uint32_t lastStepMs;
};

ServoAxis mouthAxis = {Servo(), MOUTH_PIN, MOUTH_CLOSED, MOUTH_CLOSED, 8, 0};
ServoAxis leftArmAxis = {Servo(), LEFT_ARM_PIN, ARM_CENTER, ARM_CENTER, 5, 0};
ServoAxis rightArmAxis = {Servo(), RIGHT_ARM_PIN, ARM_CENTER, ARM_CENTER, 5, 0};
ServoAxis leftEyeAxis = {Servo(), LEFT_EYE_PIN, LEFT_EYE_CENTER, LEFT_EYE_CENTER, 3, 0};
ServoAxis rightEyeAxis = {Servo(), RIGHT_EYE_PIN, RIGHT_EYE_CENTER, RIGHT_EYE_CENTER, 3, 0};

struct SpeakingPlan
{
  int wordCount;
  int durationMs;
  int tickMs;
  bool active;
  uint32_t startedAtMs;
  uint32_t lastMouthTickMs;
};

SpeakingPlan speakingPlan = {0, 0, 140, false, 0, 0};

bool attachAxis(ServoAxis& axis, const char* name)
{
  axis.servo.setPeriodHertz(50);
  axis.servo.attach(axis.pin, 500, 2400);

  if (!axis.servo.attached())
  {
    Serial.print("SERVO ATTACH FAILED: ");
    Serial.print(name);
    Serial.print(" pin=");
    Serial.println(axis.pin);
    return false;
  }

  Serial.print("SERVO ATTACHED: ");
  Serial.print(name);
  Serial.print(" pin=");
  Serial.println(axis.pin);
  axis.servo.write(axis.current);
  return true;
}

//
// HTTP server
//

WebServer server(80);

//
// Motion helpers
//

int clampToRange(int value, int minValue, int maxValue)
{
  if (value < minValue)
    return minValue;
  if (value > maxValue)
    return maxValue;
  return value;
}

void setTarget(ServoAxis& axis, int target)
{
  axis.target = target;
}

// ==========================================
// FUNCIÓN CORREGIDA PARA TWEAK DE CABEZA
// Acepta un flag de suavidad.
// ==========================================
void stepAxis(ServoAxis& axis, bool smooth = false)
{
  if (axis.current == axis.target)
    return;

  if (smooth)
  {
    uint32_t nowMs = millis();
    // Respeta el tiempo del servo para moverlo grado por grado suavemente
    if (nowMs - axis.lastStepMs >= axis.stepDelayMs)
    {
      axis.lastStepMs = nowMs;
      if (axis.target > axis.current)
        axis.current++;
      else
        axis.current--;
        
      axis.servo.write(axis.current);
    }
  }
  else
  {
    // Resto del cuerpo se mueve de golpe
    axis.current = axis.target;
    axis.servo.write(axis.current);
  }
}

int triangleWave(uint32_t nowMs, uint32_t periodMs, int minValue, int maxValue)
{
  if (periodMs < 2)
    return minValue;

  uint32_t half = periodMs / 2;
  uint32_t t = nowMs % periodMs;

  if (t < half)
    return map(t, 0, half, minValue, maxValue);

  return map(t - half, 0, half, maxValue, minValue);
}

void setEyesByGazePercent(int gazePercent)
{
  gazePercent = clampToRange(gazePercent, -100, 100);

  // Positive gaze means turn right for both eyes.
  int leftTarget = map(gazePercent, -100, 100, LEFT_EYE_MAX, LEFT_EYE_MIN);
  int rightTarget = map(gazePercent, -100, 100, RIGHT_EYE_MAX, RIGHT_EYE_MIN);

  setTarget(leftEyeAxis, clampToRange(leftTarget, LEFT_EYE_MIN, LEFT_EYE_MAX));
  setTarget(rightEyeAxis, clampToRange(rightTarget, RIGHT_EYE_MIN, RIGHT_EYE_MAX));
}

void setRobotState(RobotState next)
{
  currentState = next;

  if (currentState == STATE_LISTENING)
  {
    Serial.println("STATE -> LISTENING");
    setTarget(mouthAxis, MOUTH_CLOSED);
    speakingPlan.active = false;
  }
  else if (currentState == STATE_THINKING)
  {
    Serial.println("STATE -> THINKING");
    setTarget(mouthAxis, MOUTH_CLOSED);
    setTarget(leftArmAxis, ARM_CENTER);
    setTarget(rightArmAxis, ARM_CENTER);
    speakingPlan.active = false;
  }
  else if (currentState == STATE_SPEAKING)
  {
    Serial.println("STATE -> SPEAKING");
  }
  else
  {
    Serial.println("STATE -> IDLE");
    speakingPlan.active = false;
    setTarget(mouthAxis, MOUTH_CLOSED);
    setTarget(leftArmAxis, leftArmAxis.current);
    setTarget(rightArmAxis, rightArmAxis.current);
    setTarget(leftEyeAxis, leftEyeAxis.current);
    setTarget(rightEyeAxis, rightEyeAxis.current);
  }
}

void updateListeningAnimation(uint32_t nowMs)
{
  int left = triangleWave(nowMs, 900, ARM_MIN, ARM_MAX);
  int right = ARM_MIN + ARM_MAX - left;
  setTarget(leftArmAxis, left);
  setTarget(rightArmAxis, right);

  setTarget(leftEyeAxis, LEFT_EYE_CENTER);
  setTarget(rightEyeAxis, RIGHT_EYE_CENTER);
}

void updateThinkingAnimation(uint32_t nowMs)
{
  // Use full travel and higher speed for both eyes while thinking.
  int leftEye = triangleWave(nowMs, 850, LEFT_EYE_MAX, LEFT_EYE_MIN);
  int rightEye = triangleWave(nowMs, 850, RIGHT_EYE_MAX, RIGHT_EYE_MIN);
  setTarget(leftEyeAxis, leftEye);
  setTarget(rightEyeAxis, rightEye);

  setTarget(leftArmAxis, ARM_CENTER);
  setTarget(rightArmAxis, ARM_CENTER);
  setTarget(mouthAxis, MOUTH_CLOSED);
}

void updateSpeakingAnimation(uint32_t nowMs)
{
  if (!speakingPlan.active)
  {
    setTarget(mouthAxis, MOUTH_CLOSED);
    return;
  }

  // ==========================================
  // TWEAK: Delay de 2 segundos antes de hablar
  // ==========================================
  const uint32_t START_DELAY_MS = 2000;
  
  if (nowMs - speakingPlan.startedAtMs < START_DELAY_MS)
  {
    setTarget(mouthAxis, MOUTH_CLOSED);
    return; // Congela la animación de hablar hasta que pasen los 2 segundos
  }

  // Se resta el delay para que la duración original fluya correctamente
  uint32_t elapsed = nowMs - (speakingPlan.startedAtMs + START_DELAY_MS);
  
  if (elapsed >= (uint32_t)speakingPlan.durationMs)
  {
    speakingPlan.active = false;
    setTarget(mouthAxis, MOUTH_CLOSED);
    return;
  }

  int left = triangleWave(nowMs, 760, ARM_MIN, ARM_MAX);
  int right = ARM_MIN + ARM_MAX - left;
  setTarget(leftArmAxis, left);
  setTarget(rightArmAxis, right);

  setTarget(leftEyeAxis, LEFT_EYE_CENTER);
  setTarget(rightEyeAxis, RIGHT_EYE_CENTER);

  if (nowMs - speakingPlan.lastMouthTickMs >= (uint32_t)speakingPlan.tickMs)
  {
    speakingPlan.lastMouthTickMs = nowMs;
    int randomChoice = random(0, 100);

    if (randomChoice < 20)
      setTarget(mouthAxis, MOUTH_CLOSED);
    else if (randomChoice < 60)
      setTarget(mouthAxis, MOUTH_HALF);
    else
      setTarget(mouthAxis, MOUTH_OPEN);
  }
}

void updateIdleAnimation()
{
  // Idle means no active animation. Keep current targets.
}

void updateStateMachine()
{
  uint32_t nowMs = millis();

  if (currentState == STATE_LISTENING)
    updateListeningAnimation(nowMs);
  else if (currentState == STATE_THINKING)
    updateThinkingAnimation(nowMs);
  else if (currentState == STATE_SPEAKING)
    updateSpeakingAnimation(nowMs);
  else
    updateIdleAnimation();

  // ==========================================
  // APLICACIÓN DE SUAVIDAD (TRUE = SUAVE)
  // Únicamente la cabeza (boca) recibe suavidad.
  // ==========================================
  stepAxis(mouthAxis, true);  
  
  stepAxis(leftArmAxis);
  stepAxis(rightArmAxis);
  stepAxis(leftEyeAxis);
  stepAxis(rightEyeAxis);
}

//
// Mouth control for manual action endpoint compatibility
//

void mouthOpen()
{
  Serial.println("MOUTH OPEN");
  setTarget(mouthAxis, MOUTH_OPEN);
}

void mouthHalf()
{
  Serial.println("MOUTH HALF");
  setTarget(mouthAxis, MOUTH_HALF);
}

void mouthCloseSlow()
{
  Serial.println("MOUTH CLOSE");
  setTarget(mouthAxis, MOUTH_CLOSED);
}

//
// HTTP handlers
//

void handleState()
{

  if (!server.hasArg("plain"))
  {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  String body = server.arg("plain");

  Serial.println("STATE PAYLOAD:");
  Serial.println(body);

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err)
  {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  const char* state = doc["state"];
  if (state == nullptr)
  {
    server.send(400, "text/plain", "Missing state");
    return;
  }

  String s = String(state);

  if (s == "SPEAKING")
    setRobotState(STATE_SPEAKING);
  else if (s == "THINKING")
    setRobotState(STATE_THINKING);
  else if (s == "LISTENING")
    setRobotState(STATE_LISTENING);
  else if (s == "IDLE")
    setRobotState(STATE_IDLE);

  server.send(200, "text/plain", "OK");
}

void handleSpeakingPlan()
{
  if (!server.hasArg("plain"))
  {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  String body = server.arg("plain");

  Serial.println("SPEAKING PLAN PAYLOAD:");
  Serial.println(body);

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err)
  {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  int wordCount = doc["word_count"] | 0;
  int durationMs = doc["estimated_duration_ms"] | (wordCount * 360);
  int tickMs = doc["recommended_tick_ms"] | 140;
  int go = doc["go"] | 0;

  if (wordCount <= 0)
    wordCount = 1;
  if (durationMs < 500)
    durationMs = 500;

  tickMs = clampToRange(tickMs, 90, 260);

  speakingPlan.wordCount = wordCount;
  speakingPlan.durationMs = durationMs;
  speakingPlan.tickMs = tickMs;
  speakingPlan.active = false;

  Serial.print("PLAN words=");
  Serial.print(speakingPlan.wordCount);
  Serial.print(" durationMs=");
  Serial.print(speakingPlan.durationMs);
  Serial.print(" tickMs=");
  Serial.println(speakingPlan.tickMs);

  if (go == 1)
  {
    setRobotState(STATE_SPEAKING);
    speakingPlan.active = true;
    speakingPlan.startedAtMs = millis();
    speakingPlan.lastMouthTickMs = 0;
  }

  server.send(200, "text/plain", "OK");
}

void handleSignal()
{
  int go = 1;
  if (server.hasArg("plain"))
  {
    StaticJsonDocument<128> doc;
    if (!deserializeJson(doc, server.arg("plain")))
      go = doc["go"] | 1;
  }

  if (go == 1)
  {
    Serial.println("GO SIGNAL RECEIVED");
    setRobotState(STATE_SPEAKING);
    speakingPlan.active = true;
    speakingPlan.startedAtMs = millis();
    speakingPlan.lastMouthTickMs = 0;
  }

  server.send(200, "text/plain", "OK");
}

void handleAction()
{
  if (!server.hasArg("plain"))
  {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  String body = server.arg("plain");

  StaticJsonDocument<256> doc;

  if (deserializeJson(doc, body))
  {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  const char* action = doc["action"];

  if (action == nullptr)
  {
    server.send(400, "text/plain", "Missing action");
    return;
  }

  String a = String(action);

  if (a == "OPEN")
    mouthOpen();
  else if (a == "HALF")
    mouthHalf();
  else if (a == "CLOSE")
    mouthCloseSlow();

  if (a == "SPEAKING")
    setRobotState(STATE_SPEAKING);
  else if (a == "THINKING")
    setRobotState(STATE_THINKING);
  else if (a == "LISTENING")
    setRobotState(STATE_LISTENING);
  else if (a == "IDLE")
    setRobotState(STATE_IDLE);

  server.send(200, "text/plain", "OK");
}

//
// Setup
//

void setup()
{
  Serial.begin(115200);

  randomSeed((uint32_t)esp_random());

  // Required by ESP32Servo for stable multi-servo control.
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  attachAxis(mouthAxis, "MOUTH");
  attachAxis(leftArmAxis, "LEFT_ARM");
  attachAxis(rightArmAxis, "RIGHT_ARM");
  attachAxis(leftEyeAxis, "LEFT_EYE");
  attachAxis(rightEyeAxis, "RIGHT_EYE");

  //
  // Start WiFi Access Point
  //

  WiFi.softAP(ssid, password);

  Serial.println("Access Point started");

  Serial.print("IP address: ");
  Serial.println(WiFi.softAPIP());

  //
  // HTTP routes
  //

  server.on("/state", HTTP_POST, handleState);
  server.on("/speaking-plan", HTTP_POST, handleSpeakingPlan);

  server.on("/signal", HTTP_POST, handleSignal);

  server.on("/action", HTTP_POST, handleAction);

  server.begin();

  Serial.println("HTTP server started");

  setRobotState(STATE_IDLE);
}

//
// Loop
//

void loop()
{
  server.handleClient();
  updateStateMachine();
}