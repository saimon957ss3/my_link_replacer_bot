import os
import re
from telegram import Update, LinkPreviewOptions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- আপনার টোকেন এবং লিংক এখানে সেট করা হয়েছে ---
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

# --- শুধুমাত্র মেম্বারদের পোস্টের জন্য ৪টি রিঅ্যাকশন বাটন (অফার ছাড়া) ---
def get_member_markup(msg_id):
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
    
    data = reactions_data[msg_id]
    
    love_text = f"❤️ {data['love']}" if data['love'] > 0 else "❤️"
    fire_text = f"🔥 {data['fire']}" if data['fire'] > 0 else "🔥"
    like_text = f"👍 {data['like']}" if data['like'] > 0 else "👍"
    dislike_text = f"👎 {data['dislike']}" if data['dislike'] > 0 else "👎"
    
    keyboard = [[
        InlineKeyboardButton(love_text, callback_data=f"react_{msg_id}_love"),
        InlineKeyboardButton(fire_text, callback_data=f"react_{msg_id}_fire"),
        InlineKeyboardButton(like_text, callback_data=f"react_{msg_id}_like"),
        InlineKeyboardButton(dislike_text, callback_data=f"react_{msg_id}_dislike")
    ]]
    return InlineKeyboardMarkup(keyboard)

# --- অ্যাডমিন বা বটের নিজের পোস্টের জন্য সব বাটন একসাথে (ফুল অফারসহ) ---
def get_admin_combined_markup(msg_id):
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
    
    data = reactions_data[msg_id]
    
    love_text = f"❤️ {data['love']}" if data['love'] > 0 else "❤️"
    fire_text = f"🔥 {data['fire']}" if data['fire'] > 0 else "🔥"
    like_text = f"👍 {data['like']}" if data['like'] > 0 else "👍"
    dislike_text = f"👎 {data['dislike']}" if data['dislike'] > 0 else "👎"
    
    keyboard = [
        # ১. আকর্ষণীয় রেজিস্ট্রেশন বোনাস বাটন
        [InlineKeyboardButton("🔴 রেজিস্ট্রেশন করে ২০০ টাকা বোনাস পান 🔴", url=ADMIN_LINK)],
        # ২. গ্রাহক সেবা এবং লগ ইন বাটন (এক লাইনে পাশাপাশি)
        [
            InlineKeyboardButton("📞 গ্রাহক সেবা", url="https://t.me"),
            InlineKeyboardButton("🔐 লগ ইন", url=ADMIN_LINK)
        ],
        # ৩. ৪টি রিঅ্যাকশন বাটন
        [
            InlineKeyboardButton(love_text, callback_data=f"react_{msg_id}_love"),
            InlineKeyboardButton(fire_text, callback_data=f"react_{msg_id}_fire"),
            InlineKeyboardButton(like_text, callback_data=f"react_{msg_id}_like"),
            InlineKeyboardButton(dislike_text, callback_data=f"react_{msg_id}_dislike")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- নতুন মেম্বার জয়েন করলে বাটনসহ ওয়েলকাম মেসেজ দেওয়ার ফাংশন ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
            
        user_mention = member.mention_html()
        
        welcome_text = (
            f"👋 <b>স্বাগতম {user_mention}, আমাদের গ্রুপে আপনাকে স্বাগতম!</b>\n\n"
            f"🎮 গেম খেলতে এবং আমাদের অফিশিয়াল সার্ভিসে যুক্ত হতে নিচের বাটনগুলো ব্যবহার করুন:"
        )
        
        unique_welcome_id = f"welcome_{member.id}"
        reply_markup = get_admin_combined_markup(unique_welcome_id)
        
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            print(f"Error sending welcome message: {e}")

# --- বাটনে ক্লিক করলে রিঅ্যাকশন কাউন্ট করার ফাংশন (মেম্বার ও এডমিন উভয়ের জন্য ডাইনামিক) ---
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
        # ওয়েলকাম বা এডমিন মেসেজ হলে ফুল অফার বাটনসহ আপডেট হবে, মেম্বার হলে শুধু রিঅ্যাকশন বাটন আপডেট হবে
        if "welcome_" in msg_id or "admin_" in msg_id:
            await query.edit_message_reply_markup(reply_markup=get_admin_combined_markup(msg_id))
        else:
            await query.edit_message_reply_markup(reply_markup=get_member_markup(msg_id))
    except Exception as e:
        print(f"Error updating reaction markup: {e}")

# --- গ্রুপে আসা সমস্ত মেসেজ ফিল্টার ও প্রসেস করার মূল ফাংশন ---
async def process_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message: 
        return
    
    # বট নিজের পাঠানো মেসেজ হলে এড়িয়ে যাবে
    if message.from_user and message.from_user.is_bot: 
        return

    # পোস্টদাতা অ্যাডমিন কিনা তা চেক করা
    is_admin = False
    try:
        chat_admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        if any(admin.user.id == message.from_user.id for admin in chat_admins):
            is_admin = True
    except Exception as e:
        print(f"Admin check error: {e}")
        return

    # মেসেজের মূল টেক্সট ফরম্যাট নেওয়া
    final_message = message.text_html if message.text_html else message.caption_html
    if not final_message and message.text:
        final_message = message.text

    if final_message:
        try:
            # আসল পোস্টটি গ্রুপ থেকে ডিলিট করা
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
            
            preview_disabled = LinkPreviewOptions(is_disabled=True)
            
            # এডমিন এবং মেম্বারদের জন্য আলাদা বাটন সেট করা
            if is_admin:
                unique_msg_id = f"admin_{update.effective_chat.id}{message.message_id}"
                reply_markup = get_admin_combined_markup(unique_msg_id)
            else:
                unique_msg_id = f"member_{update.effective_chat.id}{message.message_id}"
                reply_markup = get_member_markup(unique_msg_id)
            
            # ছবিসহ পোস্ট হলে
            if message.photo:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=message.photo[-1].file_id,
                    caption=final_message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            else: # সাধারণ টেক্সট বা কোড হলে
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=final_message,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=preview_disabled,
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"Error handling group message: {e}")

def main():
    threading.Thread(target=run_server, daemon=True).start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # হ্যান্ডলারসমূহ সেটআপ করা
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CallbackQueryHandler(handle_reaction, pattern=r"^react_"))
    application.add_handler(MessageHandler(filters.ALL, process_group_messages))
    
    print("আপনার নিখুঁত কাস্টমাইজড টেলিগ্রাম বট সফলভাবে সচল হয়েছে...")
    application.run_polling()

if __name__ == "__main__":
    main()
