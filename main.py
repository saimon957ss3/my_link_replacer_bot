import os
import re
from telegram import Update, LinkPreviewOptions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- আপনার নতুন লিংক এবং টোকেন এখানে সরাসরি বসানো হয়েছে ---
BOT_TOKEN = "8857827625:AAH5atf8X3rktmiCKimGA4JgtFnMNNYG984"
ADMIN_LINK = "https://f999game.com"
# -------------------------------------------------------------

# Render সার্ভার সচল রাখার জন্য ডামি ওয়েব সার্ভার
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is Running Successfully!")

def run_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

# রিঅ্যাকশন কাউন্ট ট্র্যাক করার জন্য গ্লোবাল ডিকশনারি
reactions_data = {}

# --- নতুন মেম্বার জয়েন করলে ওয়েলকাম মেসেজ দেওয়ার ফাংশন ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
            
        user_mention = member.mention_html()
        
        welcome_text = (
            f"👋 <b>স্বাগতম {user_mention}, আমাদের গ্রুপে আপনাকে স্বাগতম!</b>\n\n"
            f"🎮 আমাদের অফিশিয়াল গেম লিংকে জয়েন করতে নিচের লিংকে ক্লিক করুন:\n"
            f"🔗 <a href='{ADMIN_LINK}'>এখানে ক্লিক করে জয়েন করুন</a>\n\n"
            f"✨ আশা করি গ্রুপের সকল নিয়ম মেনে আমাদের সাথেই থাকবেন। ধন্যবাদ!"
        )
        
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            print(f"Error sending welcome message: {e}")

# --- রিঅ্যাকশন এবং লাল বোনাস বাটন তৈরি করার ফাংশন ---
def get_combined_markup(msg_id):
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
    
    data = reactions_data[msg_id]
    
    love_text = f"❤️ {data['love']}" if data['love'] > 0 else "❤️"
    fire_text = f"🔥 {data['fire']}" if data['fire'] > 0 else "🔥"
    like_text = f"👍 {data['like']}" if data['like'] > 0 else "👍"
    dislike_text = f"👎 {data['dislike']}" if data['dislike'] > 0 else "👎"
    
    keyboard = [
        # প্রথম লাইনে থাকবে লাল রঙের হাইলাইট করা ২০০ টাকা বোনাসের বাটনটি
        [InlineKeyboardButton("🔴 রেজিস্ট্রেশন করে ২০০ টাকা বোনাস পান 🔴", url=ADMIN_LINK)],
        # দ্বিতীয় লাইনে থাকবে আপনার ৪টি রিঅ্যাকশন বাটন
        [
            InlineKeyboardButton(love_text, callback_data=f"react_{msg_id}_love"),
            InlineKeyboardButton(fire_text, callback_data=f"react_{msg_id}_fire"),
            InlineKeyboardButton(like_text, callback_data=f"react_{msg_id}_like"),
            InlineKeyboardButton(dislike_text, callback_data=f"react_{msg_id}_dislike")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- বাটনে ক্লিক করলে রিঅ্যাকশন কাউন্ট করার ফাংশন ---
async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    parts = query.data.split("_")
    if len(parts) != 3:
        await query.answer()
        return
        
    _, msg_id, reaction_type = parts
    
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
        
    data = reactions_data[msg_id]
    user_clicks = data["users"]
    
    if str(user_id) in user_clicks:
        previous_reaction = user_clicks[str(user_id)]
        if previous_reaction == reaction_type:
            data[reaction_type] -= 1
            del user_clicks[str(user_id)]
            await query.answer("রিঅ্যাকশন তুলে নেওয়া হয়েছে!")
        else:
            data[previous_reaction] -= 1
            data[reaction_type] += 1
            user_clicks[str(user_id)] = reaction_type
            await query.answer("আপনার রিঅ্যাকশন পরিবর্তন করা হয়েছে!")
    else:
        data[reaction_type] += 1
        user_clicks[str(user_id)] = reaction_type
        await query.answer("আপনি রিঅ্যাকশন দিয়েছেন!")
        
    try:
        await query.edit_message_reply_markup(reply_markup=get_combined_markup(msg_id))
    except Exception as e:
        print(f"Error updating reaction markup: {e}")

# --- শুধুমাত্র এডমিনের পোস্টে অফার ফুটার ও বাটন যুক্ত করার ফাংশন ---
async def process_admin_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message: 
        return
    
    if message.from_user and message.from_user.is_bot: 
        return
    
    is_admin = False
    try:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        if any(admin.user.id == message.from_user.id for admin in chat_admins):
            is_admin = True
    except Exception as e:
        print(f"Admin check error: {e}")
        return

    if not is_admin:
        return

    text_to_check = message.text_html if message.text_html else message.caption_html
    
    if text_to_check:
        # নিচে শুধুমাত্র গ্রাহক সেবা ও লগইন এর টেক্সট লিংক থাকবে (বোনাস লিংকটি বাটনে চলে গেছে)
        custom_footer = (
            f"\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f" <b>গ্রাহক সেবা</b> - <a href='https://t.me'>t.me/f999com</a>\n"
            f" <b>লগ ইন</b> - <a href='{ADMIN_LINK}'>{ADMIN_LINK}</a>"
        )
        
        final_message = text_to_check + custom_footer
        
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
            
            preview_disabled = LinkPreviewOptions(is_disabled=True)
            unique_msg_id = f"{update.effective_chat.id}{message.message_id}"
            reply_markup = get_combined_markup(unique_msg_id)
            
            if message.photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=message.photo[-1].file_id,
                    caption=final_message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=final_message,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_disabled,
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"Error handling admin message: {e}")

def main():
    threading.Thread(target=run_server, daemon=True).start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CallbackQueryHandler(handle_reaction, pattern=r"^react_"))
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, process_admin_posts))
    
    print("Your Bot is updated and running with bonus button and reactions...")
    application.run_polling()

if __name__ == "__main__":
    main()
