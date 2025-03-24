# 🎵 Spotify Album of the Week – GUI Tool

This is a simple PyQt5-based GUI application for adding and processing Spotify album URLs. It allows users to input an album URL, gather album metadata, and append relevant information to an Excel master list.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/davidgreenblott/spotify_aotw
cd spotify_aotw
```

### 2. Set Up Mamba Enviornment
This project uses conda/mamba for enviornment managment. Use the provided `enviornment.yml` to install all dependencies.

```bash
mamba env create -f environment.yml
```

and then active the environment
```bash
mamba activate spotify-env
```

### 3. Run the App
Once the mamba enviornment is active, launch the PyQt5 GUI:
```bash
python add_album_gui.py
```