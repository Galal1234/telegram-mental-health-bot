import os
import json
import random
import schedule
import time
import threading
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
import logging
import hashlib
import re
from collections import defaultdict

# Enable comprehensive logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('mental_health_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8003913696:AAFzWOmJIBA5lGA3ezQV1_DcLMcCbIZo86s")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@everyyyyyyyyyyday")
GROUP_LINK = os.getenv("TELEGRAM_GROUP_LINK", "https://t.me/your_mental_health_group")
DATABASE_PATH = "mental_health_data.db"

# Conversation states
(START, ASSESSMENT_SELECTION, PHQ9_TEST, GAD7_TEST, PSS_TEST, 
 BECK_ANXIETY, BECK_DEPRESSION, CUSTOM_ASSESSMENT, ANALYSIS, 
 FOLLOW_UP, END) = range(11)

@dataclass
class UserProfile:
    user_id: int
    username: str
    first_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    created_at: datetime = None
    last_assessment: datetime = None
    risk_level: str = "unknown"
    total_assessments: int = 0

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with comprehensive schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            age INTEGER,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_assessment TIMESTAMP,
            risk_level TEXT DEFAULT 'unknown',
            total_assessments INTEGER DEFAULT 0,
            emergency_contact TEXT,
            consent_given BOOLEAN DEFAULT FALSE
        )
        ''')
        
        # Assessments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            assessment_type TEXT,
            raw_scores TEXT,
            calculated_scores TEXT,
            risk_level TEXT,
            severity TEXT,
            recommendations TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            follow_up_needed BOOLEAN,
            counselor_notified BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # User responses table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            assessment_id INTEGER,
            question_id TEXT,
            question_text TEXT,
            response_text TEXT,
            response_score INTEGER,
            response_time_seconds INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (assessment_id) REFERENCES assessments (id)
        )
        ''')
        
        # Notifications table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            notification_type TEXT,
            message TEXT,
            scheduled_time TIMESTAMP,
            sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

class ClinicalAssessments:
    """World-standard clinical assessments for mental health"""
    
    # PHQ-9 Questions
    PHQ9_QUESTIONS = [
        {
            "id": "phq9_1",
            "question": "قلة الاهتمام أو المتعة في فعل الأشياء",
            "category": "فقدان الاهتمام",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_2", 
            "question": "الشعور بالإحباط أو الاكتئاب أو اليأس",
            "category": "المزاج المكتئب",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_3",
            "question": "صعوبة في النوم أو النوم أكثر من اللازم",
            "category": "اضطرابات النوم",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_4",
            "question": "الشعور بالتعب أو قلة الطاقة",
            "category": "التعب والطاقة",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_5",
            "question": "ضعف الشهية أو الإفراط في الأكل",
            "category": "الشهية",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_6",
            "question": "الشعور السيء تجاه نفسك - أو أنك فاشل أو خذلت نفسك أو عائلتك",
            "category": "تقدير الذات",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_7",
            "question": "صعوبة في التركيز على الأشياء مثل قراءة الجريدة أو مشاهدة التلفزيون",
            "category": "التركيز",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_8",
            "question": "التحرك أو التحدث ببطء شديد بحيث يلاحظ الآخرون، أو العكس - التململ أو الحركة الزائدة",
            "category": "الحركة النفسية",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "phq9_9",
            "question": "أفكار أنه من الأفضل أن تموت أو إيذاء نفسك بطريقة ما",
            "category": "الأفكار الانتحارية",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        }
    ]
    
    # GAD-7 Questions
    GAD7_QUESTIONS = [
        {
            "id": "gad7_1",
            "question": "الشعور بالعصبية أو القلق أو التوتر",
            "category": "القلق العام",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_2",
            "question": "عدم القدرة على التوقف عن القلق أو السيطرة عليه",
            "category": "التحكم في القلق",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_3",
            "question": "القلق الشديد حول أشياء مختلفة",
            "category": "القلق المفرط",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_4",
            "question": "صعوبة في الاسترخاء",
            "category": "الاسترخاء",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_5",
            "question": "الشعور بالقلق الشديد لدرجة صعوبة البقاء ساكناً",
            "category": "القلق الحركي",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_6",
            "question": "الانزعاج أو الغضب بسهولة",
            "category": "التهيج",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        },
        {
            "id": "gad7_7",
            "question": "الشعور بالخوف كما لو أن شيئاً فظيعاً قد يحدث",
            "category": "توقع الكارثة",
            "options": [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
        }
    ]

class AIAnalyzer:
    """AI analysis for mental health assessments"""
    
    def __init__(self):
        self.response_patterns = {
            'emotional_indicators': {
                'positive': ['سعيد', 'مرتاح', 'هادئ', 'متفائل', 'راضي'],
                'negative': ['حزين', 'قلق', 'خائف', 'غاضب', 'محبط'],
                'extreme': ['انتحار', 'موت', 'إيذاء', 'نهاية']
            }
        }
    
    def analyze_text_response(self, text: str) -> Dict[str, float]:
        """Analyze text responses"""
        text_lower = text.lower()
        scores = {
            'emotional_distress': 0.0,
            'risk_indicators': 0.0
        }
        
        negative_count = sum(1 for word in self.response_patterns['emotional_indicators']['negative'] 
                           if word in text_lower)
        extreme_count = sum(1 for word in self.response_patterns['emotional_indicators']['extreme'] 
                          if word in text_lower)
        
        scores['emotional_distress'] = min(1.0, negative_count * 0.2)
        scores['risk_indicators'] = min(1.0, extreme_count * 0.5)
        
        return scores
    
    def calculate_composite_risk(self, assessment_scores: Dict[str, float], 
                               text_analysis: Dict[str, float]) -> Tuple[str, float]:
        """Calculate overall risk level"""
        total_score = 0.0
        
        if 'phq9_total' in assessment_scores:
            phq9_normalized = min(1.0, assessment_scores['phq9_total'] / 27.0)
            total_score += phq9_normalized * 0.4
        
        if 'gad7_total' in assessment_scores:
            gad7_normalized = min(1.0, assessment_scores['gad7_total'] / 21.0)
            total_score += gad7_normalized * 0.3
        
        text_risk = text_analysis.get('risk_indicators', 0) * 2 + text_analysis.get('emotional_distress', 0)
        total_score += text_risk * 0.3
        
        if total_score >= 0.8:
            return "عالي جداً - طوارئ", total_score
        elif total_score >= 0.6:
            return "عالي", total_score
        elif total_score >= 0.4:
            return "متوسط", total_score
        else:
            return "منخفض", total_score

class AdvancedMentalHealthBot:
    """Advanced Mental Health Assessment Bot"""
    
    def __init__(self):
        self.db = DatabaseManager(DATABASE_PATH)
        self.assessments = ClinicalAssessments()
        self.ai_analyzer = AIAnalyzer()
        self.app_instance = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command"""
        user = update.effective_user
        
        # Check if user exists
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user.id, user.username, user.first_name, datetime.now()))
            conn.commit()
            
            welcome_message = f"""
🌟 **أهلاً وسهلاً {user.first_name}!**

أنا نظام تقييم الصحة النفسية المتقدم، مصمم لتقديم تقييم علمي دقيق وشامل.

🎯 **ما أقدمه:**
• تقييمات نفسية معتمدة عالمياً (PHQ-9, GAD-7)
• تحليل ذكي باستخدام الذكاء الاصطناعي
• توصيات علاجية مخصصة
• متابعة دورية ودعم مستمر

⚠️ **مهم:** هذا للتقييم الأولي ولا يغني عن استشارة طبيب مختص.

هل توافق على بدء التقييم؟
            """
            
            keyboard = [
                [InlineKeyboardButton("موافق، ابدأ التقييم 🎯", callback_data="start_assessment")],
                [InlineKeyboardButton("غير موافق ❌", callback_data="decline")]
            ]
        else:
            welcome_message = f"👋 مرحباً بعودتك {user.first_name}!"
            keyboard = [
                [InlineKeyboardButton("تقييم جديد 🔄", callback_data="start_assessment")],
                [InlineKeyboardButton("عرض الإحصائيات 📈", callback_data="view_stats")]
            ]
        
        conn.close()
        await update.message.reply_text(welcome_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_assessment":
            await self.start_assessment(query, context)
        elif query.data.startswith("answer_"):
            await self.handle_answer(query, context)
    
    async def start_assessment(self, query, context):
        """Start PHQ-9 assessment"""
        context.user_data['current_assessment'] = 'phq9'
        context.user_data['question_index'] = 0
        context.user_data['answers'] = {}
        
        # Create assessment record
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO assessments (user_id, assessment_type, timestamp)
            VALUES (?, ?, ?)
        ''', (query.from_user.id, 'phq9', datetime.now()))
        context.user_data['assessment_id'] = cursor.lastrowid
        conn.commit()
        conn.close()
        
        await self.send_question(query, context)
    
    async def send_question(self, query, context):
        """Send current question"""
        question_index = context.user_data['question_index']
        questions = self.assessments.PHQ9_QUESTIONS
        
        if question_index >= len(questions):
            await self.complete_assessment(query, context)
            return
        
        question = questions[question_index]
        keyboard = []
        
        for i, (option_text, score) in enumerate(question['options']):
            callback_data = f"answer_{question['id']}_{i}_{score}"
            keyboard.append([InlineKeyboardButton(option_text, callback_data=callback_data)])
        
        message_text = f"""
📋 **استبيان الصحة النفسية (PHQ-9)**
السؤال {question_index + 1}/{len(questions)}

🔍 **{question['category']}**

❓ خلال الأسبوعين الماضيين، كم مرة تضايقت من:

{question['question']}
        """
        
        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    async def handle_answer(self, query, context):
        """Handle user answer"""
        parts = query.data.split("_")
        question_id = parts[1]
        option_index = int(parts[2])
        score = int(parts[3])
        
        # Store answer
        context.user_data['answers'][question_id] = score
        
        # Show selected answer
        questions = self.assessments.PHQ9_QUESTIONS
        selected_option = questions[context.user_data['question_index']]['options'][option_index][0]
        await query.edit_message_text(f"✅ تم اختيار: {selected_option}")
        
        # Move to next question
        context.user_data['question_index'] += 1
        
        await asyncio.sleep(1)
        await self.send_question(query, context)
    
    async def complete_assessment(self, query, context):
        """Complete assessment and provide analysis"""
        answers = context.user_data['answers']
        
        # Calculate PHQ-9 score
        total_score = sum(answers.values())
        
        # Determine severity
        if total_score <= 4:
            severity = "أعراض اكتئاب طفيفة"
            risk_level = "منخفض"
        elif total_score <= 9:
            severity = "أعراض اكتئاب خفيفة"
            risk_level = "منخفض إلى متوسط"
        elif total_score <= 14:
            severity = "أعراض اكتئاب متوسطة"
            risk_level = "متوسط"
        elif total_score <= 19:
            severity = "أعراض اكتئاب متوسطة إلى شديدة"
            risk_level = "عالي"
        else:
            severity = "أعراض اكتئاب شديدة"
            risk_level = "عالي جداً"
        
        # Generate recommendations
        recommendations = self.generate_recommendations(total_score, answers)
        
        # Update database
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE assessments 
            SET calculated_scores = ?, risk_level = ?, severity = ?, recommendations = ?
            WHERE id = ?
        ''', (json.dumps({'phq9_total': total_score}), risk_level, severity, 
              json.dumps(recommendations), context.user_data['assessment_id']))
        
        cursor.execute('''
            UPDATE users 
            SET last_assessment = ?, risk_level = ?, total_assessments = total_assessments + 1
            WHERE user_id = ?
        ''', (datetime.now(), risk_level, query.from_user.id))
        
        conn.commit()
        conn.close()
        
        # Generate report
        report = f"""
🧠 **تقرير التقييم النفسي**

📊 **النتائج:**
• النتيجة الإجمالية: {total_score}/27
• التصنيف: {severity}
• مستوى المخاطر: {risk_level}

💡 **التوصيات:**
"""
        
        for i, rec in enumerate(recommendations[:5], 1):
            report += f"{i}. {rec}\n"
        
        report += """
📞 **المساعدة الفورية:**
• خط المساعدة النفسية: 920033360
• الطوارئ: 997

⚠️ هذا التقييم للإرشاد فقط ولا يغني عن استشارة طبيب مختص.
        """
        
        await query.message.reply_text(report, parse_mode='Markdown')
        
        # Offer new assessment
        keyboard = [[InlineKeyboardButton("إجراء تقييم جديد 🔄", callback_data="start_assessment")]]
        await query.message.reply_text("هل تريد إجراء تقييم آخر؟", reply_markup=InlineKeyboardMarkup(keyboard))
    
    def generate_recommendations(self, score: int, answers: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if score >= 15:
            recommendations.extend([
                "🚨 استشارة طبيب نفسي فوراً لتقييم شامل",
                "💊 مناقشة العلاج الدوائي مع مختص",
                "🧠 العلاج النفسي المعرفي السلوكي (CBT)"
            ])
        elif score >= 10:
            recommendations.extend([
                "👨‍⚕️ استشارة طبيب نفسي أو أخصائي نفسي",
                "🏃‍♂️ ممارسة الرياضة 30 دقيقة يومياً",
                "🧘‍♀️ تقنيات الاسترخاء والتأمل"
            ])
        else:
            recommendations.extend([
                "💚 الحفاظ على الأنشطة الإيجابية",
                "🤝 التواصل الاجتماعي المنتظم",
                "😴 نظام نوم صحي ومنتظم"
            ])
        
        # Specific recommendations based on symptoms
        if answers.get('phq9_9', 0) > 0:  # Suicidal thoughts
            recommendations.insert(0, "🚨 **عاجل**: التواصل الفوري مع خط المساعدة أو الطوارئ")
        
        if answers.get('phq9_3', 0) >= 2:  # Sleep problems
            recommendations.append("😴 استشارة طبيب حول اضطرابات النوم")
        
        if answers.get('phq9_4', 0) >= 2:  # Fatigue
            recommendations.append("⚡ فحص طبي شامل لاستبعاد أسباب جسدية للتعب")
        
        return recommendations

def main():
    """Main function"""
    bot = AdvancedMentalHealthBot()
    
    try:
        bot.app_instance = Application.builder().token(TOKEN).build()
        bot.app_instance.add_handler(CommandHandler("start", bot.start_command))
        bot.app_instance.add_handler(CallbackQueryHandler(bot.handle_callback))
        
        logger.info("🚀 Mental Health Bot starting...")
        bot.app_instance.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
