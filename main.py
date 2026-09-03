import os
import re
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- আপনার দেওয়া টোকেন এবং লিংক এখানে সরাসরি বসানো হয়েছে ---
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

async def cloak_links_and_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message: 
        return
    
    # বট নিজের মেসেজ বা অন্য কোনো বটের মেসেজ হলে এড়িয়ে যাবে
    if message.from_user and message.from_user.is_bot: 
        return
    
    # গ্রুপের অ্যাডমিনরা পোস্ট করলে লিংক পরিবর্তন হবে না
    try:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        if any(admin.user.id == message.from_user.id for admin in chat_admins): 
            return
    except:
        pass

    # মেম্বারের দেওয়া আসল টেক্সট বা ক্যাপশন নেওয়া (HTML ফরম্যাটে)
    text_to_check = message.text_html if message.text_html else message.caption_html
    
    if text_to_check:
        # লিংক খুঁজে বের করার জন্য রেগুলার এক্সপ্রেশন
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        
        # যদি মেসেজে কোনো লিংক থাকে
        if re.search(url_pattern, text_to_check):
            
            # মেম্বারের লিংকের ওপরে আপনার লিংক ক্লোকিং করার ফাংশন
            def replace_with_cloak(match):
                member_link = match.group(0)
                # মেম্বারের টেক্সট লিংকটি দেখাবে, কিন্তু ব্যাকগ্রাউন্ডে আপনার অ্যাডমিন লিংক থাকবে
                return f'<a href="{ADMIN_LINK}">{member_link}</a>'
            
            # লিংক ক্লোকিং ফর্মুলা রান করা
            new_text = re.sub(url_pattern, replace_with_cloak, text_to_check)
            
            # কে পোস্ট করেছে তার নাম যুক্ত করা
            user_mention = f"<b>পোস্ট করেছেন:</b> {message.from_user.mention_html()}\n\n" if message.from_user else ""
            final_message = user_mention + new_text
            
            try:
                # মেম্বারের আসল পোস্ট গ্রুপ থেকে ডিলিট করা
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
                
                # যদি পোস্টে কোনো ছবি বা মিডিয়া থাকে
                if message.photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=message.photo[-1].file_id,
                        caption=final_message,
                        parse_mode=ParseMode.HTML
                    )
                else: # সাধারণ শুধু টেক্সট মেসেজ হলে
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=final_message,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                print(f"Error handling message: {e}")

def main():
    # ব্যাকগ্রাউন্ডে সার্ভার সচল রাখার থ্রেড চালু করা
    threading.Thread(target=run_server, daemon=True).start()
    
    # বট অ্যাপ্লিকেশন চালু করা
    application = Application.builder().token(BOT_TOKEN).build()
    
    # টেক্সট এবং ক্যাপশন ফিল্টার সচল রাখা
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, cloak_links_and_repost))
    
    print("আপনার কাস্টম লিংক ক্লোকিং বট সফলভাবে সচল হয়েছে...")
    application.run_polling()

if __name__ == "__main__":
    main()
