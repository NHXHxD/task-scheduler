import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    filters,
)
import sqlite3
from datetime import datetime, timedelta
import pytz

# Set your desired local timezone here.
LOCAL_TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")  # Example: ICT (UTC+7)

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO  # Change to DEBUG for even more detail
)
logger = logging.getLogger(__name__)

# Database setup
conn = sqlite3.connect("todo.db", check_same_thread=False)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        task TEXT,
        due_time TEXT
    )"""
)
conn.commit()

# Constants for ConversationHandler states
ADD_TASK, SET_REMINDER = range(2)

def convert_utc_to_local(utc_str: str) -> str:
    """
    Convert a UTC datetime string (in the format "%Y-%m-%d %H:%M:%S")
    to a local time string including timezone abbreviation.
    """
    try:
        dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
        dt_utc = pytz.utc.localize(dt_utc)
        dt_local = dt_utc.astimezone(LOCAL_TIMEZONE)
        return dt_local.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        logger.error("Error converting time: %s", e)
        return utc_str  # Fallback: return the original string if error

# Command: /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🌟 Welcome to your Personal Assistant Bot! 🌟\n\n"
        "Here's what I can do:\n"
        "/addtask - Add a new task to your to-do list\n"
        "/listtasks - List all your tasks\n"
        "/deletetask - Delete a task by its ID\n"
        "/setreminder - Set a reminder for a task\n"
        "/help - Show this help message"
    )

# Command: /addtask
async def add_task(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Please enter the task you want to add:")
    return ADD_TASK

async def save_task(update: Update, context: CallbackContext) -> int:
    task = update.message.text.strip()
    if task:
        c.execute(
            "INSERT INTO tasks (chat_id, task, due_time) VALUES (?, ?, ?)",
            (update.message.chat_id, task, None),
        )
        conn.commit()
        await update.message.reply_text(f"✅ Task added: {task}")
    else:
        await update.message.reply_text("❌ Task cannot be empty. Please try again.")
    return ConversationHandler.END

# Command: /listtasks
async def list_tasks(update: Update, context: CallbackContext) -> None:
    c.execute(
        "SELECT id, task, due_time FROM tasks WHERE chat_id = ? ORDER BY id",
        (update.message.chat_id,),
    )
    tasks = c.fetchall()
    if tasks:
        task_list = []
        for task in tasks:
            task_id, task_text, due_time = task
            if due_time:
                # Convert the UTC time to local time
                due_local = convert_utc_to_local(due_time)
                due_display = f"(Due: {due_local})"
            else:
                due_display = ""
            task_list.append(f"📌 {task_id}. {task_text} {due_display}")
        await update.message.reply_text("📋 Your tasks:\n" + "\n".join(task_list))
    else:
        await update.message.reply_text("🎉 You have no tasks!")

# Command: /deletetask
async def delete_task(update: Update, context: CallbackContext) -> None:
    try:
        task_id = int(context.args[0])
        
        # First, verify the task exists
        c.execute(
            "SELECT id FROM tasks WHERE id = ? AND chat_id = ?",
            (task_id, update.message.chat_id),
        )
        if not c.fetchone():
            await update.message.reply_text("❌ Task not found.")
            return

        # Delete the task
        c.execute(
            "DELETE FROM tasks WHERE id = ? AND chat_id = ?",
            (task_id, update.message.chat_id),
        )
        conn.commit()
        
        # Update all tasks with higher IDs
        c.execute(
            """
            UPDATE tasks 
            SET id = id - 1 
            WHERE chat_id = ? AND id > ?
            """,
            (update.message.chat_id, task_id),
        )
        conn.commit()
        
        await update.message.reply_text(f"✅ Task {task_id} deleted and IDs reorganized.")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage: /deletetask <task_id>")

# Command: /setreminder
async def set_reminder(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Please enter the task ID and the reminder time in the format:\n"
        "<task_id> <time_in_minutes>\n\n"
        "Example: 1 30 (reminds you in 30 minutes for task ID 1)"
    )
    return SET_REMINDER

async def save_reminder(update: Update, context: CallbackContext) -> int:
    try:
        input_data = update.message.text.strip().split()
        if len(input_data) < 2:
            raise ValueError("Insufficient arguments")
        task_id = int(input_data[0])
        minutes = int(input_data[1])
        logger.info("Received /setreminder for task_id %d with delay %d minutes", task_id, minutes)
        
        # Verify that the task exists
        c.execute(
            "SELECT task FROM tasks WHERE id = ? AND chat_id = ?",
            (task_id, update.message.chat_id),
        )
        task = c.fetchone()
        if not task:
            await update.message.reply_text("❌ Task not found.")
            return ConversationHandler.END

        # Calculate due time in UTC and store it
        due_time = (datetime.now(pytz.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "UPDATE tasks SET due_time = ? WHERE id = ? AND chat_id = ?",
            (due_time, task_id, update.message.chat_id),
        )
        conn.commit()
        
        logger.info("Task %d updated with due_time %s", task_id, due_time)
        
        # Schedule the reminder using the application's job queue.
        context.application.job_queue.run_once(
            send_reminder,
            when=timedelta(minutes=minutes),
            chat_id=update.message.chat_id,
            name=str(task_id),
            data={"task_name": task[0]}
        )
        logger.info("Scheduled reminder for task %d", task_id)
        
        await update.message.reply_text(
            f"⏰ Reminder set for task {task_id} in {minutes} minutes."
        )
    except Exception as e:
        logger.exception("Error in save_reminder")
        await update.message.reply_text(f"❌ Invalid format or error: {e}")
    return ConversationHandler.END

async def send_reminder(context: CallbackContext) -> None:
    job = context.job
    task_name = job.data.get("task_name")
    chat_id = job.chat_id
    logger.info("Sending reminder for task: %s", task_name)
    if task_name and chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔔 Reminder: {task_name}"
        )

# Command: /help
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🤖 Here's how to use me:\n\n"
        "/start - Start the bot\n"
        "/addtask - Add a new task\n"
        "/listtasks - List all tasks\n"
        "/deletetask <task_id> - Delete a task\n"
        "/setreminder - Set a reminder for a task\n"
        "/help - Show this help message"
    )

# Enhanced error handler with detailed logging
async def error(update: object, context: CallbackContext) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and getattr(update, "message", None):
        await update.message.reply_text(f"❌ An error occurred: {context.error}")

# Main function
def main() -> None:
    # Replace 'YOUR_TOKEN' with bot's token.
    application = Application.builder().token("YOUR_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("addtask", add_task),
            CommandHandler("setreminder", set_reminder),
        ],
        states={
            ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
            SET_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reminder)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("listtasks", list_tasks))
    application.add_handler(CommandHandler("deletetask", delete_task))
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error)

    application.run_polling()

if __name__ == "__main__":
    main()
