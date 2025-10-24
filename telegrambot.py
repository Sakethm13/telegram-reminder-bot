# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import pytz

# =================== CONFIG ===================
TOKEN = "8267512155:AAEzkgUm-oGss-P7Xu399uL7Zngy3HE29KQ"  # 🔹 Replace with your bot token
TIMEZONE = pytz.timezone("Asia/Kolkata")

# =================== IN-MEMORY DATA ===================
# Each user has their own reminder set
user_reminders = {}  # {chat_id: {"recurring": [], "temp": [], "weekly": []}}

# =================== COMMAND HANDLERS ===================

def start(update: Update, context: CallbackContext):
    msg = (
        "Welcome jii! 🚀\n\n"
        "Available Commands:\n"
        "/setreminder HH MM text → daily reminder\n"
        "/settemp HH MM text → one-time reminder (today only)\n"
        "/setweekly DAY HH MM text → weekly reminder\n"
        "/list → show all reminders\n"
        "/dailysummary → enable daily summary at 9:00 AM\n"
        "/deletereminder ID → delete a reminder by its number"
    )
    update.message.reply_text(msg)


# ========== DAILY REMINDER ==========
def set_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in user_reminders:
        user_reminders[chat_id] = {"recurring": [], "temp": [], "weekly": []}

    try:
        if len(context.args) < 3:
            update.message.reply_text("❌ Usage: /setreminder HH MM text")
            return

        hour = int(context.args[0])
        minute = int(context.args[1])
        text = " ".join(context.args[2:])

        user_reminders[chat_id]["recurring"].append({"hour": hour, "minute": minute, "text": text})

        trigger = CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE)
        scheduler.add_job(
            lambda: context.bot.send_message(chat_id, f"⏰ Reminder: {text}"),
            trigger=trigger
        )

        update.message.reply_text(f"✅ Daily reminder set at {hour:02d}:{minute:02d} → {text}")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}\n❌ Usage: /setreminder HH MM text")


# ========== ONE-TIME REMINDER ==========
def set_temp_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in user_reminders:
        user_reminders[chat_id] = {"recurring": [], "temp": [], "weekly": []}

    try:
        if len(context.args) < 3:
            update.message.reply_text("❌ Usage: /settemp HH MM text")
            return

        hour = int(context.args[0])
        minute = int(context.args[1])
        text = " ".join(context.args[2:])

        now = datetime.now(TIMEZONE)
        remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_time < now:
            remind_time += timedelta(days=1)

        user_reminders[chat_id]["temp"].append({"time": str(remind_time), "text": text})

        trigger = DateTrigger(run_date=remind_time)
        scheduler.add_job(
            lambda: context.bot.send_message(chat_id, f"⏳ Reminder: {text}"),
            trigger=trigger
        )

        update.message.reply_text(f"✅ One-time reminder set for {remind_time.strftime('%Y-%m-%d %H:%M')} → {text}")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}\n❌ Usage: /settemp HH MM text")


# ========== WEEKLY REMINDER ==========
def set_weekly(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id not in user_reminders:
        user_reminders[chat_id] = {"recurring": [], "temp": [], "weekly": []}

    try:
        if len(context.args) < 4:
            update.message.reply_text("❌ Usage: /setweekly DAY HH MM text")
            return

        day = context.args[0].capitalize()
        hour = int(context.args[1])
        minute = int(context.args[2])
        text = " ".join(context.args[3:])

        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if day not in valid_days:
            update.message.reply_text("❌ Invalid day name (use e.g. Monday)")
            return

        user_reminders[chat_id]["weekly"].append({"day": day, "hour": hour, "minute": minute, "text": text})

        day_index = valid_days.index(day)
        trigger = CronTrigger(day_of_week=day_index, hour=hour, minute=minute, timezone=TIMEZONE)

        scheduler.add_job(
            lambda: context.bot.send_message(chat_id, f"📅 Weekly Reminder ({day}): {text}"),
            trigger=trigger
        )
        update.message.reply_text(f"✅ Weekly reminder set for {day} at {hour:02d}:{minute:02d} → {text}")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {e}\n❌ Usage: /setweekly DAY HH MM text")


# ========== LIST REMINDERS ==========
def list_reminders(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_reminders.get(chat_id, {"recurring": [], "temp": [], "weekly": []})
    try:
        msg = "📋 *Your Reminders:*\n"
        idx = 1

        if data["recurring"]:
            msg += "\n🕒 Daily:\n"
            for r in data["recurring"]:
                msg += f"{idx}. {r['hour']:02d}:{r['minute']:02d} → {r['text']}\n"
                idx += 1

        if data["temp"]:
            msg += "\n⏳ One-Time:\n"
            for r in data["temp"]:
                msg += f"{idx}. {r['time']} → {r['text']}\n"
                idx += 1

        if data["weekly"]:
            msg += "\n📆 Weekly:\n"
            for r in data["weekly"]:
                msg += f"{idx}. {r['day']} {r['hour']:02d}:{r['minute']:02d} → {r['text']}\n"
                idx += 1

        if idx == 1:
            msg = "😴 No reminders yet."

        update.message.reply_text(msg)

    except Exception as e:
        update.message.reply_text(f"⚠️ Error while listing reminders: {e}")


# ========== DELETE REMINDER ==========
def delete_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    data = user_reminders.get(chat_id, {"recurring": [], "temp": [], "weekly": []})

    try:
        args = context.args
        if not args:
            update.message.reply_text("❌ Usage: /deletereminder ID")
            return

        rid = int(args[0]) - 1
        all_items = (
            [(r, "recurring") for r in data["recurring"]] +
            [(r, "temp") for r in data["temp"]] +
            [(r, "weekly") for r in data["weekly"]]
        )

        if rid < 0 or rid >= len(all_items):
            update.message.reply_text("⚠️ Invalid ID!")
            return

        _, category = all_items[rid]

        if category == "recurring":
            data["recurring"].pop(rid)
        elif category == "temp":
            data["temp"].pop(rid - len(data["recurring"]))
        elif category == "weekly":
            data["weekly"].pop(rid - len(data["recurring"]) - len(data["temp"]))

        update.message.reply_text(f"✅ Reminder {args[0]} deleted successfully!")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error while deleting reminder: {e}")


# ========== DAILY SUMMARY ==========
def daily_summary(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    scheduler.add_job(
        lambda: context.bot.send_message(chat_id, "📅 Daily Summary: Don’t forget to check your reminders!"),
        trigger=CronTrigger(hour=9, minute=0, timezone=TIMEZONE)
    )
    update.message.reply_text("✅ Daily summary enabled for 9:00 AM!")


# =================== MAIN ===================
scheduler = BackgroundScheduler()
scheduler.start()

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("setreminder", set_reminder))
dp.add_handler(CommandHandler("settemp", set_temp_reminder))
dp.add_handler(CommandHandler("setweekly", set_weekly))
dp.add_handler(CommandHandler("list", list_reminders))
dp.add_handler(CommandHandler("deletereminder", delete_reminder))
dp.add_handler(CommandHandler("dailysummary", daily_summary))

print("🤖 Bot is running 24x7 jii...")
updater.start_polling()
updater.idle()
