#!/usr/bin/env python
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os

from dotenv import load_dotenv

import logging
from logging.handlers import TimedRotatingFileHandler

import httpx
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


load_dotenv()  # take environment variables

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
filehandler = TimedRotatingFileHandler('errorlog.log', when='midnight', interval=1, backupCount=7)
filehandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'))
logging.getLogger('').addHandler(filehandler)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

CHOOSING, TYPING_REPLY, TYPING_CHOICE, DISPLAY_LESSON_INFO = range(4)

reply_keyboard = [
    # ["Age", "Favourite colour"],
    # ["Number of siblings", "Something else..."],
    ["Padel lessons"],
    ["Exit"],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def facts_to_str(user_data: dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask user for input."""
    await update.message.reply_text(
        "Hi, what would you like to know?",
        reply_markup=markup,
    )

    return CHOOSING


async def display_lesson_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    organisation_id = 'df82f4dd-fd87-4af5-9c2f-656fe1a44357'
    lessons_url = f'https://api.foys.io/trainer-booking/public/api/v1/organisations/{organisation_id}/lesson-packages'
    params = {
        'locationIds': 'f37fb2ae-bf24-44f1-9b81-61e6c0784840',
        'categoryIds': ['98', '217'],
        'daysOfWeek': ['Wednesday', 'Thursday'],
        'skipCount': '0',
        'maxResultCount': '20',
        'organisationId': organisation_id
    }

    x = httpx.get(lessons_url, params=params)
    res = x.json()

    if ("items" not in res) or len(res['items']) == 0:
        answer_text = "No options found..."
    else:
        answer_text = ""
        for item in res['items']:
            answer_text += (
                f"*{item['name']}*\n"
                f"{item['dayOfWeek']} {item['startTime'][:5]} - {item['endTime'][:5]}\n"
                f"Starting: {item['startDate'][:10]} ({item['amountOfLessons']}x)\n"
                f"{item['locationCity']} {item['locationName']}\n"
                f"Price: €{item['price']}\n"
                f"Trainer: {item['trainerName']}\n\n"
            )

    await update.message.reply_text(
        answer_text,
        parse_mode='markdown',
        reply_markup=markup,
    )

    return CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for info about the selected predefined choice."""
    text = update.message.text
    context.user_data["choice"] = text
    await update.message.reply_text(f"Your {text.lower()}? Yes, I would love to hear about that!")

    return TYPING_REPLY


async def custom_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for a description of a custom category."""
    await update.message.reply_text(
        'Alright, please send me the category first, for example "Most impressive skill"'
    )

    return TYPING_CHOICE


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""
    user_data = context.user_data
    text = update.message.text
    category = user_data["choice"]
    user_data[category] = text
    del user_data["choice"]

    await update.message.reply_text(
        "Neat! Just so you know, this is what you already told me:"
        f"{facts_to_str(user_data)}You can tell me more, or change your opinion"
        " on something.",
        reply_markup=markup,
    )

    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""
    user_data = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    await update.message.reply_text(
        f"I learned these facts about you: {facts_to_str(user_data)}Until next time!",
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


# noinspection PyTypeChecker
def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex("^(Age|Favourite colour|Number of siblings)$"), regular_choice
                ),
                MessageHandler(
                    filters.Regex("^(Padel lessons)$"), display_lesson_info
                ),
                MessageHandler(filters.Regex("^Something else...$"), custom_choice),
            ],
            # TYPING_CHOICE: [
            #     MessageHandler(
            #         filters.TEXT & ~(filters.COMMAND | filters.Regex("^Exit$")), regular_choice
            #     )
            # ],
            # TYPING_REPLY: [
            #     MessageHandler(
            #         filters.TEXT & ~(filters.COMMAND | filters.Regex("^Exit$")),
            #         received_information,
            #     )
            # ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Exit$"), done)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
