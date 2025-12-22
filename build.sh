
#!/usr/bin/env bash
# יוצאים אם יש שגיאה
set -o errexit

# התקנת ספריות פייתון
pip install -r requirements.txt

# יצירת תיקייה לתוכנות עזר
mkdir -p bin

# הורדת FFmpeg (גרסה סטטית ללינוקס)
echo "Downloading FFmpeg for Render..."
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ -C bin --strip-components=1

# כעת ffmpeg נמצא בתוך תיקיית bin/
echo "FFmpeg installed successfully!"