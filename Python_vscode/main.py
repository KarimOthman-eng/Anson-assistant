import requests
import time
import pygame
import winsound
from groq import Groq
import os

# =================  CONFIGURATION =================
BLYNK_AUTH_TOKEN = "..."
GROQ_API_KEY     = "..."
ELEVENLABS_API_KEY = "..."


BLYNK_SERVER     = "..."
VOICE_ID         = "..." 

# --- DATASTREAM MAPPING ---
PIN_AI_OUTPUT   = "V0"  # String: AI reply
PIN_LED         = "V1"  # Int: Light
PIN_CHAT_INPUT  = "V2"  # String: Chat
PIN_DISTANCE    = "V3"  # Double: Proximity
PIN_TEMP        = "V5"  # Double: Temperature
PIN_ACCEL       = "V6"  # Double: Acceleration (Theft)
PIN_SEC_SWITCH  = "V7"  # Int: Security Switch (0/1)
PIN_HUMIDITY = "V4" # Double: Humidity (NOT USED)
# --- THRESHOLDS ---
TEMP_HIGH_LIMIT = 40.0
DIST_CRASH_LIMIT = 4.0
ACCEL_THEFT_LIMIT = 10.0

# ================= INITIALIZATION =================
client = Groq(api_key=GROQ_API_KEY)
pygame.mixer.init()

# GLOBAL VARIABLES
security_active = False 

def play_sfx(alert_type="normal"):
    """Plays sci-fi beeps"""
    try:
        if alert_type == "alarm":
            for _ in range(3): winsound.Beep(3000, 100); time.sleep(0.05)
        else:
            winsound.Beep(2500, 80); winsound.Beep(2800, 100)
    except: pass

def speak_elevenlabs(text, is_alarm=False):
    """Generates voice using ElevenLabs"""
    print(f" ANSON: {text}")
    play_sfx("alarm" if is_alarm else "normal")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {
        "text": text, 
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.35, "similarity_boost": 0.8}
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with open("voice.mp3", 'wb') as f: f.write(response.content)
            pygame.mixer.music.load("voice.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): time.sleep(0.1)
            pygame.mixer.music.unload()
    except Exception as e: print(e)

# =================  BLYNK TOOLS =================
def blynk_read_float(pin, default=0.0):
    try:
        r = requests.get(f"{BLYNK_SERVER}get?token={BLYNK_AUTH_TOKEN}&{pin}")
        if r.status_code == 200 and r.text not in ["", "None"]: return float(r.text)
        return default
    except: return default

def blynk_read_str(pin):
    try:
        r = requests.get(f"{BLYNK_SERVER}get?token={BLYNK_AUTH_TOKEN}&{pin}")
        return r.text if r.status_code == 200 and r.text != "None" else None
    except: return None

def blynk_write(pin, value):
    try: requests.get(f"{BLYNK_SERVER}update?token={BLYNK_AUTH_TOKEN}&{pin}={value}")
    except: pass

# =================  AI  =================
def ask_groq(user_msg, is_sec):
    status = "SECURITY ACTIVE" if is_sec else "PATROL MODE"
    
    #  INSTRUCTION: Talk about ANY subject, but keep personality strict
    system_instruction = (
        f"You are ANSON, you are created by karim OTHMAN,a smart AI integrated into a bike. Status: {status}. "
        f"Temperature={temp_val}°C, Humidity={humidity_val}% ,Distance={dist_val},Acceleration={accel_val}"
        f"COMMANDER SAYS: {user_msg}"

        "Your Rules:"
        "1. You are a bike assistent."
        "2. You must maintain your personality: Strict, Professional, Female, slightly robotic."
        "3. Do NOT say you are just a bike AI. You are intelligent."
        "4. If the user asks for a specific bike command, use these tags:"
        "   - 'Activate security'or simular -> End reply with [SEC_ON]"
        "   - 'Deactivate security' simular -> End reply with [SEC_OFF]"
        "   - 'Light ON' or simular -> End reply with [LED_ON]"
        "   - 'Light OFF' or simular -> End reply with [LED_OFF]"
        "5. Keep answers concise (under 2 sentences) for voice speed."
        "6. if i insult you, insult me imediatly with a harsh response without says how dare you."
    )


    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": user_msg}],
            model="llama-3.3-70b-versatile", temperature=0.7, max_tokens=150
        )
        return completion.choices[0].message.content
    except: return "Connection failure."

# =================  MAIN LOOP =================
print("ANSON ONLINE. FULL CONVERSATION MODE ACTIVE. ")
speak_elevenlabs("Anson online. Ready for conversation.")

last_temp_alert = 0
last_prox_alert = 0
last_theft_alert = 0

while True:
    try:
        current_time = time.time()

        # --- 1. SENSOR READS ---
        accel_val = blynk_read_float(PIN_ACCEL, 0.0) 
        v7_switch = blynk_read_float(PIN_SEC_SWITCH, 0.0)
        dist_val  = blynk_read_float(PIN_DISTANCE, 100.0)
        temp_val  = blynk_read_float(PIN_TEMP, 20.0)
        humidity_val = blynk_read_float(PIN_HUMIDITY, 50.0)  # NOT USED
        # --- 2. SECURITY SYNC (V7 Switch) ---
        if v7_switch == 1.0 and not security_active:
            security_active = True
            print(" Security ON (V7)")
            speak_elevenlabs("Security engaged.")
        elif v7_switch == 0.0 and security_active:
            security_active = False
            print(" Security OFF (V7)")
            speak_elevenlabs("Security disengaged.")

        # --- 3. CHAT HANDLING (TEXT) ---
        user_input = blynk_read_str(PIN_CHAT_INPUT)

        if user_input and user_input not in ["0", "", "None"]:
            print(f"\n User: {user_input}")
            blynk_write(PIN_CHAT_INPUT, "") # Clear Input

            # Ask Groq (She can now answer anything)
            reply = ask_groq(user_input,security_active)
        
            
            # Process Control Tags
            if "[SEC_ON]" in reply: 
                security_active=True; blynk_write(PIN_SEC_SWITCH, 1); reply=reply.replace("[SEC_ON]","")
            if "[SEC_OFF]" in reply: 
                security_active=False; blynk_write(PIN_SEC_SWITCH, 0); reply=reply.replace("[SEC_OFF]","")
            if "[LED_ON]" in reply: 
                blynk_write(PIN_LED, 1); reply=reply.replace("[LED_ON]","")
            if "[LED_OFF]" in reply: 
                blynk_write(PIN_LED, 0); reply=reply.replace("[LED_OFF]","")

            # Speak and Show Result
            blynk_write(PIN_AI_OUTPUT, reply)
            speak_elevenlabs(reply.strip())

        # --- 4. ALERTS ---
        if security_active:
            # Theft Alert (V6 > 10)
            if abs(accel_val) > ACCEL_THEFT_LIMIT and (current_time - last_theft_alert > 5):
                msg = "VOL ALERT! Violation detected!"
                print(f" {msg}"); blynk_write(PIN_LED, 1); speak_elevenlabs(msg, True);
                time.sleep(0.5); blynk_write(PIN_LED, 0); last_theft_alert = current_time

        # Crash Alert (V3 < 4)
        if dist_val < DIST_CRASH_LIMIT and (current_time - last_prox_alert > 5):
            msg = "Crash imminent!"
            speak_elevenlabs(msg, True); last_prox_alert = current_time

        # Temperature Alerts (V5)
        if current_time - last_temp_alert > 15:
            if temp_val > TEMP_HIGH_LIMIT: 
                speak_elevenlabs("Critical heat warning!", True); last_temp_alert = current_time
            elif temp_val < 0:
                speak_elevenlabs("Freezing temperatures detected.", True); last_temp_alert = current_time

        time.sleep(0.5)

    except KeyboardInterrupt: break
    except Exception as e: print(e); time.sleep(1)