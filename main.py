import os
import json
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8003913696:AAFzWOmJIBA5lGA3ezQV1_DcLMcCbIZo86s")

# أسئلة PHQ-9 للاكتئاب
PHQ9_QUESTIONS = [
    {
        "id": "q1",
        "text": "قلة الاهتمام أو المتعة في فعل الأشياء",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q2", 
        "text": "الشعور بالإحباط أو الاكتئاب أو اليأس",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q3",
        "text": "صعوبة في النوم أو النوم أكثر من اللازم",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q4",
        "text": "الشعور بالتعب أو قلة الطاقة",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q5",
        "text": "ضعف الشهية أو الإفراط في الأكل",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q6",
        "text": "الشعور السيء تجاه نفسك أو أنك فاشل",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q7",
        "text": "صعوبة في التركيز على الأشياء",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q8",
        "text": "التحرك أو التحدث ببطء شديد أو العكس",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    {
        "id": "q9",
        "text": "أفكار أنه من الأفضل أن تموت أو إيذاء نفسك",
        "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    }
]

def init_database():
    """إنشاء قاعدة البيانات"""
    conn = sqlite3.connect('mental_health.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        answers TEXT,
        total_score INTEGER,
        risk_level TEXT,
        timestamp TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت"""
    user = update.effective_user
    
    welcome_text = f"""
🧠 **أهلاً وسهلاً {user.first_name}!**

مرحباً بك في نظام تقييم الصحة النفسية المتقدم 🌟

**ما نقدمه لك:**
✅ تقييم نفسي علمي معتمد (PHQ-9)
✅ تحليل ذكي لحالتك النفسية  
✅ توصيات علاجية مخصصة
✅ خصوصية وأمان كاملين

⚠️ **تنبيه مهم:**
هذا التقييم للإرشاد الأولي ولا يغني عن استشارة طبيب مختص

**هل تريد بدء التقييم النفسي؟**
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 نعم، ابدأ التقييم", callback_data="start_assessment")],
        [InlineKeyboardButton("ℹ️ معلومات أكثر", callback_data="more_info")],
        [InlineKeyboardButton("❌ لا، شكراً", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_assessment":
        await start_assessment(query, context)
    elif query.data == "more_info":
        await show_more_info(query, context)
    elif query.data == "cancel":
        await cancel_assessment(query, context)
    elif query.data.startswith("answer_"):
        await handle_answer(query, context)
    elif query.data == "new_assessment":
        await start_assessment(query, context)

async def start_assessment(query, context):
    """بدء التقييم النفسي"""
    context.user_data['current_question'] = 0
    context.user_data['answers'] = {}
    context.user_data['start_time'] = datetime.now()
    
    await send_question(query, context)

async def send_question(query, context):
    """إرسال السؤال التالي"""
    question_index = context.user_data.get('current_question', 0)
    
    if question_index >= len(PHQ9_QUESTIONS):
        await complete_assessment(query, context)
        return
    
    question = PHQ9_QUESTIONS[question_index]
    
    # إنشاء أزرار الإجابات
    keyboard = []
    for i, (option_text, score) in enumerate(question['options']):
        callback_data = f"answer_{question['id']}_{i}_{score}"
        keyboard.append([InlineKeyboardButton(option_text, callback_data=callback_data)])
    
    question_text = f"""
📋 **استبيان الصحة النفسية (PHQ-9)**

**السؤال {question_index + 1} من {len(PHQ9_QUESTIONS)}**

❓ **خلال الأسبوعين الماضيين، كم مرة تضايقت من:**

{question['text']}

**اختر الإجابة المناسبة:**
    """
    
    try:
        await query.edit_message_text(
            question_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except:
        await query.message.reply_text(
            question_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def handle_answer(query, context):
    """معالجة إجابة المستخدم"""
    # تحليل البيانات المرسلة
    parts = query.data.split("_")
    question_id = parts[1]
    option_index = int(parts[2])
    score = int(parts[3])
    
    # حفظ الإجابة
    context.user_data['answers'][question_id] = score
    
    # عرض الإجابة المختارة
    question_index = context.user_data.get('current_question', 0)
    selected_option = PHQ9_QUESTIONS[question_index]['options'][option_index][0]
    
    await query.edit_message_text(f"✅ **تم اختيار:** {selected_option}")
    
    # الانتقال للسؤال التالي
    context.user_data['current_question'] = question_index + 1
    
    # انتظار قصير ثم إرسال السؤال التالي
    await asyncio.sleep(1.5)
    await send_question(query, context)

async def complete_assessment(query, context):
    """إكمال التقييم وإعطاء النتائج"""
    answers = context.user_data.get('answers', {})
    total_score = sum(answers.values())
    
    # تحديد مستوى المخاطر
    if total_score <= 4:
        risk_level = "منخفض"
        severity = "أعراض اكتئاب طفيفة أو معدومة"
        color = "🟢"
    elif total_score <= 9:
        risk_level = "خفيف"
        severity = "أعراض اكتئاب خفيفة"
        color = "🟡"
    elif total_score <= 14:
        risk_level = "متوسط"
        severity = "أعراض اكتئاب متوسطة"
        color = "🟠"
    elif total_score <= 19:
        risk_level = "عالي"
        severity = "أعراض اكتئاب متوسطة إلى شديدة"
        color = "🔴"
    else:
        risk_level = "عالي جداً"
        severity = "أعراض اكتئاب شديدة"
        color = "🚨"
    
    # حفظ النتائج في قاعدة البيانات
    user = query.from_user
    save_assessment(user.id, user.username, user.first_name, answers, total_score, risk_level)
    
    # إنشاء التوصيات
    recommendations = generate_recommendations(total_score, answers)
    
    # إنشاء التقرير
    report = f"""
🧠 **تقرير التقييم النفسي الشامل**

👤 **المستخدم:** {user.first_name}
📅 **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 **النتائج:**
{color} **النتيجة الإجمالية:** {total_score}/27
{color} **التصنيف:** {severity}
{color} **مستوى المخاطر:** {risk_level}

💡 **التوصيات العلاجية:**
{chr(10).join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations))}

📞 **خطوط المساعدة العاجلة:**
• خط المساعدة النفسية: 920033360
• الطوارئ: 997
• خط الأمان الوطني: 1919

⚠️ **تنبيه مهم:**
هذا التقييم للإرشاد الأولي فقط ولا يغني عن التشخيص الطبي المتخصص.

💙 **رسالة أمل:**
مهما كانت النتيجة، تذكر أن طلب المساعدة خطوة شجاعة نحو التحسن.
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 إجراء تقييم جديد", callback_data="new_assessment")],
        [InlineKeyboardButton("📋 نصائح إضافية", callback_data="more_tips")]
    ]
    
    await query.message.reply_text(
        report,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def generate_recommendations(score, answers):
    """إنشاء توصيات مخصصة"""
    recommendations = []
    
    # توصيات حسب النتيجة الإجمالية
    if score >= 20:
        recommendations.extend([
            "🚨 **عاجل**: استشارة طبيب نفسي فوراً",
            "💊 مناقشة العلاج الدوائي مع مختص",
            "🏥 زيارة أقرب مستشفى للتقييم العاجل"
        ])
    elif score >= 15:
        recommendations.extend([
            "👨‍⚕️ استشارة طبيب نفسي أو أخصائي نفسي",
            "🧠 العلاج النفسي المعرفي السلوكي (CBT)",
            "💊 تقييم الحاجة للعلاج الدوائي"
        ])
    elif score >= 10:
        recommendations.extend([
            "🩺 استشارة أخصائي نفسي",
            "🏃‍♂️ ممارسة الرياضة 30 دقيقة يومياً",
            "🧘‍♀️ تعلم تقنيات الاسترخاء والتأمل"
        ])
    else:
        recommendations.extend([
            "💚 الحفاظ على الأنشطة الإيجابية",
            "🤝 تقوية العلاقات الاجتماعية",
            "😴 الحفاظ على نظام نوم صحي"
        ])
    
    # توصيات خاصة حسب الأعراض
    if answers.get('q9', 0) > 0:  # أفكار إيذاء النفس
        recommendations.insert(0, "🚨 **أولوية قصوى**: التواصل الفوري مع خطوط الطوارئ")
    
    if answers.get('q3', 0) >= 2:  # مشاكل النوم
        recommendations.append("😴 استشارة طبيب حول اضطرابات النوم")
    
    if answers.get('q4', 0) >= 2:  # التعب
        recommendations.append("⚡ فحص طبي شامل لاستبعاد أسباب جسدية")
    
    return recommendations[:6]  # أول 6 توصيات

def save_assessment(user_id, username, first_name, answers, total_score, risk_level):
    """حفظ التقييم في قاعدة البيانات"""
    conn = sqlite3.connect('mental_health.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO assessments (user_id, username, first_name, answers, total_score, risk_level, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, json.dumps(answers), total_score, risk_level, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

async def show_more_info(query, context):
    """عرض معلومات إضافية"""
    info_text = """
📖 **معلومات حول التقييم النفسي**

🎯 **ما هو استبيان PHQ-9؟**
هو أداة تشخيص معتمدة عالمياً لتقييم أعراض الاكتئاب

🔬 **الأساس العلمي:**
• طورته منظمة الصحة العالمية
• مستخدم في المستشفيات والعيادات
• دقة عالية في التشخيص الأولي

🛡️ **الخصوصية:**
• بياناتك محمية ومشفرة
• لا نشارك معلوماتك مع أي طرف ثالث
• يمكنك حذف بياناتك في أي وقت

⏱️ **المدة:**
التقييم يستغرق 5-7 دقائق فقط

هل تريد بدء التقييم الآن؟
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 نعم، ابدأ التقييم", callback_data="start_assessment")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="cancel")]
    ]
    
    await query.edit_message_text(
        info_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def cancel_assessment(query, context):
    """إلغاء التقييم"""
    cancel_text = """
✋ **تم إلغاء التقييم**

لا مشكلة! يمكنك العودة في أي وقت تريده.

💡 **تذكر:**
• صحتك النفسية مهمة
• طلب المساعدة علامة قوة
• نحن هنا عندما تكون مستعداً

اكتب /start للعودة في أي وقت

🌟 **في رعاية الله**
    """
    
    await query.edit_message_text(cancel_text, parse_mode='Markdown')

def main():
    """تشغيل البوت"""
    # إنشاء قاعدة البيانات
    init_database()
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # بدء تشغيل البوت
    logger.info("🚀 بوت الصحة النفسية يعمل الآن!")
    application.run_polling()

if __name__ == '__main__':
    main()
