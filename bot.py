import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@sinhalamoviez")
HELP_MESSAGE_ID = int(os.environ.get("HELP_MESSAGE_ID", "12942"))
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))  # Your Telegram user ID

class MovieBot:
    def __init__(self):
        self.waiting_for_data = {}
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is the admin."""
        return user_id == ADMIN_USER_ID
    
    async def start(self, update: Update, context: CallbackContext):
        """Send a message when the command /start is issued."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.is_admin(user_id):
            await update.message.reply_text(
                "⛔ Access Denied!\n\n"
                "This bot is private and can only be used by the owner."
            )
            return
        
        self.waiting_for_data[user_id] = {}
        
        await update.message.reply_text(
            "🎬 Welcome to Sinhala Movies Bot! 🎬\n\n"
            "Let's create a movie post!\n\n"
            "📸 First, send me the movie poster image:"
        )
        self.waiting_for_data[user_id]['step'] = 'poster'
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle incoming messages based on the current step."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.is_admin(user_id):
            await update.message.reply_text(
                "⛔ Access Denied!\n\n"
                "This bot is private."
            )
            return
        
        if user_id not in self.waiting_for_data:
            await update.message.reply_text(
                "Please use /start to begin creating a movie post."
            )
            return
        
        step = self.waiting_for_data[user_id].get('step')
        
        if step == 'poster' and update.message.photo:
            photo = update.message.photo[-1]
            self.waiting_for_data[user_id]['poster'] = photo.file_id
            self.waiting_for_data[user_id]['step'] = 'english_name'
            await update.message.reply_text(
                "✅ Poster received!\n\n"
                "📝 Now send the movie name in ENGLISH:"
            )
        
        elif step == 'english_name' and update.message.text:
            self.waiting_for_data[user_id]['english_name'] = update.message.text
            self.waiting_for_data[user_id]['step'] = 'sinhala_name'
            await update.message.reply_text(
                "✅ English name received!\n\n"
                "📝 Now send the movie name in SINHALA:"
            )
        
        elif step == 'sinhala_name' and update.message.text:
            self.waiting_for_data[user_id]['sinhala_name'] = update.message.text
            self.waiting_for_data[user_id]['step'] = 'year'
            await update.message.reply_text(
                "✅ Sinhala name received!\n\n"
                "📅 Now send the movie YEAR (e.g., 2016):"
            )
        
        elif step == 'year' and update.message.text:
            self.waiting_for_data[user_id]['year'] = update.message.text
            self.waiting_for_data[user_id]['step'] = 'deep_link'
            await update.message.reply_text(
                "✅ Year received!\n\n"
                "🔗 Now send the DEEP LINK for download:"
            )
        
        elif step == 'deep_link' and update.message.text:
            self.waiting_for_data[user_id]['deep_link'] = update.message.text
            await self.show_preview(update, context, user_id)
    
    async def show_preview(self, update: Update, context: CallbackContext, user_id: int):
        """Show preview of the post with Send button."""
        data = self.waiting_for_data[user_id]
        
        # Create the help link
        help_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}/{HELP_MESSAGE_ID}"
        
        # Create the caption preview
        caption = (
            f"<b>{data['sinhala_name']} {data['year']}</b>\n"
            f"<b>{data['english_name']} {data['year']}</b>\n\n"
            f"{CHANNEL_ID}\n\n"
            f'<blockquote><a href="{help_link}">🤖 bot ගෙන් film එක ගන්න තේරෙන්නේ නැත්නම් මෙතනින් බලන්න 👈</a></blockquote>'
        )
        
        # Create keyboard with Send and Cancel buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ SEND TO CHANNEL", callback_data=f"send_{user_id}"),
                InlineKeyboardButton("❌ CANCEL", callback_data=f"cancel_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send preview
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=data['poster'],
            caption=f"📋 PREVIEW:\n\n{caption}\n\n🔗 Download: {data['deep_link']}\n\n👆 Click 'SEND TO CHANNEL' to post this to {CHANNEL_ID}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        self.waiting_for_data[user_id]['step'] = 'preview_shown'
    
    async def handle_callback(self, update: Update, context: CallbackContext):
        """Handle button callbacks."""
        query = update.callback_query
        
        # Check if user is admin
        if not self.is_admin(query.from_user.id):
            await query.answer("⛔ Access Denied!", show_alert=True)
            return
        
        await query.answer()
        
        # Parse callback data
        action, user_id_str = query.data.split('_')
        user_id = int(user_id_str)
        
        if query.from_user.id != user_id:
            await query.answer("This button is not for you!", show_alert=True)
            return
        
        if action == "send":
            await self.send_to_channel(query, context, user_id)
        elif action == "cancel":
            await self.cancel_post(query, user_id)
    
    async def send_to_channel(self, query, context: CallbackContext, user_id: int):
        """Send the movie post to the channel."""
        data = self.waiting_for_data.get(user_id)
        
        if not data:
            await query.edit_message_caption(
                caption="❌ Session expired. Please use /start to create a new post."
            )
            return
        
        # Create the help link
        help_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}/{HELP_MESSAGE_ID}"
        
        # Create the final caption (without download link in text)
        caption = (
            f"<b>{data['sinhala_name']} {data['year']}</b>\n"
            f"<b>{data['english_name']} {data['year']}</b>\n\n"
            f"{CHANNEL_ID}\n\n"
            f'<blockquote><a href="{help_link}">🤖 bot ගෙන් film එක ගන්න තේරෙන්නේ නැත්නම් මෙතනින් බලන්න 👈</a></blockquote>'
        )
        
        # Create inline keyboard button with emoji and URL text
        keyboard = [
            [InlineKeyboardButton("🎬 DOWNLOD 📥", url=data['deep_link'])]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Send to channel
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=data['poster'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            # Update preview message
            await query.edit_message_caption(
                caption=(
                    f"✅ SUCCESS!\n\n"
                    f"Movie posted to {CHANNEL_ID}!\n\n"
                    f"🎬 {data['english_name']} ({data['year']})\n\n"
                    f"Use /start to add another movie."
                )
            )
            
        except Exception as e:
            logger.error(f"Error posting to channel: {e}")
            await query.edit_message_caption(
                caption=(
                    f"❌ ERROR!\n\n"
                    f"Failed to post: {str(e)}\n\n"
                    f"Make sure:\n"
                    f"1. Bot is admin in {CHANNEL_ID}\n"
                    f"2. Bot has permission to post\n\n"
                    f"Use /start to try again."
                )
            )
        
        # Clear user data
        if user_id in self.waiting_for_data:
            del self.waiting_for_data[user_id]
    
    async def cancel_post(self, query, user_id: int):
        """Cancel the current post."""
        if user_id in self.waiting_for_data:
            del self.waiting_for_data[user_id]
        
        await query.edit_message_caption(
            caption="❌ Post cancelled.\n\nUse /start to create a new movie post."
        )
    
    async def cancel_command(self, update: Update, context: CallbackContext):
        """Cancel the current operation via command."""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.is_admin(user_id):
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        if user_id in self.waiting_for_data:
            del self.waiting_for_data[user_id]
        await update.message.reply_text("❌ Operation cancelled. Use /start to begin again.")

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Initialize bot
    movie_bot = MovieBot()
    
    # Register handlers
    application.add_handler(CommandHandler("start", movie_bot.start))
    application.add_handler(CommandHandler("cancel", movie_bot.cancel_command))
    application.add_handler(CallbackQueryHandler(movie_bot.handle_callback))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.TEXT & ~filters.COMMAND, 
        movie_bot.handle_message
    ))
    
    # Start the bot
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
