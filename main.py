#!/usr/bin/env python3
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تمكين السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8003913696:AAFzWOmJIBA5lGA3ezQV1_DcLMcCbIZo86s")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    user = update.effective_user
    
    text = f"""
🌟 مرحباً {user.first_name}!

أنا بوت الصحة النفسية المتطور 🧠

✅ تقييم نفسي علمي دقيق
✅ تحليل ذكي للحالة النفسية  
✅ توصيات علاجية مخصصة
✅ خصوصية وأمان تامين

هل تريد بدء التقييم النفسي؟
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 نعم، ابدأ التقييم", callback_data="start_test")],
        [InlineKeyboardButton("ℹ️ معلومات أكثر", callback_data="info")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_test":
        await start_phq9_test(query, context)
    elif query.data == "info":
        await show_info(query)
    elif query.data == "cancel":
        await cancel(query)
    elif query.data.startswith("q_"):
        await handle_answer(query, context)

async def start_phq9_test(query, context):
    """بدء اختبار PHQ-9"""
    context.user_data['question'] = 0
    context.user_data['scores'] = []
    
    await send_question(query, context)

async def send_question(query, context):
    """إرسال السؤال"""
    questions = [
        "قلة الاهتمام أو المتعة في فعل الأشياء",
        "الشعور بالإحباط أو الاكتئاب أو اليأس", 
        "صعوبة في النوم أو النوم أكثر من اللازم",
        "الشعور بالتعب أو قلة الطاقة",
        "ضعف الشهية أو الإفراط في الأكل",
        "الشعور السيء تجاه نفسك",
        "صعوبة في التركيز على الأشياء",
        "التحرك أو التحدث ببطء شديد",
        "أفكار إيذاء النفس أو الموت"
    ]
    
    current_q = context.user_data.get('question', 0)
    
    if current_q >= len(questions):
        await show_results(query, context)
        return
    
    text = f"""
📋 **اختبار الصحة النفسية PHQ-9**

السؤال {current_q + 1} من {len(questions)}

❓ خلال الأسبوعين الماضيين، كم مرة تضايقت من:

**{questions[current_q]}**

اختر الإجابة المناسبة:
    """
    
    keyboard = [
        [InlineKeyboardButton("مطلقاً", callback_data=f"q_{current_q}_0")],
        [InlineKeyboardButton("عدة أيام", callback_data=f"q_{current_q}_1")],
        [InlineKeyboardButton("أكثر من نصف الأيام", callback_data=f"q_{current_q}_2")],
        [InlineKeyboardButton("تقريباً كل يوم", callback_data=f"q_{current_q}_3")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_answer(query, context):
    """معالجة الإجابة"""
    parts = query.data.split("_")
    question_num = int(parts[1])
    score = int(parts[2])
    
    # حفظ النتيجة
    if 'scores' not in context.user_data:
        context.user_data['scores'] = []
    
    while len(context.user_data['scores']) <= question_num:
        context.user_data['scores'].append(0)
    
    context.user_data['scores'][question_num] = score
    context.user_data['question'] = question_num + 1
    
    # عرض الإجابة المختارة
    options = ["مطلقاً", "عدة أيام", "أكثر من نصف الأيام", "تقريباً كل يوم"]
    await query.edit_message_text(f"✅ تم اختيار: {options[score]}")
    
    # إرسال السؤال التالي بعد ثانية
    import asyncio
    await asyncio.sleep(1)
    await send_question(query, context)

async def show_results(query, context):
    """عرض النتائج"""
    scores = context.user_data.get('scores', [])
    total = sum(scores)
    
    # تحديد الحالة
    if total <= 4:
        level = "طبيعي"
        color = "🟢"
        description = "لا توجد أعراض اكتئاب واضحة"
    elif total <= 9:
        level = "خفيف"  
        color = "🟡"
        description = "أعراض اكتئاب خفيفة"
    elif total <= 14:
        level = "متوسط"
        color = "🟠" 
        description = "أعراض اكتئاب متوسطة"
    elif total <= 19:
        level = "شديد"
        color = "🔴"
        description = "أعراض اكتئاب شديدة"
    else:
        level = "شديد جداً"
        color = "🚨"
        description = "أعراض اكتئاب شديدة جداً"
    
    # التوصيات
    if total >= 15:
        recommendations = [
            "🏥 استشارة طبيب نفسي فوراً",
            "💊 مناقشة العلاج الدوائي", 
            "🤝 طلب الدعم من الأهل والأصدقاء"
        ]
    elif total >= 10:
        recommendations = [
            "👨‍⚕️ استشارة أخصائي نفسي",
            "🏃‍♂️ ممارسة الرياضة يومياً",
            "🧘‍♀️ تعلم تقنيات الاسترخاء"
        ]
    else:
        recommendations = [
            "💚 الحفاظ على الأنشطة الإيجابية",
            "😴 نظام نوم صحي",
            "🤝 التواصل الاجتماعي"
        ]
    
    result_text = f"""
🧠 **نتائج التقييم النفسي**

{color} **النتيجة:** {total}/27
{color} **المستوى:** {level}
{color} **الوصف:** {description}

💡 **التوصيات:**
{chr(10).join(f"• {rec}" for rec in recommendations)}

📞 **خطوط المساعدة:**
• خط المساعدة النفسية: 920033360
• الطوارئ: 997

⚠️ **تنبيه:** هذا تقييم أولي ولا يغني عن استشارة طبيب مختص.

💙 **تذكر:** طلب المساعدة علامة قوة وليس ضعف!
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 اختبار جديد", callback_data="start_test")],
        [InlineKeyboardButton("ℹ️ نصائح إضافية", callback_data="tips")]
    ]
    
    await query.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_info(query):
    """عرض المعلومات"""
    info_text = """
📖 **معلومات حول الاختبار**

🎯 **ما هو PHQ-9؟**
استبيان معتمد عالمياً لتقييم أعراض الاكتئاب

🔬 **الأساس العلمي:**
• معتمد من منظمة الصحة العالمية
• يُستخدم في المستشفيات والعيادات
• دقة عالية في التشخيص الأولي

⏱️ **المدة:** 3-5 دقائق فقط
🛡️ **الخصوصية:** بياناتك محمية بالكامل

هل تريد بدء الاختبار؟
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 نعم، ابدأ الاختبار", callback_data="start_test")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="cancel")]
    ]
    
    await query.edit_message_text(info_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel(query):
    """إلغاء"""
    await query.edit_message_text("""
✋ **تم الإلغاء**

لا مشكلة! يمكنك العودة في أي وقت.

💡 **تذكر:**
صحتك النفسية مهمة، ونحن هنا عندما تكون مستعداً.

اكتب /start للعودة 🌟
    """)

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # طباعة رسالة البداية
    print("🚀 بوت الصحة النفسية يعمل الآن!")
    logger.info("🚀 Mental Health Bot is running!")
    
    # تشغيل البوت
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
