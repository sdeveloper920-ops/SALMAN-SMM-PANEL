import os, json, logging, uuid
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("salman-smm")

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
CURRENCY = os.getenv("CURRENCY", "৳")
PAYMENT_INSTRUCTIONS = os.getenv("PAYMENT_INSTRUCTIONS", "পেমেন্টের জন্য অ্যাডমিনের সাথে যোগাযোগ করুন।")
PAYMENT_METHODS = ["বিকাশ", "নগদ", "রকেট", "উপায়"]

def payment_text():
    lines=["💳 **পেমেন্ট মাধ্যম**"]
    for method in PAYMENT_METHODS:
        snap=db.collection("settings").document("payments").get()
        cfg=(snap.to_dict() or {}).get(method,{}) if snap.exists else {}
        if cfg.get("active", True):
            lines.append(f"• {method}: {cfg.get('number','নম্বর সেট করা হয়নি')}\\n  {cfg.get('instruction','')}")
    return "\\n".join(lines)

if not firebase_admin._apps:
    raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    if raw:
        cred = credentials.Certificate(json.loads(raw))
    else:
        path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
        cred = credentials.Certificate(path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

HOME = ReplyKeyboardMarkup(
    [["🛍 Services", "👤 My Account"], ["➕ Add Funds", "📦 My Orders"], ["📞 Support", "ℹ️ Help"]],
    resize_keyboard=True
)

def is_admin(uid): return uid in ADMIN_IDS
def now(): return datetime.now(timezone.utc).isoformat()
def money(v): return f"{float(v):,.2f}{CURRENCY}"
def user_ref(uid): return db.collection("users").document(str(uid))
def get_user(uid):
    ref=user_ref(uid); snap=ref.get()
    if not snap.exists:
        data={"user_id":uid,"balance":0.0,"created_at":now(),"username":None}
        ref.set(data); return data
    return snap.to_dict()
def services():
    return [(d.id,d.to_dict()) for d in db.collection("services").where("active","==",True).stream()]
def main_menu_text():
    return "স্বাগতম SALMAN SMM PANEL-এ! 👋\nনিচের মেনু থেকে একটি অপশন বেছে নিন।"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    data=get_user(u.id); data["username"]=u.username or ""; data["first_name"]=u.first_name or ""
    user_ref(u.id).set(data, merge=True)
    await update.message.reply_text(main_menu_text(), reply_markup=HOME)

async def help_cmd(update, context):
    await update.message.reply_text("ব্যবহার:\n🛍 Services — সার্ভিস ও অর্ডার\n➕ Add Funds — ব্যালেন্স রিচার্জ রিকোয়েস্ট\n📦 My Orders — অর্ডার ইতিহাস\n📞 Support — অ্যাডমিনের সাথে যোগাযোগ\n\nঅর্ডার ম্যানুয়ালি অ্যাডমিন প্রসেস করবেন।", reply_markup=HOME)

async def account(update, context):
    u=update.effective_user; d=get_user(u.id)
    await update.message.reply_text(f"👤 Account\nID: `{u.id}`\nName: {u.first_name}\nBalance: {money(d.get('balance',0))}", parse_mode="Markdown", reply_markup=HOME)

async def show_services(update, context):
    items=services()
    if not items:
        await update.message.reply_text("এখনো কোনো সার্ভিস যোগ করা হয়নি। পরে আবার চেষ্টা করুন।", reply_markup=HOME); return
    rows=[]
    for sid,s in items:
        rows.append([InlineKeyboardButton(f"{s.get('name','Service')} · {money(s.get('price_per_1000',0))}/1K", callback_data=f"svc:{sid}")])
    await update.message.reply_text("একটি সার্ভিস বেছে নিন:", reply_markup=InlineKeyboardMarkup(rows))

async def show_orders(update, context):
    docs=db.collection("orders").where("user_id","==",update.effective_user.id).stream()
    arr=sorted([d.to_dict() for d in docs], key=lambda x:x.get("created_at",""), reverse=True)[:10]
    if not arr: await update.message.reply_text("আপনার কোনো অর্ডার নেই।", reply_markup=HOME); return
    lines=["📦 আপনার সাম্প্রতিক অর্ডার:"]
    for o in arr:
        lines.append(f"#{o['order_id']} | {o.get('service_name')} | {o.get('quantity')} | {o.get('status')} | {money(o.get('total',0))}")
    await update.message.reply_text("\n".join(lines), reply_markup=HOME)

async def add_funds(update, context):
    context.user_data["state"]="deposit_amount"
    await update.message.reply_text("কত টাকা Add Funds করতে চান? শুধু সংখ্যা লিখুন।\\n\\n"+payment_text(),parse_mode="Markdown")

async def support(update, context):
    await update.message.reply_text("সাপোর্টের জন্য আপনার Telegram ID অ্যাডমিনকে পাঠান:\n"+", ".join(map(str,ADMIN_IDS or ["Admin not configured"])), reply_markup=HOME)

async def admin_panel(update, context):
    if not is_admin(update.effective_user.id): return await update.message.reply_text("⛔ Access denied.")
    kb=[[InlineKeyboardButton("🆕 Pending Orders",callback_data="admin:orders"),
         InlineKeyboardButton("💳 Deposit Requests",callback_data="admin:deposits")],
        [InlineKeyboardButton("📊 Statistics",callback_data="admin:stats")]]
    await update.message.reply_text("🛠 SALMAN SMM PANEL — Admin",reply_markup=InlineKeyboardMarkup(kb))

async def addservice(update, context):
    if not is_admin(update.effective_user.id): return
    raw=" ".join(context.args)
    # Format: category | name | price_per_1000 | min | max
    p=[x.strip() for x in raw.split("|")]
    if len(p)!=5:
        return await update.message.reply_text("ফরম্যাট:\n/addservice Category | Service name | Price per 1000 | Min | Max\nউদাহরণ:\n/addservice Instagram | Followers | 120 | 100 | 10000")
    try:
        cat,name,price,mn,mx=p; price=float(price); mn=int(mn); mx=int(mx)
        if price<=0 or mn<1 or mx<mn: raise ValueError()
        ref=db.collection("services").document()
        ref.set({"category":cat,"name":name,"price_per_1000":price,"min":mn,"max":mx,"active":True,"created_at":now()})
        await update.message.reply_text(f"✅ সার্ভিস যোগ হয়েছে। ID: {ref.id}")
    except Exception:
        await update.message.reply_text("তথ্য সঠিক নয়। আবার চেষ্টা করুন।")

async def setpayment(update, context):
    if not is_admin(update.effective_user.id): return
    raw=" ".join(context.args)
    # Format: /setpayment Method | Number | Instructions
    p=[x.strip() for x in raw.split("|")]
    if len(p)<2 or p[0] not in PAYMENT_METHODS:
        return await update.message.reply_text("ফরম্যাট:\\n/setpayment বিকাশ | 01XXXXXXXXX | Personal নম্বরে Send Money করুন")
    method, number = p[0], p[1]
    instruction = p[2] if len(p)>2 else "পেমেন্ট করার পর Transaction ID দিন।"
    ref=db.collection("settings").document("payments")
    ref.set({method:{"number":number,"instruction":instruction,"active":True}},merge=True)
    await update.message.reply_text(f"✅ {method} পেমেন্ট সেটিংস সংরক্ষণ হয়েছে।")

async def togglepayment(update, context):
    if not is_admin(update.effective_user.id): return
    if len(context.args)!=2 or context.args[0] not in PAYMENT_METHODS or context.args[1].lower() not in ("on","off"):
        return await update.message.reply_text("ফরম্যাট: /togglepayment বিকাশ on অথবা /togglepayment বিকাশ off")
    method, state=context.args[0], context.args[1].lower()
    ref=db.collection("settings").document("payments")
    ref.set({method:{"active":state=="on"}},merge=True)
    await update.message.reply_text(f"✅ {method}: {'চালু' if state=='on' else 'বন্ধ'}")

async def paymentsettings(update, context):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(payment_text()+"\\n\\nনম্বর সেট: /setpayment Method | Number | Instructions\\nচালু/বন্ধ: /togglepayment Method on/off",parse_mode="Markdown")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=(update.message.text or "").strip(); uid=update.effective_user.id
    if text=="🛍 Services": return await show_services(update,context)
    if text=="👤 My Account": return await account(update,context)
    if text=="➕ Add Funds": return await add_funds(update,context)
    if text=="📦 My Orders": return await show_orders(update,context)
    if text=="📞 Support": return await support(update,context)
    if text=="ℹ️ Help": return await help_cmd(update,context)
    state=context.user_data.get("state")
    if state=="deposit_amount":
        try:
            amount=float(text)
            if amount<=0 or amount>1000000: raise ValueError()
            context.user_data["deposit_amount"]=amount; context.user_data["state"]="deposit_method"
            await update.message.reply_text(f"পরিমাণ: {money(amount)}\nপেমেন্টের মাধ্যম/TrxID লিখুন।\n\n{PAYMENT_INSTRUCTIONS}")
        except ValueError: await update.message.reply_text("সঠিক পরিমাণ লিখুন, যেমন 500")
        return
    if state=="deposit_method":
        amount=context.user_data.pop("deposit_amount",0); context.user_data.pop("state",None)
        ref=db.collection("deposits").document()
        ref.set({"deposit_id":ref.id,"user_id":uid,"amount":amount,"details":text,"status":"pending","created_at":now()})
        await update.message.reply_text("✅ Add Funds রিকোয়েস্ট জমা হয়েছে। অ্যাডমিন যাচাই করবেন।",reply_markup=HOME)
        for aid in ADMIN_IDS:
            try: await context.bot.send_message(aid,f"💳 নতুন Deposit Request\nID: {ref.id}\nUser: {uid}\nAmount: {money(amount)}\nDetails: {text}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Approve",callback_data=f"depok:{ref.id}"),InlineKeyboardButton("Reject",callback_data=f"depno:{ref.id}")]]))
            except Exception: pass
        return
    if state and state.startswith("order_link:"):
        sid=state.split(":",1)[1]; s=db.collection("services").document(sid).get()
        if not s.exists: context.user_data.clear(); return await update.message.reply_text("সার্ভিস পাওয়া যায়নি।")
        context.user_data["order_link"]=text; context.user_data["state"]="order_qty:"+sid
        await update.message.reply_text("কত Quantity চান? শুধু সংখ্যা লিখুন।")
        return
    if state and state.startswith("order_qty:"):
        sid=state.split(":",1)[1]
        try: qty=int(text)
        except ValueError: return await update.message.reply_text("Quantity সংখ্যা দিয়ে লিখুন।")
        snap=db.collection("services").document(sid).get()
        if not snap.exists: context.user_data.clear(); return await update.message.reply_text("সার্ভিস পাওয়া যায়নি।")
        s=snap.to_dict()
        if qty<s["min"] or qty>s["max"]: return await update.message.reply_text(f"Quantity {s['min']} থেকে {s['max']} হতে হবে।")
        total=round(qty*float(s["price_per_1000"])/1000,2)
        context.user_data.update({"state":"order_confirm:"+sid,"order_qty":qty,"order_total":total})
        kb=[[InlineKeyboardButton("✅ Confirm Order",callback_data=f"orderconfirm:{sid}"),InlineKeyboardButton("❌ Cancel",callback_data="cancel")]]
        await update.message.reply_text(f"অর্ডার নিশ্চিত করবেন?\nসার্ভিস: {s['name']}\nQuantity: {qty}\nলিংক: {context.user_data['order_link']}\nমূল্য: {money(total)}",reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text("মেনু থেকে একটি অপশন বেছে নিন।",reply_markup=HOME)

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); data=q.data; uid=q.from_user.id
    if data=="cancel": context.user_data.clear(); return await q.edit_message_text("অর্ডার বাতিল করা হয়েছে।")
    if data.startswith("svc:"):
        sid=data.split(":",1)[1]; snap=db.collection("services").document(sid).get()
        if not snap.exists: return await q.edit_message_text("সার্ভিস পাওয়া যায়নি।")
        s=snap.to_dict(); context.user_data["state"]="order_link:"+sid
        return await q.edit_message_text(f"**{s['name']}**\nCategory: {s.get('category')}\nPrice: {money(s['price_per_1000'])}/1000\nMin: {s['min']} | Max: {s['max']}\n\nআপনার Target Link পাঠান।",parse_mode="Markdown")
    if data.startswith("orderconfirm:"):
        sid=data.split(":",1)[1]; qty=context.user_data.get("order_qty"); total=context.user_data.get("order_total"); link=context.user_data.get("order_link")
        if not qty or not total or not link: return await q.edit_message_text("সেশন শেষ। আবার অর্ডার করুন।")
        uref=user_ref(uid); u=get_user(uid); bal=float(u.get("balance",0))
        if bal<total: context.user_data.clear(); return await q.edit_message_text(f"❌ পর্যাপ্ত ব্যালেন্স নেই। প্রয়োজন {money(total)}, আছে {money(bal)}")
        sref=db.collection("services").document(sid).get()
        if not sref.exists: return await q.edit_message_text("সার্ভিস পাওয়া যায়নি।")
        s=sref.to_dict(); oid=uuid.uuid4().hex[:10].upper()
        uref.update({"balance":round(bal-total,2)})
        db.collection("orders").document(oid).set({"order_id":oid,"user_id":uid,"service_id":sid,"service_name":s["name"],"link":link,"quantity":qty,"total":total,"status":"pending","created_at":now()})
        context.user_data.clear()
        await q.edit_message_text(f"✅ অর্ডার জমা হয়েছে!\nOrder ID: #{oid}\nStatus: Pending\nমূল্য: {money(total)}")
        for aid in ADMIN_IDS:
            try: await context.bot.send_message(aid,f"🆕 নতুন অর্ডার\nID: #{oid}\nUser: {uid}\nService: {s['name']}\nQuantity: {qty}\nLink: {link}\nAmount: {money(total)}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Processing",callback_data=f"ost:{oid}:processing"),InlineKeyboardButton("✅ Complete",callback_data=f"ost:{oid}:completed")],[InlineKeyboardButton("❌ Reject + Refund",callback_data=f"ost:{oid}:rejected")]]))
            except Exception: pass
        return
    if data.startswith("admin:"):
        if not is_admin(uid): return
        kind=data.split(":")[1]
        if kind=="orders":
            docs=list(db.collection("orders").where("status","==","pending").stream())[:15]
            if not docs: return await q.edit_message_text("Pending order নেই।")
            for d in docs:
                o=d.to_dict()
                await context.bot.send_message(uid,f"#{o['order_id']} | {o['service_name']} | {o['quantity']} | {o['link']} | {money(o['total'])}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Processing",callback_data=f"ost:{o['order_id']}:processing"),InlineKeyboardButton("Complete",callback_data=f"ost:{o['order_id']}:completed")],[InlineKeyboardButton("Reject + Refund",callback_data=f"ost:{o['order_id']}:rejected")]]))
            return await q.edit_message_text("Pending orders পাঠানো হয়েছে।")
        if kind=="deposits":
            docs=list(db.collection("deposits").where("status","==","pending").stream())[:15]
            if not docs: return await q.edit_message_text("Pending deposit নেই।")
            for d in docs:
                x=d.to_dict()
                await context.bot.send_message(uid,f"Deposit {x['deposit_id']}\nUser: {x['user_id']}\nAmount: {money(x['amount'])}\nDetails: {x['details']}",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Approve",callback_data=f"depok:{x['deposit_id']}"),InlineKeyboardButton("Reject",callback_data=f"depno:{x['deposit_id']}")]]))
            return await q.edit_message_text("Deposit requests পাঠানো হয়েছে।")
        if kind=="stats":
            users=len(list(db.collection("users").stream())); orders=len(list(db.collection("orders").stream()))
            return await q.edit_message_text(f"📊 Statistics\nUsers: {users}\nOrders: {orders}")
    if data.startswith("ost:"):
        if not is_admin(uid): return
        _,oid,status=data.split(":")
        ref=db.collection("orders").document(oid); snap=ref.get()
        if not snap.exists: return await q.edit_message_text("অর্ডার পাওয়া যায়নি।")
        o=snap.to_dict()
        if o["status"] in ("completed","rejected"): return await q.edit_message_text("এই অর্ডার আগে থেকেই শেষ হয়েছে।")
        ref.update({"status":status,"updated_at":now()})
        if status=="rejected":
            uref=user_ref(o["user_id"]); u=get_user(o["user_id"]); uref.update({"balance":round(float(u.get("balance",0))+float(o["total"]),2)})
        try: await context.bot.send_message(o["user_id"],f"আপনার অর্ডার #{oid} এর স্ট্যাটাস: {status}"+("\nটাকা ফেরত দেওয়া হয়েছে।" if status=="rejected" else ""))
        except Exception: pass
        return await q.edit_message_text(f"অর্ডার #{oid}: {status}")
    if data.startswith(("depok:","depno:")):
        if not is_admin(uid): return
        action,did=data.split(":",1); ref=db.collection("deposits").document(did); snap=ref.get()
        if not snap.exists: return await q.edit_message_text("Request পাওয়া যায়নি।")
        x=snap.to_dict()
        if x["status"]!="pending": return await q.edit_message_text("এটি আগে থেকেই প্রসেস করা হয়েছে।")
        status="approved" if action=="depok" else "rejected"
        ref.update({"status":status,"updated_at":now()})
        if status=="approved":
            uref=user_ref(x["user_id"]); u=get_user(x["user_id"]); uref.update({"balance":round(float(u.get("balance",0))+float(x["amount"]),2)})
        try: await context.bot.send_message(x["user_id"],f"আপনার Deposit {did}: {status}"+(f"\nনতুন ব্যালেন্স: {money(get_user(x['user_id']).get('balance',0))}" if status=="approved" else ""))
        except Exception: pass
        return await q.edit_message_text(f"Deposit {did}: {status}")

async def error_handler(update, context):
    log.exception("Update failed", exc_info=context.error)
    if update and update.effective_message:
        try: await update.effective_message.reply_text("একটি সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।")
        except Exception: pass

def main():
    if not ADMIN_IDS: raise RuntimeError("ADMIN_IDS সেট করা হয়নি।")
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help_cmd))
    app.add_handler(CommandHandler("admin",admin_panel))
    app.add_handler(CommandHandler("addservice",addservice))
    app.add_handler(CommandHandler("setpayment",setpayment))
    app.add_handler(CommandHandler("togglepayment",togglepayment))
    app.add_handler(CommandHandler("paymentsettings",paymentsettings))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,on_text))
    app.add_error_handler(error_handler)
    log.info("SALMAN SMM PANEL is running")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()
