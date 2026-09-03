import os
import re
from telegram import Update, LinkPreviewOptions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- আপনার নতুন লিংক এবং টোকেন এখানে সেট করা হয়েছে ---
BOT_TOKEN = "8857827625:AAH5atf8X3rktmiCKimGA4JgtFnMNNYG984"
ADMIN_LINK = "https://www.f999game.com/?dl=2mlug1"
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

# --- নতুন মেম্বার জয়েন করলে ওয়েলকাম মেসেজ দেওয়ার ফাংশন ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
            
        user_mention = member.mention_html()
        
        welcome_text = (
            f"👋 <b>স্বাগতম {user_mention}, আমাদের গ্রুপে আপনাকে স্বাগতম!</b>\n\n"
            f"🎮 আমাদের অফিশিয়াল গেম লিংকে জয়েন করতে নিচের বাটনে ক্লিক করুন:\n"
        )
        
        # ওয়েলকাম মেসেজেও ডাইরেক্ট বাটন যুক্ত করা হলো
        keyboard = [[InlineKeyboardButton("🎮 এখানে ক্লিক করে জয়েন করুন 🎮", url=ADMIN_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Error sending welcome message: {e}")

# --- পোস্টের লিংক পরিবর্তন এবং ইনলাইন বাটন যুক্ত করার ফাংশন ---
async def cloak_links_and_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message: 
        return
    
    if message.from_user and message.from_user.is_bot: 
        return
    
    try:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        if any(admin.user.id == message.from_user.id for admin in chat_admins): 
            return
    except:
        pass

    # মেম্বারের টেক্সট বা ক্যাপশন নেওয়া (সাধারণ টেক্সট হিসেবে, যাতে ভেতরের আসল লিংক পপ-আপ না করে)
    text_to_check = message.text if message.text else message.caption
    
    if text_to_check:
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        
        if re.search(url_pattern, text_to_check):
            # মেম্বারের মেসেজ থেকে সরাসরি লিংকটি টেক্সট আকারে রেখে দেওয়া হবে (মাস্কিং ছাড়া)
            final_text = text_to_check
            
            # কে পোস্ট করেছে তার নাম যুক্ত করা
            user_mention = f"<b>পোস্ট করেছেন:</b> {message.from_user.mention_html()}\n\n" if message.from_user else ""
            final_message = user_mention + final_text
            
            # নিচের সুন্দর ইনলাইন বাটন তৈরি (যাতে ক্লিক করলে ডাইরেক্ট ব্রাউজারে আপনার লিংকে নিয়ে যায়)
            keyboard = [[InlineKeyboardButton("🔗 মূল লিংকে প্রবেশ করুন (Click Here) 🔗", url=ADMIN_LINK)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                # মেম্বারের আসল পোস্ট ডিলিট করা
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
                
                # যদি পোস্টে ছবি থাকে
                if message.photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=message.photo[-1].file_id,
                        caption=final_message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else: # শুধু টেক্সট হলে
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=final_message,
                        parse_mode=ParseMode.HTML,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Error handling message: {e}")

def main():
    threading.Thread(target=run_server, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, cloak_links_and_repost))
    
    print("আপনার কাস্টম বাটন ও লিংক রিপ্লেসার বট সফলভাবে সচল হয়েছে...")
    application.run_polling()

if __name__ == "__main__":
    main()
                             
