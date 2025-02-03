# Personal Assistant Telegram Bot

A Telegram bot that acts as your personal assistant for managing tasks. This bot allows you to add tasks, list, delete, and set reminders. The reminders are scheduled using a job queue and time values are stored in UTC by default, which can be modified to display local timezone.

## Features

- **Add Task:** Create new tasks for your to-do list.
- **List Tasks:** Display all your tasks with due dates converted to your local time.
- **Delete Task:** Remove tasks by specifying their ID. The task IDs are renumbered after deletion.
- **Set Reminder:** Set a reminder for any task by specifying a delay in minutes. The bot sends you a reminder message when the time comes.
- **Timezone Handling:** All due times are stored in UTC and converted to your specified local timezone.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/NHXHxD/task-scheduler
   cd task-scheduler

2. **Install Dependencies:**

    ```bash
    pip install python-telegram-bot pytz

## Configuration
1. Obtain a Telegram Bot Token:
Create your bot using BotFather on Telegram.
Copy the token provided by BotFather.

2. Set the Bot Token:
Open the soure file (taskScheduler.py) and replace "YOUR_TOKEN" with your bot token.

3. Set the Local Timezone:
By default, the bot converts UTC times to the Asia/Ho_Chi_Minh timezone.
To change the timezone, update the LOCAL_TIMEZONE variable in bot.py

    ```python
    LOCAL_TIMEZONE = pytz.timezone("Your/Timezone")

Example:

    ```python
    LOCAL_TIMEZONE = pytz.timezone("America/New_York")

