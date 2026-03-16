# 🔑 Needed API Keys

Currently, **Atlas & ARIA are configured to run 100% FREE** using local models and open-source libraries.
However, to unlock "Premium" capabilities (Advanced Voice, proprietary models), you can optionally add the following keys.

## 🎙️ Voice & Audio (Optional)

### 1. ElevenLabs (For "Human-Like" TTS)
**Purpose:** Replaces the robotic Google voice with hyper-realistic AI voices.
- **Cost:** Free tier available (10k characters/month).
- **How to get:**
  1. Go to [elevenlabs.io](https://elevenlabs.io).
  2. Sign up.
  3. Click your profile icon → "Profile + API Key".
  4. Copy the API Key.
- **Config:** `ELEVENLABS_API_KEY`

### 2. OpenAI (For "Whisper" STT)
**Purpose:** Provides state-of-the-art speech recognition (better than Google Free).
- **Cost:** Pay-per-use (very cheap).
- **How to get:**
  1. Go to [platform.openai.com](https://platform.openai.com/api-keys).
  2. Sign up/Log in.
  3. Create a new secret key.
- **Config:** `OPENAI_API_KEY`

---

## 🔌 Integrations (Optional)

### 3. Telegram Bot
**Purpose:** Chat with ARIA via Telegram app.
- **Cost:** Free.
- **How to get:**
  1. Open Telegram.
  2. Search for **@BotFather**.
  3. Send command `/newbot`.
  4. Follow instructions to get the **Token**.
- **Config:** `TELEGRAM_BOT_TOKEN`

### 4. Discord Bot
**Purpose:** Add ARIA to a Discord server.
- **Cost:** Free.
- **How to get:**
  1. Go to [Discord Developer Portal](https://discord.com/developers/applications).
  2. create "New Application".
  3. Go to "Bot" tab -> "Add Bot".
  4. Copy **Token**.
- **Config:** `DISCORD_BOT_TOKEN`

### 5. Notion
**Purpose:** Let ARIA read/write your Notion pages.
- **Cost:** Free.
- **How to get:**
  1. Go to [Notion Integrations](https://www.notion.so/my-integrations).
  2. Create new integration.
  3. Copy **Internal Integration Secret**.
- **Config:** `NOTION_API_KEY`

---

## 🔒 Configuration
Add these keys to either:
1. `python/src/atlas/assistants/aria/config/api_keys.py`
2. Or your system Environment Variables.
