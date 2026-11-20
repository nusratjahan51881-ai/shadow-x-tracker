import os
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify
from telegram import Bot

app = Flask(__name__)

TOKEN = os.environ["8890793243:AAHdgH9PF8aHFhLJuUrWomsgaXewig4y1LA"]
bot = Bot(8890793243:AAHdgH9PF8aHFhLJuUrWomsgaXewig4y1LA)


@app.route("/")
def home():
    return "Shadow X Tracker Online"


@app.route("/track/<int:uid>")
def tracking(uid):
    return render_template("index.html", uid=uid)


@app.route("/submit/<int:uid>", methods=["POST"])
async def submit(uid):
    data = request.get_json(silent=True) or {}

    if data.get("consent") is not True:
        return jsonify({"error": "Consent required"}), 403

    device = str(data.get("device", "Unknown"))[:150]
    browser = str(data.get("browser", "Unknown"))[:150]
    os_name = str(data.get("os", "Unknown"))[:150]
    screen = str(data.get("screen", "Unknown"))[:50]

    report = (
        "📱 DEVICE REPORT\n\n"
        f"🆔 User ID: {uid}\n"
        f"📱 Device: {device}\n"
        f"🌐 Browser: {browser}\n"
        f"💻 OS: {os_name}\n"
        f"📐 Screen: {screen}\n"
        f"🕒 Time: {datetime.now(timezone.utc).isoformat()}"
    )

    await bot.send_message(chat_id=uid, text=report)

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run()
