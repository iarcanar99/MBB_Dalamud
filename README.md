<div align="center">

<img src="icon.png" alt="Magicite Babel Icon" width="128" height="128">

# Magicite Babel - Dalamud Version

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-1.4.10.4-blue.svg)](https://github.com/iarcanar99/MBB_Dalamud)
[![FFXIV](https://img.shields.io/badge/FFXIV-Compatible-green.svg)](https://www.finalfantasyxiv.com/)
[![Dalamud](https://img.shields.io/badge/Dalamud-Plugin-purple.svg)](https://github.com/goatcorp/Dalamud)

</div>

Real-time Thai translation system for Final Fantasy XIV using advanced text hook technology. Provides Netflix-quality translation with intelligent character database and seamless gameplay integration.

## ✨ Features

- **🎯 Real-time Text Hook** - Direct game text capture, no OCR needed
- **🧠 Smart Character Database** - Personality, gender, and terminology aware translation
- **🎨 Modern UI System** - Elegant interface with customizable themes
- **⚡ High Performance** - Optimized for smooth gameplay experience
- **🔧 Easy Setup** - Simple manual installation process

## 🚀 Installation Guide

### Prerequisites

1. **Final Fantasy XIV** with **XIVLauncher** and **Dalamud**
2. **Python 3.8+** - [Download from python.org](https://www.python.org/downloads/)
3. **Gemini API Key** (Free) - [Get from Google AI Studio](https://ai.google.dev/)

### Step 1: Clone Repository

```bash
git clone https://github.com/iarcanar99/MBB_Dalamud.git
cd MBB_Dalamud
```

### Step 2: Install Python Application

1. **Install Python dependencies:**
   ```bash
   cd python-app
   pip install requests tkinter pillow python-dotenv
   ```

2. **Setup API Key:**
   ```bash
   # Copy the example environment file
   copy .env.example .env

   # Edit .env file and add your Gemini API key:
   # GEMINI_API_KEY=your_api_key_here
   ```

3. **Test Python application:**
   ```bash
   python MBB.py
   ```

### Step 3: Install Dalamud Plugin

**Manual Installation via Dalamud UI:**

1. **In FFXIV, open Plugin Installer:**
   - Type `/xlplugins` in chat, or
   - Type `/xlsettings` → Click "Plugin Installer"

2. **Install from file:**
   - Click "Settings" tab in Plugin Installer
   - Click "Install Plugin from File"
   - Navigate to your cloned repository folder
   - **Important:** Select the exact path: `[Your_Clone_Location]/MBB_Dalamud/dalamud-plugin/DalamudMBBBridge/bin/Release/win-x64/DalamudMBBBridge.dll`
   - Click "Open"

   > **Note:** The exact path depends on where you cloned the repository. Make sure to navigate to the correct `bin/Release/win-x64/` folder to ensure proper icon display and functionality.

3. **Verify installation:**
   - Go back to "Installed Plugins" tab
   - You should see "Mgicite Babel v1.4.10.4 Thai Version" in the list
   - Make sure it's enabled (checkbox checked)

### Step 4: Start Using

1. **Launch FFXIV** with XIVLauncher + Dalamud
2. **Start Python app** first: `python MBB.py`
3. **In FFXIV, type:** `/mbb` to open the interface
4. **Check connection** - You should see "🟢 Bridge Connected"
5. **Start translation** - Click "START" or type `/mbb launch`

## 🔑 Getting Your Free Gemini API Key

1. **Visit Google AI Studio:** https://ai.google.dev/
2. **Click "Get API Key"** → "Create API Key"
3. **Select or create project** → "Create API Key in new project"
4. **Copy your API key** - It starts with `AIza...`
5. **Add to .env file:**
   ```
   GEMINI_API_KEY=AIzaSyD...your_key_here
   ```

> **Note:** Gemini API is free with generous limits (15 requests/minute, 1 million tokens/day)

## 📁 Project Structure

```
MBB_Dalamud/
├── python-app/              # Main Python application
│   ├── MBB.py              # Main launcher
│   ├── *.py                # Core modules
│   ├── assets/             # Images, fonts
│   └── .env.example        # API key template
├── dalamud-plugin/         # FFXIV Plugin
│   └── DalamudMBBBridge/   # C# plugin source
├── README.md               # This file
└── .gitignore             # Git exclusions
```

## 🎮 Usage

### Basic Commands
- `/mbb` - Open main interface
- `/mbb launch` - Start translation
- `/mbb status` - Check connection status

### Key Features
- **Auto-show/hide UI** - Appears when needed
- **Theme customization** - Multiple color schemes
- **Multi-area support** - A/B/C content areas
- **Smart text filtering** - Intelligent duplicate prevention

## 🛠️ Troubleshooting

### Connection Issues
- Ensure both Python app and FFXIV are running
- Check Windows Firewall settings
- Verify Dalamud plugin is enabled

### Translation Issues
- Verify Gemini API key is correct
- Check internet connection
- Monitor API rate limits

### Performance Issues
- Lower translation speed in settings
- Reduce UI update frequency
- Check system resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- **Final Fantasy XIV** by Square Enix
- **Dalamud** framework by goatcorp
- **XIVLauncher** community
- **Google Gemini AI** for translation services

---

<div align="center">

**Made with ❤️ for the FFXIV Thai community**

[⭐ Star this repo](https://github.com/iarcanar99/MBB_Dalamud) | [🐛 Report Issues](https://github.com/iarcanar99/MBB_Dalamud/issues)

</div>