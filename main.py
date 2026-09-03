import os
import re
from telegram import Update, LinkPreviewOptions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- আপনার নতুন লিংক এবং টোকেন এখানে সরাসরি বসানো হয়েছে ---
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

# --- রিঅ্যাকশন বাটন তৈরি করার ফাংশন ---
def get_reaction_markup(msg_id):
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
    
    data = reactions_data[msg_id]
    
    # বাটনগুলোর টেক্সট এবং কাউন্ট সেট করা
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

# --- বাটনে ক্লিক করলে রিঅ্যাকশন কাউন্ট করার ফাংশন ---
async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # callback_data পার্স করা (ফরম্যাট: react_msgid_type)
    parts = query.data.split("_")
    if len(parts) != 3:
        await query.answer()
        return
        
    msg_id, reaction_type = parts[1], parts[2]
    
    if msg_id not in reactions_data:
        reactions_data[msg_id] = {"love": 0, "fire": 0, "like": 0, "dislike": 0, "users": {}}
        
    data = reactions_data[msg_id]
    user_clicks = data["users"]
    
    # এক ইউজার যাতে একই বাটনে বারবার ক্লিক করতে না পারে (টগল সিস্টেম)
    if str(user_id) in user_clicks:
        previous_reaction = user_clicks[str(user_id)]
        if previous_reaction == reaction_type:
            # একই রিঅ্যাকশনে আবার ক্লিক করলে মাইনাস হবে (রিমুভ হবে)
            data[reaction_type] -= 1
            del user_clicks[str(user_id)]
            await query.answer("রিঅ্যাকশন তুলে নেওয়া হয়েছে!")
        else:
            # অন্য রিঅ্যাকশনে ক্লিক করলে আগেরটা মাইনাস হয়ে নতুনটা প্লাস হবে
            data[previous_reaction] -= 1
            data[reaction_type] += 1
            user_clicks[str(user_id)] = reaction_type
            await query.answer("আপনার রিঅ্যাকশন পরিবর্তন করা হয়েছে!")
    else:
        # নতুন ক্লিক হলে প্লাস হবে
        data[reaction_type] += 1
        user_clicks[str(user_id)] = reaction_type
        await query.answer("আপনি রিঅ্যাকশন দিয়েছেন!")
        
    # পোস্টের বাটন আপডেট করা
    try:
        await query.edit_message_reply_markup(reply_markup=get_reaction_markup(msg_id))
    except Exception as e:
        print(f"Error updating reaction markup: {e}")

# --- লিংক ক্লোকিং এবং রিপোস্ট করার ফাংশন ---
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

    text_to_check = message.text_html if message.text_html else message.caption_html
    
    if text_to_check:
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        
        if re.search(url_pattern, text_to_check):
            
            def replace_with_cloak(match):
                member_link = match.group(0)
                return f'<a href="{ADMIN_LINK}">{member_link}</a>'
            
            new_text = re.sub(url_pattern, replace_with_cloak, text_to_check)
            
            user_mention = f"<b>পোস্ট করেছেন:</b> {message.from_user.mention_html()}\n\n" if message.from_user else ""
            final_message = user_mention + new_text
            
            try:
                # মেম্বারের আসল পোস্ট গ্রুপ থেকে ডিলিট করা
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
                
                preview_disabled = LinkPreviewOptions(is_disabled=True)
                
                # একটি ইউনিক মেসেজ আইডি জেনারেট করা ট্র্যাকিং এর জন্য
                unique_msg_id = f"{update.effective_chat.id}{message.message_id}"
                reply_markup = get_reaction_markup(unique_msg_id)
                
                # যদি পোস্টে কোনো ছবি থাকে
                if message.photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=message.photo[-1].file_id,
                        caption=final_message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else: # সাধারণ শুধু টেক্সট মেসেজ হলে
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=final_message,
                        parse_mode=ParseMode.HTML,
                        link_preview_options=preview_disabled,
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print(f"Error handling message: {e}")

def main():
    threading.Thread(target=run_server, daemon=True).start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # নতুন মেম্বার জয়েন করার হ্যান্ডলার
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # রিঅ্যাকশন বাটন ক্লিকের হ্যান্ডলার (নতুন যুক্ত করা হয়েছে)
    application.add_handler(CallbackQueryHandler(handle_reaction, pattern=r"^react_"))
    
    # লিংক রিপ্লেসের হ্যান্ডলার
    application.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, cloak_links_and_repost))
    
    print("আপনার কাস্টম লিংক ক্লোকিং, ওয়েলকাম ও রিঅ্যাকশন বট সফলভাবে সচল হয়েছে...")
    application.run_polling()

if __name__ == "__main__":
    main()
