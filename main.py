https://t.me/everyyyyyyyyyydayhttps://t.me/everyyyyyyyyyyday
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
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler,
    ConversationHandler
)
import asyncio
import logging
import hashlib
import re
from collections import defaultdict

# تمكين التسجيل الشامل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('mental_health_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# تكوين البوت - استخدم متغيرات البيئة فقط!
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@everyyyyyyyyyyday")
GROUP_LINK = os.getenv("TELEGRAM_GROUP_LINK", "https://t.me/your_mental_health_group")
DATABASE_PATH = "mental_health_data.db"

# حالات المحادثة
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
    created_at: datetime = datetime.now()
    last_assessment: datetime = None
    risk_level: str = "unknown"
    total_assessments: int = 0

class AssessmentSystem:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # إنشاء جدول المستخدمين
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            age INTEGER,
            gender TEXT,
            created_at TEXT,
            last_assessment TEXT,
            risk_level TEXT,
            total_assessments INTEGER
        )
        ''')
        
        # إنشاء جدول التقييمات
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_type TEXT,
            score INTEGER,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        ''')
        
        self.conn.commit()
    
    def save_user_profile(self, user: UserProfile):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, age, gender, created_at, last_assessment, risk_level, total_assessments)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.user_id,
            user.username,
            user.first_name,
            user.age,
            user.gender,
            user.created_at.isoformat(),
            user.last_assessment.isoformat() if user.last_assessment else None,
            user.risk_level,
            user.total_assessments
        ))
        self.conn.commit()
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return UserProfile(
                user_id=row[0],
                username=row[1],
                first_name=row[2],
                age=row[3],
                gender=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_assessment=datetime.fromisoformat(row[6]) if row[6] else None,
                risk_level=row[7],
                total_assessments=row[8]
            )
        return None

# تهيئة نظام التقييم
assessment_system = AssessmentSystem()

# تعريف معالجات الأوامر
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"User {user.id} started the conversation")
    
    # التحقق من وجود ملف تعريف المستخدم أو إنشاء واحد جديد
    profile = assessment_system.get_user_profile(user.id)
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        assessment_system.save_user_profile(profile)
    
    # إنشاء لوحة مفاتيح مخصصة
    keyboard = [
        [InlineKeyboardButton("بدء التقييم", callback_data="start_assessment")],
        [InlineKeyboardButton("مساعدة", callback_data="help")],
        [InlineKeyboardButton("انضمام للمجموعة", url=GROUP_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال رسالة الترحيب
    welcome_message = (
        f"مرحبًا {user.first_name}! 👋\n"
        "أنا بوت الصحة النفسية المصمم لمساعدتك في تتبع صحتك النفسية.\n\n"
        "يمكنك إجراء تقييمات نفسية متنوعة، والحصول على تحليلات فورية، "
        "وتلقي نصائح مخصصة بناءً على نتائجك.\n\n"
        "كيف يمكنني مساعدتك اليوم؟"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )
    
    return START

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال رسالة المساعدة عندما يتم إصدار الأمر /help"""
    help_text = (
        "أنا هنا لمساعدتك في تتبع صحتك النفسية.\n\n"
        "الأوامر المتاحة:\n"
        "/start - بدء المحادثة مع البوت\n"
        "/help - عرض هذه الرسالة\n"
        "/assessment - بدء تقييم جديد\n\n"
        "يمكنك إجراء عدة أنواع من التقييمات:\n"
        "- PHQ-9: تقييم الاكتئاب\n"
        "- GAD-7: تقييم القلق\n"
        "- PSS: مقياس الإجهاد\n\n"
        "النتائج تبقى سرية، ويمكنك مشاركتها مع متخصص إذا رغبت."
    )
    
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل النصية العادية"""
    text = update.message.text
    user = update.effective_user
    
    logger.info(f"Received message from {user.id}: {text}")
    
    # الرد على التحيات الشائعة
    greetings = ["مرحبا", "اهلا", "سلام", "السلام عليكم", "اهلين", "هاي"]
    if any(greet in text.lower() for greet in greetings):
        await update.message.reply_text(f"وعليكم السلام ورحمة الله! كيف يمكنني مساعدتك اليوم {user.first_name}?")
    else:
        await update.message.reply_text(
            "أنا هنا لمساعدتك في التقييمات النفسية. "
            "يمكنك استخدام /start لبدء تقييم جديد أو /help للحصول على المساعدة."
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة ضغطات أزرار الإنلاين"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    if data == "start_assessment":
        # عرض خيارات التقييم
        keyboard = [
            [InlineKeyboardButton("PHQ-9 (تقييم الاكتئاب)", callback_data="phq9")],
            [InlineKeyboardButton("GAD-7 (تقييم القلق)", callback_data="gad7")],
            [InlineKeyboardButton("PSS (مقياس الإجهاد)", callback_data="pss")],
            [InlineKeyboardButton("بيك للاكتئاب", callback_data="beck_depression")],
            [InlineKeyboardButton("بيك للقلق", callback_data="beck_anxiety")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="اختر نوع التقييم الذي ترغب في إجرائه:",
            reply_markup=reply_markup
        )
    elif data == "help":
        await help_command(update, context)
    else:
        await query.edit_message_text(
            text="بدأ التقييم. سأرسل لك سؤالًا تلو الآخر."
        )
        # هنا يمكنك بدء عملية التقييم الفعلية

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الخطأ وإرسال رسالة إلى المستخدم"""
    logger.error("حدث خطأ أثناء معالجة التحديث:", exc_info=context.error)
    
    if update.message:
        await update.message.reply_text(
            "عذرًا، حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى لاحقًا."
        )

def main() -> None:
    """بدء تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالج المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START: [
                CallbackQueryHandler(button_handler),
                CommandHandler('help', help_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            ],
            ASSESSMENT_SELECTION: [
                CallbackQueryHandler(button_handler),
                CommandHandler('help', help_command)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    # تسجيل معالجات الأوامر
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    # تسجيل معالج الرسائل العادية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تسجيل معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء البوت
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()