# -*- coding: utf-8 -*-
"""
KINO BOT (Telegram) - Pydroid 3 uchun
O'rnatish: Pydroid 3 -> Pip -> "pyTelegramBotAPI" ni o'rnating.

Imkoniyatlar:
- 2 til (O'zbek / Rus)
- Majburiy kanallarga obuna
- Kino kodi bo'yicha olish, nom bo'yicha qidiruv, Top kinolar
- Referal tizimi (taklif uchun bonus kunlar)
- 7 kunlik bepul sinov, keyin pullik obuna (chek yuborish -> admin tasdiqlaydi)
- Super admin panel: statistika, kino/kanal qo'shish-o'chirish,
  xabar tarqatish, obuna berish
- Obuna tugashidan 1 kun oldin eslatma
"""
import html
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types

# ===================== SOZLAMALAR =====================
# Render'da bular Environment Variables orqali beriladi.
# Pydroid'da esa "..." o'rniga to'g'ridan-to'g'ri yozing.
TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN_SHU_YERGA")           # @BotFather bergan token
ADMINS = [int(x) for x in os.getenv("ADMINS", "123456789").replace(" ", "").split(",") if x]
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))                  # Bepul sinov kunlari
REF_BONUS_DAYS = int(os.getenv("REF_BONUS_DAYS", "3"))          # Taklif uchun bonus kun
CARD = os.getenv("CARD", "8600 0000 0000 0000")                 # To'lov kartasi
CARD_OWNER = os.getenv("CARD_OWNER", "Ism Familiya")
PLANS = {                                                       # kun: narx (so'm)
    30: 15000,
    90: 40000,
    365: 140000,
}
PROTECT_CONTENT = False                # True bo'lsa kinoni yuborish/saqlash taqiqlanadi
DB_FILE = os.getenv("DB_PATH", "kino.db")
# ======================================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
lock = threading.Lock()
state = {}  # foydalanuvchi holatlari (admin qadamlari, qidiruv, chek)


# ---------------------- MATNLAR ----------------------
T = {
    "uz": {
        "choose_lang": "🌐 Tilni tanlang / Выберите язык",
        "welcome": "🎬 Xush kelibsiz, {name}!\n\nKino kodini yuboring - kinoni darhol olasiz.\n\n{status}",
        "menu_search": "🔍 Qidirish",
        "menu_top": "🔥 Top kinolar",
        "menu_profile": "👤 Profil",
        "menu_buy": "💳 Obuna",
        "menu_lang": "🌐 Til",
        "st_on": "✅ Obuna faol: {d} kun qoldi",
        "st_off": "❌ Obuna tugagan",
        "sub_required": "❗️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng «✅ Tekshirish» tugmasini bosing:",
        "check_btn": "✅ Tekshirish",
        "still_not": "❌ Hali hammasiga obuna bo'lmadingiz.",
        "notfound": "😕 Bunday kodli kino topilmadi.",
        "noaccess": "⛔️ Obunangiz tugagan. Davom etish uchun obuna oling yoki do'stlaringizni taklif qiling 👇",
        "buy_btn": "💳 Obuna olish",
        "profile": "👤 <b>Profil</b>\n\n🆔 ID: <code>{id}</code>\n📅 {status}\n👥 Takliflar: {refs}\n🎁 Har bir taklif uchun +{bonus} kun\n\n🔗 Sizning havolangiz:\n{link}",
        "buy_choose": "💳 Obuna muddatini tanlang:",
        "plan_btn": "{days} kun - {price} so'm",
        "pay_info": "💳 To'lov: <b>{price}</b> so'm ({days} kun)\n\nKarta: <code>{card}</code>\n{owner}\n\nTo'lovdan so'ng <b>chek rasmini</b> shu yerga yuboring.\nBekor qilish: /cancel",
        "need_receipt": "📸 Iltimos, chek rasmini yuboring (yoki /cancel).",
        "receipt_sent": "✅ Chek adminga yuborildi. Tasdiqlangach xabar beramiz.",
        "pay_ok": "✅ To'lov tasdiqlandi! Obuna +{days} kun uzaytirildi.",
        "pay_no": "❌ To'lov rad etildi. Savol bo'lsa admin bilan bog'laning.",
        "ref_bonus": "🎉 Do'stingiz qo'shildi! Sizga +{days} kun berildi.",
        "remind": "⏰ Obunangiz 1 kundan kam vaqtda tugaydi. «💳 Obuna» orqali uzaytiring.",
        "search_prompt": "🔍 Kino nomini yozing:",
        "search_none": "😕 Hech narsa topilmadi.",
        "search_res": "🔍 Topilgan kinolar:",
        "top_title": "🔥 Eng ko'p ko'rilgan kinolar:",
        "top_empty": "Hozircha kinolar yo'q.",
        "cancelled": "Bekor qilindi.",
        "movie_cap": "🎬 <b>{title}</b>\n🔑 Kod: <code>{code}</code>\n👁 Ko'rishlar: {views}",
    },
    "ru": {
        "choose_lang": "🌐 Tilni tanlang / Выберите язык",
        "welcome": "🎬 Добро пожаловать, {name}!\n\nОтправьте код фильма - и получите его сразу.\n\n{status}",
        "menu_search": "🔍 Поиск",
        "menu_top": "🔥 Топ фильмов",
        "menu_profile": "👤 Профиль",
        "menu_buy": "💳 Подписка",
        "menu_lang": "🌐 Язык",
        "st_on": "✅ Подписка активна: осталось {d} дн.",
        "st_off": "❌ Подписка закончилась",
        "sub_required": "❗️ Чтобы пользоваться ботом, подпишитесь на каналы ниже и нажмите «✅ Проверить»:",
        "check_btn": "✅ Проверить",
        "still_not": "❌ Вы подписались не на все каналы.",
        "notfound": "😕 Фильм с таким кодом не найден.",
        "noaccess": "⛔️ Подписка закончилась. Оформите подписку или пригласите друзей 👇",
        "buy_btn": "💳 Оформить подписку",
        "profile": "👤 <b>Профиль</b>\n\n🆔 ID: <code>{id}</code>\n📅 {status}\n👥 Приглашено: {refs}\n🎁 За каждого друга +{bonus} дн.\n\n🔗 Ваша ссылка:\n{link}",
        "buy_choose": "💳 Выберите срок подписки:",
        "plan_btn": "{days} дн. - {price} сум",
        "pay_info": "💳 Оплата: <b>{price}</b> сум ({days} дн.)\n\nКарта: <code>{card}</code>\n{owner}\n\nПосле оплаты отправьте сюда <b>фото чека</b>.\nОтмена: /cancel",
        "need_receipt": "📸 Пожалуйста, отправьте фото чека (или /cancel).",
        "receipt_sent": "✅ Чек отправлен админу. Сообщим после подтверждения.",
        "pay_ok": "✅ Оплата подтверждена! Подписка продлена на {days} дн.",
        "pay_no": "❌ Оплата отклонена. Если есть вопросы - свяжитесь с админом.",
        "ref_bonus": "🎉 Ваш друг присоединился! Вам начислено +{days} дн.",
        "remind": "⏰ Подписка закончится меньше чем через сутки. Продлите через «💳 Подписка».",
        "search_prompt": "🔍 Напишите название фильма:",
        "search_none": "😕 Ничего не найдено.",
        "search_res": "🔍 Найденные фильмы:",
        "top_title": "🔥 Самые просматриваемые фильмы:",
        "top_empty": "Пока фильмов нет.",
        "cancelled": "Отменено.",
        "movie_cap": "🎬 <b>{title}</b>\n🔑 Код: <code>{code}</code>\n👁 Просмотров: {views}",
    },
}

LABELS = {}
for _lg in T:
    for _k in ("menu_search", "menu_top", "menu_profile", "menu_buy", "menu_lang"):
        LABELS[T[_lg][_k]] = _k


# ---------------------- BAZA ----------------------
def run(q, args=()):
    with lock:
        con = sqlite3.connect(DB_FILE)
        cur = con.execute(q, args)
        con.commit()
        last = cur.lastrowid
        con.close()
        return last


def get(q, args=()):
    with lock:
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
        rows = con.execute(q, args).fetchall()
        con.close()
        return rows


def one(q, args=()):
    rows = get(q, args)
    return rows[0] if rows else None


def init_db():
    run("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, name TEXT, lang TEXT DEFAULT '',
        joined INTEGER, sub_until INTEGER, referrer INTEGER,
        ref_count INTEGER DEFAULT 0, reminded INTEGER DEFAULT 0)""")
    run("""CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY, title TEXT, file_id TEXT, ftype TEXT,
        views INTEGER DEFAULT 0, added INTEGER)""")
    run("""CREATE TABLE IF NOT EXISTS channels(
        chat_id INTEGER PRIMARY KEY, title TEXT, link TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, days INTEGER,
        amount INTEGER, status TEXT DEFAULT 'pending', created INTEGER)""")


# ---------------------- YORDAMCHI ----------------------
def now():
    return int(time.time())


def esc(s):
    return html.escape(str(s))


def lang(uid):
    r = one("SELECT lang FROM users WHERE id=?", (uid,))
    return r["lang"] if r and r["lang"] else "uz"


def t(uid, key, **kw):
    return T[lang(uid)][key].format(**kw)


def money(n):
    return f"{n:,}".replace(",", " ")


def extend(uid, days):
    u = one("SELECT sub_until FROM users WHERE id=?", (uid,))
    base = max(u["sub_until"] or 0, now()) if u else now()
    run("UPDATE users SET sub_until=?, reminded=0 WHERE id=?",
        (base + days * 86400, uid))


def status_text(uid):
    u = one("SELECT sub_until FROM users WHERE id=?", (uid,))
    left = (u["sub_until"] or 0) - now()
    if left > 0:
        return t(uid, "st_on", d=left // 86400 + 1)
    return t(uid, "st_off")


def menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(t(uid, "menu_search"), t(uid, "menu_top"))
    kb.row(t(uid, "menu_profile"), t(uid, "menu_buy"))
    kb.row(t(uid, "menu_lang"))
    return kb


def lang_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
           types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    return kb


def send_main(uid, name):
    bot.send_message(uid, t(uid, "welcome", name=esc(name), status=status_text(uid)),
                     reply_markup=menu(uid))


def not_subscribed(uid):
    bad = []
    for ch in get("SELECT * FROM channels"):
        try:
            m = bot.get_chat_member(ch["chat_id"], uid)
            if m.status in ("left", "kicked"):
                bad.append(ch)
        except Exception:
            pass  # bot kanalda admin emas bo'lsa tekshirib bo'lmaydi
    return bad


def gate(uid):
    """Majburiy obunani tekshiradi. True = o'tdi."""
    if uid in ADMINS:
        return True
    bad = not_subscribed(uid)
    if not bad:
        return True
    kb = types.InlineKeyboardMarkup()
    for ch in bad:
        kb.add(types.InlineKeyboardButton(ch["title"], url=ch["link"]))
    kb.add(types.InlineKeyboardButton(t(uid, "check_btn"), callback_data="chk"))
    bot.send_message(uid, t(uid, "sub_required"), reply_markup=kb)
    return False


def access(uid):
    """Obuna/sinov faolligini tekshiradi. True = kirish mumkin."""
    if uid in ADMINS:
        return True
    u = one("SELECT sub_until FROM users WHERE id=?", (uid,))
    if u and (u["sub_until"] or 0) > now():
        return True
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(t(uid, "buy_btn"), callback_data="buymenu"))
    bot.send_message(uid, t(uid, "noaccess"), reply_markup=kb)
    return False


def send_movie(uid, mv):
    cap = t(uid, "movie_cap", title=esc(mv["title"]), code=esc(mv["code"]),
            views=mv["views"] + 1)
    try:
        if mv["ftype"] == "video":
            bot.send_video(uid, mv["file_id"], caption=cap, protect_content=PROTECT_CONTENT)
        else:
            bot.send_document(uid, mv["file_id"], caption=cap, protect_content=PROTECT_CONTENT)
        run("UPDATE movies SET views=views+1 WHERE code=?", (mv["code"],))
    except Exception as e:
        bot.send_message(uid, f"⚠️ {esc(e)}")


def show_plans(uid):
    kb = types.InlineKeyboardMarkup()
    for days, price in PLANS.items():
        label = t(uid, "plan_btn", days=days, price=money(price))
        kb.add(types.InlineKeyboardButton(label, callback_data=f"buy_{days}"))
    bot.send_message(uid, t(uid, "buy_choose"), reply_markup=kb)


# ---------------------- ADMIN PANEL ----------------------
def admin_panel(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Statistika", callback_data="adm_stats"),
        types.InlineKeyboardButton("📣 Xabar tarqatish", callback_data="adm_bc"),
        types.InlineKeyboardButton("➕ Kino qo'shish", callback_data="adm_addmovie"),
        types.InlineKeyboardButton("🗑 Kino o'chirish", callback_data="adm_delmovie"),
        types.InlineKeyboardButton("➕ Kanal qo'shish", callback_data="adm_addch"),
        types.InlineKeyboardButton("🗑 Kanal o'chirish", callback_data="adm_delch"),
        types.InlineKeyboardButton("🎁 Obuna berish", callback_data="adm_give"),
        types.InlineKeyboardButton("🎞 Kinolar ro'yxati", callback_data="adm_list"),
    )
    bot.send_message(uid, "🛠 <b>Admin panel</b>", reply_markup=kb)


def stats_text():
    n = now()
    total = one("SELECT COUNT(*) c FROM users")["c"]
    active = one("SELECT COUNT(*) c FROM users WHERE sub_until>?", (n,))["c"]
    new24 = one("SELECT COUNT(*) c FROM users WHERE joined>?", (n - 86400,))["c"]
    movies = one("SELECT COUNT(*) c FROM movies")["c"]
    chans = one("SELECT COUNT(*) c FROM channels")["c"]
    pend = one("SELECT COUNT(*) c FROM payments WHERE status='pending'")["c"]
    rev = one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE status='ok'")["s"]
    return (f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {total}\n"
            f"✅ Faol obuna/sinov: {active}\n🆕 24 soatda: {new24}\n"
            f"🎬 Kinolar: {movies}\n📢 Kanallar: {chans}\n"
            f"⏳ Kutilayotgan to'lovlar: {pend}\n💰 Tushum: {money(rev)} so'm")


def do_broadcast(admin_id, msg):
    ok = bad = 0
    for u in get("SELECT id FROM users"):
        try:
            bot.copy_message(u["id"], msg.chat.id, msg.message_id)
            ok += 1
        except Exception:
            bad += 1
        time.sleep(0.05)
    bot.send_message(admin_id, f"📣 Yuborildi: {ok}\n❌ Xato: {bad}")


def admin_step(m):
    """Admin ko'p qadamli amallari. True = xabar ishlandi."""
    uid = m.from_user.id
    s = state[uid]
    step = s["step"]
    txt = (m.text or "").strip()

    if step == "m_code":
        if not txt:
            return True
        code = txt.lower()
        if one("SELECT 1 FROM movies WHERE code=?", (code,)):
            bot.send_message(uid, "⚠️ Bu kod band. Boshqa kod yuboring (yoki /cancel):")
            return True
        s.update(step="m_title", code=code)
        bot.send_message(uid, "📝 Kino nomini yuboring:")
    elif step == "m_title":
        if not txt:
            return True
        s.update(step="m_file", title=txt)
        bot.send_message(uid, "🎞 Endi kinoni (video yoki fayl) yuboring:")
    elif step == "m_file":
        if m.content_type == "video":
            fid, ft = m.video.file_id, "video"
        elif m.content_type == "document":
            fid, ft = m.document.file_id, "document"
        else:
            bot.send_message(uid, "❗️ Video yoki fayl yuboring.")
            return True
        run("INSERT INTO movies(code,title,file_id,ftype,added) VALUES(?,?,?,?,?)",
            (s["code"], s["title"], fid, ft, now()))
        bot.send_message(uid, f"✅ Qo'shildi!\n🔑 Kod: <code>{esc(s['code'])}</code>\n🎬 {esc(s['title'])}")
        state.pop(uid, None)
    elif step == "d_code":
        run("DELETE FROM movies WHERE code=?", (txt.lower(),))
        bot.send_message(uid, "🗑 O'chirildi (agar mavjud bo'lsa).")
        state.pop(uid, None)
    elif step == "c_add":
        x = txt
        if x.lstrip("-").isdigit():
            x = int(x)
        try:
            chat = bot.get_chat(x)
            if chat.username:
                link = f"https://t.me/{chat.username}"
            else:
                link = chat.invite_link or bot.export_chat_invite_link(chat.id)
            run("INSERT OR REPLACE INTO channels(chat_id,title,link) VALUES(?,?,?)",
                (chat.id, chat.title, link))
            bot.send_message(uid, f"✅ Kanal qo'shildi: {esc(chat.title)}")
        except Exception as e:
            bot.send_message(uid, f"❌ Xato: {esc(e)}\nBot kanalda admin bo'lishi shart.")
        state.pop(uid, None)
    elif step == "bc":
        state.pop(uid, None)
        bot.send_message(uid, "📣 Tarqatish boshlandi...")
        threading.Thread(target=do_broadcast, args=(uid, m), daemon=True).start()
    elif step == "give":
        try:
            target, days = txt.split()
            target, days = int(target), int(days)
            if not one("SELECT 1 FROM users WHERE id=?", (target,)):
                bot.send_message(uid, "❌ Foydalanuvchi topilmadi.")
            else:
                extend(target, days)
                bot.send_message(uid, f"✅ {target} ga +{days} kun berildi.")
                try:
                    bot.send_message(target, t(target, "pay_ok", days=days))
                except Exception:
                    pass
        except ValueError:
            bot.send_message(uid, "❗️ Format: <code>ID KUN</code>  (masalan: 123456 30)")
            return True
        state.pop(uid, None)
    else:
        return False
    return True


# ---------------------- BUYRUQLAR ----------------------
@bot.message_handler(commands=["start"])
def cmd_start(m):
    uid = m.from_user.id
    state.pop(uid, None)
    args = (m.text or "").split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    u = one("SELECT * FROM users WHERE id=?", (uid,))
    if not u:
        if ref == uid or ref is None or not one("SELECT 1 FROM users WHERE id=?", (ref,)):
            ref = None
        run("INSERT INTO users(id,name,joined,sub_until,referrer) VALUES(?,?,?,?,?)",
            (uid, m.from_user.first_name, now(), now() + TRIAL_DAYS * 86400, ref))
        if ref:
            extend(ref, REF_BONUS_DAYS)
            run("UPDATE users SET ref_count=ref_count+1 WHERE id=?", (ref,))
            try:
                bot.send_message(ref, t(ref, "ref_bonus", days=REF_BONUS_DAYS))
            except Exception:
                pass
        bot.send_message(uid, T["uz"]["choose_lang"], reply_markup=lang_kb())
    elif not u["lang"]:
        bot.send_message(uid, T["uz"]["choose_lang"], reply_markup=lang_kb())
    else:
        send_main(uid, m.from_user.first_name)
        gate(uid)


@bot.message_handler(commands=["admin"])
def cmd_admin(m):
    if m.from_user.id in ADMINS:
        state.pop(m.from_user.id, None)
        admin_panel(m.from_user.id)


@bot.message_handler(commands=["cancel"])
def cmd_cancel(m):
    state.pop(m.from_user.id, None)
    if one("SELECT 1 FROM users WHERE id=?", (m.from_user.id,)):
        bot.send_message(m.chat.id, t(m.from_user.id, "cancelled"))


# ---------------------- CALLBACKLAR ----------------------
@bot.callback_query_handler(func=lambda c: True)
def on_callback(c):
    uid = c.from_user.id
    d = c.data
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass

    # --- til ---
    if d.startswith("lang_"):
        if not one("SELECT 1 FROM users WHERE id=?", (uid,)):
            return
        run("UPDATE users SET lang=? WHERE id=?", (d[5:], uid))
        try:
            bot.delete_message(uid, c.message.message_id)
        except Exception:
            pass
        send_main(uid, c.from_user.first_name)
        gate(uid)
        return

    if not one("SELECT 1 FROM users WHERE id=?", (uid,)):
        return

    # --- obunani tekshirish ---
    if d == "chk":
        if not_subscribed(uid):
            bot.answer_callback_query(c.id, t(uid, "still_not"), show_alert=True)
        else:
            try:
                bot.delete_message(uid, c.message.message_id)
            except Exception:
                pass
            send_main(uid, c.from_user.first_name)
        return

    # --- kino tugmasi (qidiruv/top) ---
    if d.startswith("mv_"):
        if not gate(uid) or not access(uid):
            return
        mv = one("SELECT * FROM movies WHERE code=?", (d[3:],))
        if mv:
            send_movie(uid, mv)
        return

    # --- obuna sotib olish ---
    if d == "buymenu":
        show_plans(uid)
        return
    if d.startswith("buy_"):
        days = int(d[4:])
        if days not in PLANS:
            return
        price = PLANS[days]
        state[uid] = {"step": "receipt", "days": days, "price": price}
        bot.send_message(uid, t(uid, "pay_info", price=money(price), days=days,
                                card=CARD, owner=esc(CARD_OWNER)))
        return

    # --- to'lovni tasdiqlash/rad etish (admin) ---
    if d.startswith("pok_") or d.startswith("pno_"):
        if uid not in ADMINS:
            return
        pid = int(d[4:])
        p = one("SELECT * FROM payments WHERE id=?", (pid,))
        if not p or p["status"] != "pending":
            bot.answer_callback_query(c.id, "Allaqachon ko'rib chiqilgan.", show_alert=True)
            return
        if d.startswith("pok_"):
            run("UPDATE payments SET status='ok' WHERE id=?", (pid,))
            extend(p["user_id"], p["days"])
            note = f"✅ Tasdiqlandi (#{pid})"
            try:
                bot.send_message(p["user_id"], t(p["user_id"], "pay_ok", days=p["days"]))
            except Exception:
                pass
        else:
            run("UPDATE payments SET status='no' WHERE id=?", (pid,))
            note = f"❌ Rad etildi (#{pid})"
            try:
                bot.send_message(p["user_id"], t(p["user_id"], "pay_no"))
            except Exception:
                pass
        try:
            bot.edit_message_caption(note, c.message.chat.id, c.message.message_id)
        except Exception:
            pass
        return

    # --- admin tugmalari ---
    if d.startswith("adm_") or d.startswith("delch_"):
        if uid not in ADMINS:
            return
        if d == "adm_stats":
            bot.send_message(uid, stats_text())
        elif d == "adm_addmovie":
            state[uid] = {"step": "m_code"}
            bot.send_message(uid, "🔑 Kino kodini yuboring (masalan: 101). Bekor: /cancel")
        elif d == "adm_delmovie":
            state[uid] = {"step": "d_code"}
            bot.send_message(uid, "🗑 O'chiriladigan kino kodini yuboring:")
        elif d == "adm_addch":
            state[uid] = {"step": "c_add"}
            bot.send_message(uid, "📢 Kanal @username yoki ID sini yuboring.\n"
                                  "Avval botni o'sha kanalga ADMIN qiling!")
        elif d == "adm_delch":
            chans = get("SELECT * FROM channels")
            if not chans:
                bot.send_message(uid, "Kanallar yo'q.")
            else:
                kb = types.InlineKeyboardMarkup()
                for ch in chans:
                    kb.add(types.InlineKeyboardButton(f"🗑 {ch['title']}",
                                                      callback_data=f"delch_{ch['chat_id']}"))
                bot.send_message(uid, "Qaysi kanalni o'chirasiz?", reply_markup=kb)
        elif d.startswith("delch_"):
            run("DELETE FROM channels WHERE chat_id=?", (int(d[6:]),))
            bot.send_message(uid, "🗑 Kanal o'chirildi.")
        elif d == "adm_bc":
            state[uid] = {"step": "bc"}
            bot.send_message(uid, "📣 Tarqatiladigan xabarni yuboring (matn/rasm/video). Bekor: /cancel")
        elif d == "adm_give":
            state[uid] = {"step": "give"}
            bot.send_message(uid, "🎁 Format: <code>ID KUN</code>  (masalan: 123456 30)")
        elif d == "adm_list":
            rows = get("SELECT code,title,views FROM movies ORDER BY added DESC LIMIT 50")
            if not rows:
                bot.send_message(uid, "Kinolar yo'q.")
            else:
                txt = "\n".join(f"<code>{esc(r['code'])}</code> - {esc(r['title'])} ({r['views']})"
                                for r in rows)
                bot.send_message(uid, "🎞 <b>Kinolar (oxirgi 50):</b>\n\n" + txt)


# ---------------------- XABARLAR ----------------------
@bot.message_handler(content_types=["text", "photo", "video", "document"])
def on_message(m):
    uid = m.from_user.id
    if m.chat.type != "private":
        return
    if not one("SELECT 1 FROM users WHERE id=?", (uid,)):
        return cmd_start(m)

    txt = (m.text or "").strip()

    # menyu tugmalari
    if txt in LABELS:
        state.pop(uid, None)
        act = LABELS[txt]
        if act == "menu_lang":
            bot.send_message(uid, T["uz"]["choose_lang"], reply_markup=lang_kb())
            return
        if not gate(uid):
            return
        if act == "menu_search":
            state[uid] = {"step": "search"}
            bot.send_message(uid, t(uid, "search_prompt"))
        elif act == "menu_top":
            rows = get("SELECT code,title,views FROM movies ORDER BY views DESC LIMIT 10")
            if not rows:
                bot.send_message(uid, t(uid, "top_empty"))
            else:
                kb = types.InlineKeyboardMarkup()
                for r in rows:
                    kb.add(types.InlineKeyboardButton(f"{r['title']} ({r['views']}👁)",
                                                      callback_data=f"mv_{r['code']}"))
                bot.send_message(uid, t(uid, "top_title"), reply_markup=kb)
        elif act == "menu_profile":
            u = one("SELECT * FROM users WHERE id=?", (uid,))
            link = f"https://t.me/{BOT_USERNAME}?start={uid}"
            bot.send_message(uid, t(uid, "profile", id=uid, status=status_text(uid),
                                    refs=u["ref_count"], bonus=REF_BONUS_DAYS, link=link))
        elif act == "menu_buy":
            show_plans(uid)
        return

    # holatlar
    s = state.get(uid)
    if s:
        if uid in ADMINS and s["step"] not in ("search", "receipt"):
            if admin_step(m):
                return
        if s["step"] == "search":
            if not txt:
                return
            state.pop(uid, None)
            rows = get("SELECT code,title FROM movies WHERE title LIKE ? LIMIT 10",
                       (f"%{txt}%",))
            if not rows:
                bot.send_message(uid, t(uid, "search_none"))
            else:
                kb = types.InlineKeyboardMarkup()
                for r in rows:
                    kb.add(types.InlineKeyboardButton(r["title"], callback_data=f"mv_{r['code']}"))
                bot.send_message(uid, t(uid, "search_res"), reply_markup=kb)
            return
        if s["step"] == "receipt":
            if m.content_type not in ("photo", "document"):
                bot.send_message(uid, t(uid, "need_receipt"))
                return
            pid = run("INSERT INTO payments(user_id,days,amount,created) VALUES(?,?,?,?)",
                      (uid, s["days"], s["price"], now()))
            cap = (f"💳 To'lov #{pid}\n👤 <a href='tg://user?id={uid}'>{esc(m.from_user.first_name)}</a>"
                   f" (<code>{uid}</code>)\n📦 {s['days']} kun - {money(s['price'])} so'm")
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pok_{pid}"),
                   types.InlineKeyboardButton("❌ Rad etish", callback_data=f"pno_{pid}"))
            for a in ADMINS:
                try:
                    if m.content_type == "photo":
                        bot.send_photo(a, m.photo[-1].file_id, caption=cap, reply_markup=kb)
                    else:
                        bot.send_document(a, m.document.file_id, caption=cap, reply_markup=kb)
                except Exception:
                    pass
            state.pop(uid, None)
            bot.send_message(uid, t(uid, "receipt_sent"))
            return

    # kino kodi
    if txt:
        if not gate(uid) or not access(uid):
            return
        mv = one("SELECT * FROM movies WHERE code=?", (txt.lower(),))
        if mv:
            send_movie(uid, mv)
        else:
            bot.send_message(uid, t(uid, "notfound"))


# ---------------------- ESLATMA ----------------------
def reminder_loop():
    while True:
        try:
            n = now()
            rows = get("SELECT id FROM users WHERE reminded=0 AND sub_until>? AND sub_until<?",
                       (n, n + 86400))
            for u in rows:
                try:
                    bot.send_message(u["id"], t(u["id"], "remind"))
                except Exception:
                    pass
                run("UPDATE users SET reminded=1 WHERE id=?", (u["id"],))
        except Exception as e:
            print("reminder error:", e)
        time.sleep(1800)


# ---------------------- KEEP-ALIVE SERVER (Render uchun) ----------------------
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


def start_web():
    # Render PORT beradi (odatda 10000), bo'lmasa 1000-port ochiladi
    port = int(os.getenv("PORT", "1000"))
    try:
        srv = HTTPServer(("0.0.0.0", port), Ping)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"Web server ishga tushdi: port {port}")
    except OSError as e:
        print("Web server ochilmadi:", e)


# ---------------------- ISHGA TUSHIRISH ----------------------
if __name__ == "__main__":
    start_web()
    init_db()
    BOT_USERNAME = bot.get_me().username
    threading.Thread(target=reminder_loop, daemon=True).start()
    print(f"Bot ishga tushdi: @{BOT_USERNAME}")
    bot.infinity_polling(skip_pending=True, timeout=30)
