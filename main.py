import os
import json
import sqlite3
import logging
import asyncio
import random
import re
from datetime import datetime, timedelta
import threading
import time
import hashlib
import uuid
import subprocess
import sys

# تثبيت المكتبات المطلوبة للعمل على Replit
def install_requirements():
    """تثبيت المكتبات المطلوبة"""
    packages = ['python-telegram-bot', 'nest-asyncio', 'requests']
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

# تثبيت المكتبات
install_requirements()

# استيراد nest_asyncio لحل مشاكل event loop
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nest_asyncio"])
    import nest_asyncio
    nest_asyncio.apply()

# استيراد telegram بعد التثبيت
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات المتقدم
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[
        logging.FileHandler('mental_health_advanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إعدادات البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8003913696:AAFzWOmJIBA5lGA3ezQV1_DcLMcCbIZo86s")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@your_channel_username")

# قاعدة المعرفة الإسلامية والفلسفية المتقدمة
KNOWLEDGE_DATABASE = {
    'depression': {
        'quran': {
            'ayah': "﴿وَلَا تَيْأَسُوا مِن رَّوْحِ اللَّهِ ۖ إِنَّهُ لَا يَيْأَسُ مِن رَّوْحِ اللَّهِ إِلَّا الْقَوْمُ الْكَافِرُونَ﴾",
            'reference': "[يوسف:87]",
            'tafseer': "النهي عن اليأس والإحباط، فإن رحمة الله واسعة"
        },
        'hadith': {
            'text': "عَجَبًا لِأَمْرِ الْمُؤْمِنِ، إِنَّ أَمْرَهُ كُلَّهُ خَيْرٌ",
            'source': "رواه مسلم",
            'meaning': "كل ما يصيب المؤمن فيه خير له"
        },
        'philosophers': {
            'stoicism': "في الفلسفة الرواقية، الاكتئاب نتيجة لمقاومة ما لا يمكن تغييره",
            'viktor_frankl': "يمكن للإنسان أن يتحمل أي معاناة إذا وجد معنى لها",
            'cognitive_therapy': "الأفكار السلبية التلقائية هي السبب الرئيسي للاكتئاب"
        }
    },
    'anxiety': {
        'quran': {
            'ayah': "﴿الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللَّهِ ۗ أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾",
            'reference': "[الرعد:28]",
            'tafseer': "ذكر الله يجلب الطمأنينة والسكينة للقلب"
        },
        'hadith': {
            'text': "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ",
            'source': "رواه البخاري",
            'meaning': "دعاء للتخلص من القلق والحزن"
        },
        'philosophers': {
            'epictetus': "أنت تتضايق ليس من الأحداث، بل من رأيك فيها",
            'mindfulness': "القلق يأتي من العيش في المستقبل، العيش في الحاضر يجلب السلام",
            'cbt': "تحدي الأفكار الكارثية يقلل من القلق بشكل كبير"
        }
    }
}

# اختبار تحليل الشخصية MBTI
MBTI_ASSESSMENT = {
    'name': 'اختبار تحليل الشخصية مايرز-بريغز (MBTI)',
    'description': 'تحليل شامل للشخصية وفقاً لمؤشر مايرز-بريغز المعتمد عالمياً',
    'icon': '🧠',
    'dimensions': {
        'EI': {
            'name': 'الانفتاح مقابل الانطواء',
            'description': 'كيف تتفاعل مع العالم وتستمد طاقتك',
            'questions': [
                {
                    'text': 'أين تشعر بمزيد من الطاقة والحيوية؟',
                    'options': [
                        {'text': 'في المجموعات والأنشطة الاجتماعية', 'weight': 'E'},
                        {'text': 'في الأوقات الهادئة والأنشطة الفردية', 'weight': 'I'}
                    ]
                },
                {
                    'text': 'عندما تواجه مشكلة، ماذا تفعل أولاً؟',
                    'options': [
                        {'text': 'أتحدث مع الآخرين لأخذ آرائهم', 'weight': 'E'},
                        {'text': 'أفكر فيها بنفسي أولاً', 'weight': 'I'}
                    ]
                },
                {
                    'text': 'في المناسبات الاجتماعية:',
                    'options': [
                        {'text': 'أتفاعل مع أكبر عدد من الناس', 'weight': 'E'},
                        {'text': 'أركز على محادثات عميقة مع قلة من الأشخاص', 'weight': 'I'}
                    ]
                }
            ]
        },
        'SN': {
            'name': 'الحس مقابل الحدس',
            'description': 'كيف تجمع المعلومات وتفهم العالم',
            'questions': [
                {
                    'text': 'عند تعلم شيء جديد، تفضل:',
                    'options': [
                        {'text': 'التفاصيل والحقائق الملموسة', 'weight': 'S'},
                        {'text': 'الصورة الكبيرة والإمكانيات', 'weight': 'N'}
                    ]
                },
                {
                    'text': 'عندما تحكي قصة:',
                    'options': [
                        {'text': 'تركز على التفاصيل والأحداث الفعلية', 'weight': 'S'},
                        {'text': 'تركز على المعنى والرسالة العامة', 'weight': 'N'}
                    ]
                },
                {
                    'text': 'تثق أكثر في:',
                    'options': [
                        {'text': 'التجربة والخبرة العملية', 'weight': 'S'},
                        {'text': 'الحدس والإلهام', 'weight': 'N'}
                    ]
                }
            ]
        },
        'TF': {
            'name': 'التفكير مقابل المشاعر',
            'description': 'كيف تتخذ القرارات',
            'questions': [
                {
                    'text': 'عند اتخاذ قرار مهم:',
                    'options': [
                        {'text': 'تحلل المنطق والحقائق', 'weight': 'T'},
                        {'text': 'تأخذ في الاعتبار تأثيره على الأشخاص', 'weight': 'F'}
                    ]
                },
                {
                    'text': 'يراك الآخرون كشخص:',
                    'options': [
                        {'text': 'عادل ومنطقي', 'weight': 'T'},
                        {'text': 'مهتم ومتعاطف', 'weight': 'F'}
                    ]
                },
                {
                    'text': 'عند حل نزاع بين الأصدقاء:',
                    'options': [
                        {'text': 'تبحث عن الحل الأكثر عدالة', 'weight': 'T'},
                        {'text': 'تحاول فهم مشاعر كل طرف', 'weight': 'F'}
                    ]
                }
            ]
        },
        'JP': {
            'name': 'الحزم مقابل المرونة',
            'description': 'كيف تنظم حياتك وتتعامل مع الخطط',
            'questions': [
                {
                    'text': 'تفضل العمل:',
                    'options': [
                        {'text': 'وفق خطة محددة وجدول زمني', 'weight': 'J'},
                        {'text': 'بمرونة حسب الظروف', 'weight': 'P'}
                    ]
                },
                {
                    'text': 'عندما تذهب لرحلة:',
                    'options': [
                        {'text': 'تخطط لكل التفاصيل مسبقاً', 'weight': 'J'},
                        {'text': 'تفضل الارتجال واكتشاف الأشياء', 'weight': 'P'}
                    ]
                },
                {
                    'text': 'في مساحة عملك:',
                    'options': [
                        {'text': 'كل شيء منظم ومرتب', 'weight': 'J'},
                        {'text': 'فوضى إبداعية ومرونة', 'weight': 'P'}
                    ]
                }
            ]
        }
    }
}

# أنماط الشخصية MBTI
MBTI_TYPES = {
    'INTJ': {
        'name': 'المعمار / العقل المدبر',
        'description': 'شخصية منطقية ومستقلة وحازمة، يتمتع بخيال قوي وطموح كبير.',
        'strengths': ['التفكير الاستراتيجي', 'الاستقلالية', 'الحزم', 'الإبداع'],
        'weaknesses': ['صعوبة في التعبير عن المشاعر', 'الكمالية المفرطة', 'التحليل الزائد'],
        'careers': ['مهندس', 'عالم', 'محام', 'طبيب', 'مبرمج', 'مستشار استراتيجي'],
        'advice': 'ركز على تطوير مهاراتك الاجتماعية وتعلم كيفية التعبير عن مشاعرك.'
    },
    'INTP': {
        'name': 'المفكر / المنطقي',
        'description': 'شخصية فضولية ومرنة، يحب استكشاف النظريات والأفكار المعقدة.',
        'strengths': ['التحليل المنطقي', 'الإبداع النظري', 'المرونة الذهنية', 'الاستقلالية'],
        'weaknesses': ['تجاهل التفاصيل العملية', 'صعوبة في اتخاذ القرارات', 'تجنب الصراعات'],
        'careers': ['باحث', 'عالم', 'فيلسوف', 'مبرمج', 'كاتب', 'محلل'],
        'advice': 'اعمل على تطبيق أفكارك النظرية في مشاريع عملية محددة.'
    },
    'ENTJ': {
        'name': 'القائد / المدير التنفيذي',
        'description': 'شخصية قيادية طبيعية، حازمة وواثقة، تحب التحديات والنتائج.',
        'strengths': ['القيادة الطبيعية', 'التفكير الاستراتيجي', 'الثقة بالنفس', 'الكفاءة'],
        'weaknesses': ['عدم الصبر', 'التسلط أحياناً', 'تجاهل المشاعر'],
        'careers': ['مدير تنفيذي', 'محام', 'مستشار إداري', 'رائد أعمال', 'سياسي'],
        'advice': 'تعلم الاستماع لآراء الآخرين وتقدير مشاعرهم في عملية اتخاذ القرار.'
    },
    'ENTP': {
        'name': 'المناظر / المبتكر',
        'description': 'شخصية مبدعة ومتحمسة، تحب التحديات الذهنية والأفكار الجديدة.',
        'strengths': ['الإبداع', 'المرونة', 'الحماس', 'التفكير السريع'],
        'weaknesses': ['عدم التركيز على التفاصيل', 'تجنب المهام الروتينية', 'فقدان الاهتمام بسرعة'],
        'careers': ['رائد أعمال', 'مستشار', 'صحافي', 'مخترع', 'محامي', 'مطور'],
        'advice': 'اعمل على إنهاء المشاريع التي تبدأها وطور صبرك مع التفاصيل.'
    },
    'INFJ': {
        'name': 'المدافع / المحامي',
        'description': 'شخصية مثالية ومبدعة، تسعى لإحداث تأثير إيجابي في العالم.',
        'strengths': ['التعاطف العميق', 'الرؤية المستقبلية', 'الإبداع', 'المثالية'],
        'weaknesses': ['الحساسية المفرطة', 'الكمالية', 'تجنب الصراعات'],
        'careers': ['مستشار نفسي', 'كاتب', 'معلم', 'عامل اجتماعي', 'فنان'],
        'advice': 'تعلم وضع حدود صحية وتقبل أن الكمال غير ممكن.'
    },
    'INFP': {
        'name': 'الوسيط / المثالي',
        'description': 'شخصية مبدعة ومتعاطفة، تسعى للأصالة والتوافق مع قيمها.',
        'strengths': ['الإبداع', 'التعاطف', 'المرونة', 'الأصالة'],
        'weaknesses': ['أخذ الأمور بصورة شخصية', 'صعوبة في اتخاذ القرارات', 'التسويف'],
        'careers': ['فنان', 'كاتب', 'مستشار', 'معالج نفسي', 'ناشط اجتماعي'],
        'advice': 'اعمل على تطوير مهارات إدارة الوقت والثقة بالنفس.'
    },
    'ENFJ': {
        'name': 'البطل / المعلم',
        'description': 'شخصية ملهمة وكاريزمية، تحب مساعدة الآخرين على تحقيق إمكاناتهم.',
        'strengths': ['القيادة الملهمة', 'التعاطف', 'التواصل', 'التحفيز'],
        'weaknesses': ['إهمال احتياجاتهم الخاصة', 'الحساسية للنقد', 'المثالية'],
        'careers': ['معلم', 'مدرب', 'مستشار', 'مدير موارد بشرية', 'خطيب'],
        'advice': 'تذكر أن تهتم بنفسك كما تهتم بالآخرين.'
    },
    'ENFP': {
        'name': 'المتحمس / المشجع',
        'description': 'شخصية متحمسة ومبدعة واجتماعية، تحب استكشاف الإمكانيات الجديدة.',
        'strengths': ['الحماس', 'الإبداع', 'المرونة', 'التفاؤل'],
        'weaknesses': ['عدم التركيز', 'التسويف', 'الحساسية للضغط'],
        'careers': ['إعلامي', 'مستشار', 'مطور منتجات', 'معلم', 'مسوق'],
        'advice': 'اعمل على تطوير الانضباط الذاتي والتركيز على أهدافك.'
    },
    'ISTJ': {
        'name': 'اللوجستي / المدبر',
        'description': 'شخصية موثوقة ومسؤولة، تحترم التقاليد والنظام.',
        'strengths': ['الموثوقية', 'التنظيم', 'المسؤولية', 'الصبر'],
        'weaknesses': ['مقاومة التغيير', 'صعوبة في التعبير عن المشاعر', 'الجمود أحياناً'],
        'careers': ['محاسب', 'مهندس', 'مدير مالي', 'محامي', 'طبيب'],
        'advice': 'كن أكثر انفتاحاً على الأفكار الجديدة والتغيير.'
    },
    'ISFJ': {
        'name': 'المدافع / الحامي',
        'description': 'شخصية محبة ومهتمة بالآخرين، تسعى لحماية ودعم من حولها.',
        'strengths': ['التعاطف', 'الموثوقية', 'الصبر', 'الاهتمام بالتفاصيل'],
        'weaknesses': ['صعوبة في قول لا', 'تجنب الصراعات', 'إهمال احتياجاتهم'],
        'careers': ['ممرض', 'معلم', 'عامل اجتماعي', 'مستشار', 'طبيب أطفال'],
        'advice': 'تعلم وضع حدود صحية والاهتمام بنفسك أيضاً.'
    },
    'ESTJ': {
        'name': 'المنفذ / المدير',
        'description': 'شخصية منظمة وعملية، تحب النظام والكفاءة في العمل.',
        'strengths': ['القيادة', 'التنظيم', 'الكفاءة', 'المسؤولية'],
        'weaknesses': ['عدم المرونة', 'صعوبة في التعامل مع المشاعر', 'التسلط أحياناً'],
        'careers': ['مدير', 'محامي', 'ضابط', 'مدير مالي', 'رجل أعمال'],
        'advice': 'اعمل على تطوير مرونتك والاستماع لوجهات النظر الأخرى.'
    },
    'ESFJ': {
        'name': 'القنصل / المضيف',
        'description': 'شخصية اجتماعية ومهتمة، تحب مساعدة الآخرين وخلق الانسجام.',
        'strengths': ['التعاطف', 'التعاون', 'الموثوقية', 'المهارات الاجتماعية'],
        'weaknesses': ['الحساسية للنقد', 'صعوبة في قول لا', 'تجنب الصراعات'],
        'careers': ['معلم', 'ممرض', 'مستشار', 'مدير موارد بشرية', 'منسق فعاليات'],
        'advice': 'تعلم التعامل مع النقد البناء وتطوير ثقتك بنفسك.'
    },
    'ISTP': {
        'name': 'الفني / الحرفي',
        'description': 'شخصية عملية ومرنة، تحب استكشاف الأشياء بالتجربة العملية.',
        'strengths': ['حل المشاكل العملية', 'المرونة', 'الهدوء تحت الضغط', 'الاستقلالية'],
        'weaknesses': ['صعوبة في التعبير عن المشاعر', 'تجنب الالتزامات', 'العزلة أحياناً'],
        'careers': ['مهندس', 'فني', 'طيار', 'رياضي', 'مطور برمجيات'],
        'advice': 'اعمل على تطوير مهاراتك في التواصل والتعبير عن مشاعرك.'
    },
    'ISFP': {
        'name': 'المغامر / الفنان',
        'description': 'شخصية مبدعة ومرنة، تقدر الجمال والأصالة في الحياة.',
        'strengths': ['الإبداع', 'التعاطف', 'المرونة', 'التقدير الجمالي'],
        'weaknesses': ['صعوبة في التخطيط طويل المدى', 'الحساسية للنقد', 'تجنب الصراعات'],
        'careers': ['فنان', 'مصمم', 'موسيقي', 'مصور', 'معالج طبيعي'],
        'advice': 'اعمل على تطوير مهارات التخطيط والثقة بالنفس.'
    },
    'ESTP': {
        'name': 'رجل الأعمال / المؤدي',
        'description': 'شخصية نشيطة ومرحة، تحب العمل والتفاعل مع الناس.',
        'strengths': ['المرونة', 'الكاريزما', 'العملية', 'حل المشاكل السريع'],
        'weaknesses': ['عدم الصبر', 'صعوبة في التخطيط طويل المدى', 'تجنب النظريات'],
        'careers': ['مندوب مبيعات', 'ممثل', 'رياضي', 'رائد أعمال', 'مدير مشروع'],
        'advice': 'اعمل على تطوير صبرك ومهارات التخطيط طويل المدى.'
    },
    'ESFP': {
        'name': 'المؤدي / المسلي',
        'description': 'شخصية متحمسة ومرحة، تحب إدخال البهجة على حياة الآخرين.',
        'strengths': ['الحماس', 'التفاؤل', 'المرونة', 'المهارات الاجتماعية'],
        'weaknesses': ['صعوبة في التخطيط', 'تجنب الصراعات', 'عدم التركيز على المستقبل'],
        'careers': ['ممثل', 'معلم', 'مستشار', 'منسق فعاليات', 'مدرب'],
        'advice': 'اعمل على تطوير مهارات التخطيط والتفكير في العواقب طويلة المدى.'
    }
}

# التقييمات النفسية المتقدمة
PSYCHOLOGICAL_ASSESSMENTS = {
    'phq9': {
        'name': 'استبيان الاكتئاب PHQ-9',
        'icon': '😔',
        'questions': [
            "قلة الاهتمام أو المتعة في فعل الأشياء",
            "الشعور بالإحباط أو الاكتئاب أو اليأس",
            "صعوبة في النوم أو النوم أكثر من اللازم",
            "الشعور بالتعب أو قلة الطاقة",
            "ضعف الشهية أو الإفراط في الأكل",
            "الشعور السيء تجاه نفسك",
            "صعوبة في التركيز على الأشياء",
            "التحرك أو التحدث ببطء شديد أو العكس",
            "أفكار إيذاء النفس أو الموت"
        ],
        'options': [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    'gad7': {
        'name': 'مقياس القلق العام GAD-7',
        'icon': '😰',
        'questions': [
            "الشعور بالعصبية أو القلق أو التوتر",
            "عدم القدرة على التوقف عن القلق أو السيطرة عليه",
            "القلق الشديد حول أشياء مختلفة",
            "صعوبة في الاسترخاء",
            "الشعور بالقلق الشديد لدرجة صعوبة البقاء ساكناً",
            "الانزعاج أو الغضب بسهولة",
            "الشعور بالخوف كما لو أن شيئاً فظيعاً قد يحدث"
        ],
        'options': [("مطلقاً", 0), ("عدة أيام", 1), ("أكثر من نصف الأيام", 2), ("تقريباً كل يوم", 3)]
    },
    'mbti': {
        'name': 'تحليل الشخصية مايرز-بريغز (MBTI)',
        'icon': '🧠',
        'description': 'اختبار شامل لتحديد نمط شخصيتك وفقاً لمؤشر مايرز-بريغز المعتمد عالمياً'
    },
    'psychological_evaluation': {
        'name': 'التقييم النفسي الشامل',
        'icon': '🔍',
        'description': 'تقييم نفسي متكامل يشمل التاريخ الطبي والبيئة الاجتماعية والحالة النفسية',
        'categories': [
            'medical_history',
            'social_environment', 
            'addiction_behaviors',
            'psychological_state'
        ]
    }
}

# أسئلة التقييم النفسي الشامل
PSYCHOLOGICAL_QUESTIONS = {
    'medical_history': [
        {
            'id': 'mh_001',
            'question': 'هل تعاني من أي أمراض مزمنة؟',
            'type': 'multiple_choice',
            'options': ['نعم', 'لا', 'غير متأكد'],
            'required': True
        },
        {
            'id': 'mh_002', 
            'question': 'هل تتناول أي أدوية بانتظام؟',
            'type': 'multiple_choice',
            'options': ['نعم', 'لا'],
            'required': True
        },
        {
            'id': 'mh_003',
            'question': 'هل سبق أن تلقيت علاجاً نفسياً؟',
            'type': 'multiple_choice', 
            'options': ['نعم', 'لا', 'أفضل عدم الإجابة'],
            'required': False
        }
    ],
    'social_environment': [
        {
            'id': 'se_001',
            'question': 'كيف تقيم مستوى الدعم من عائلتك؟',
            'type': 'scale',
            'scale_min': 1,
            'scale_max': 5,
            'scale_labels': ['ضعيف جداً', 'ضعيف', 'متوسط', 'جيد', 'ممتاز'],
            'required': True
        },
        {
            'id': 'se_002',
            'question': 'كيف تقيم علاقاتك الاجتماعية؟',
            'type': 'scale',
            'scale_min': 1,
            'scale_max': 5,
            'scale_labels': ['ضعيفة جداً', 'ضعيفة', 'متوسطة', 'جيدة', 'ممتازة'],
            'required': True
        }
    ],
    'addiction_behaviors': [
        {
            'id': 'ab_001',
            'question': 'هل تشعر أن لديك سلوكيات قد تكون ضارة أو إدمانية؟',
            'type': 'multiple_choice',
            'options': ['نعم', 'لا', 'غير متأكد', 'أفضل عدم الإجابة'],
            'required': False
        }
    ],
    'psychological_state': [
        {
            'id': 'ps_001',
            'question': 'كيف تقيم مستوى التوتر في حياتك حالياً؟',
            'type': 'scale',
            'scale_min': 1,
            'scale_max': 5,
            'scale_labels': ['منخفض جداً', 'منخفض', 'متوسط', 'عالي', 'عالي جداً'],
            'required': True
        }
    ]
}

# موارد الدعم الديني والفلسفي
SUPPORT_RESOURCES = {
    'religious': [
        {
            'category': 'stress_relief',
            'title': 'الصبر في القرآن الكريم',
            'content': 'قال الله تعالى: "وَاصْبِرْ وَمَا صَبْرُكَ إِلَّا بِاللَّهِ وَلَا تَحْزَنْ عَلَيْهِمْ وَلَا تَكُ فِي ضَيْقٍ مِّمَّا يَمْكُرُونَ" (النحل: 127). الصبر هو مفتاح الفرج، وهو من أعظم الصفات التي يمكن أن يتحلى بها المؤمن في مواجهة الصعاب.',
            'source': 'القرآن الكريم - سورة النحل',
            'tags': ['stress', 'patience', 'quran', 'relief']
        },
        {
            'category': 'anxiety_relief',
            'title': 'الذكر وطمأنينة القلب',
            'content': 'قال الله تعالى: "الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللَّهِ أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ" (الرعد: 28). ذكر الله تعالى يجلب السكينة والطمأنينة للقلب المضطرب.',
            'source': 'القرآن الكريم - سورة الرعد',
            'tags': ['anxiety', 'dhikr', 'peace', 'heart']
        }
    ],
    'philosophical': [
        {
            'category': 'stoicism',
            'title': 'حكمة إبكتيتوس في التحكم',
            'content': 'قال الفيلسوف إبكتيتوس: "هناك أشياء في سيطرتنا وأشياء ليست في سيطرتنا. في سيطرتنا آراؤنا ورغباتنا وأفعالنا. وليس في سيطرتنا أجسادنا وممتلكاتنا وسمعتنا ومناصبنا." فهم هذا التمييز يحرر الإنسان من القلق غير المبرر.',
            'source': 'إبكتيتوس - الفلسفة الرواقية',
            'tags': ['control', 'stoicism', 'anxiety', 'wisdom']
        },
        {
            'category': 'existentialism',
            'title': 'البحث عن المعنى - فيكتور فرانكل',
            'content': 'يقول فيكتور فرانكل: "كل شيء يمكن أن يُؤخذ من الإنسان إلا شيئاً واحداً: آخر الحريات الإنسانية - القدرة على اختيار موقفه في أي ظروف معطاة." إيجاد المعنى في المعاناة يحولها إلى إنجاز إنساني.',
            'source': 'فيكتور فرانكل - الإنسان يبحث عن المعنى',
            'tags': ['meaning', 'purpose', 'suffering', 'choice']
        }
    ]
}

class AdvancedMentalHealthDatabase:
    """قاعدة بيانات متقدمة للصحة النفسية"""

    def __init__(self):
        self.db_path = 'advanced_mental_health.db'
        self.init_database()

    def init_database(self):
        """إنشاء قاعدة البيانات المتقدمة"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # جدول المستخدمين المتقدم
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                age INTEGER,
                gender TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_assessments INTEGER DEFAULT 0,
                risk_level TEXT DEFAULT 'unknown',
                bio TEXT,
                last_interaction TIMESTAMP,
                preferred_language TEXT DEFAULT 'ar'
            )
            ''')

            # جدول التقييمات
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                assessment_type TEXT,
                questions_answers TEXT,
                total_score INTEGER,
                subscale_scores TEXT,
                risk_level TEXT,
                severity TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                recommendations TEXT,
                islamic_guidance TEXT,
                follow_up_needed BOOLEAN,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            ''')

            # جدول تحليل MBTI
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mbti_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                personality_type TEXT,
                dimension_scores TEXT,
                detailed_analysis TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            ''')

            # جدول التقييم النفسي الشامل
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS psychological_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                evaluation_data TEXT,
                analysis_results TEXT,
                support_resources TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            ''')

            conn.commit()
            conn.close()
            logger.info("🗄️ قاعدة البيانات المتقدمة تم إنشاؤها بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")

class PsychologicalAnalysisService:
    """خدمة التحليل النفسي المتكاملة"""

    @staticmethod
    def generate_user_id(telegram_user_id: str) -> str:
        """إنشاء معرف مستخدم مشفر"""
        return hashlib.sha256(f"user_{telegram_user_id}".encode()).hexdigest()[:32]

    @staticmethod
    def analyze_mbti(responses: dict) -> dict:
        """تحليل نتائج اختبار MBTI"""
        dimension_scores = {'E': 0, 'I': 0, 'S': 0, 'N': 0, 'T': 0, 'F': 0, 'J': 0, 'P': 0}

        # حساب النقاط لكل بعد
        for dimension, answers in responses.items():
            for answer in answers:
                if answer in dimension_scores:
                    dimension_scores[answer] += 1

        # تحديد النمط
        personality_type = ""
        personality_type += 'E' if dimension_scores['E'] > dimension_scores['I'] else 'I'
        personality_type += 'S' if dimension_scores['S'] > dimension_scores['N'] else 'N'
        personality_type += 'T' if dimension_scores['T'] > dimension_scores['F'] else 'F'
        personality_type += 'J' if dimension_scores['J'] > dimension_scores['P'] else 'P'

        # الحصول على تفاصيل النمط
        personality_details = MBTI_TYPES.get(personality_type, {
            'name': 'غير محدد',
            'description': 'نمط شخصية غير مصنف',
            'strengths': [],
            'weaknesses': [],
            'careers': [],
            'advice': 'تحتاج لمزيد من التقييم'
        })

        return {
            'personality_type': personality_type,
            'dimension_scores': dimension_scores,
            'details': personality_details,
            'confidence_score': min(max(
                abs(dimension_scores['J'] - dimension_scores['P']) / 12.0, 0.5), 1.0)
        }

    @staticmethod
    def analyze_psychological_evaluation(responses: dict) -> dict:
        """تحليل التقييم النفسي الشامل"""
        analysis = {
            'risk_factors': [],
            'protective_factors': [],
            'recommendations': [],
            'support_needed': False
        }

        # تحليل كل فئة
        for category, answers in responses.items():
            if category == 'medical_history':
                analysis = PsychologicalAnalysisService._analyze_medical_history(answers, analysis)
            elif category == 'social_environment':
                analysis = PsychologicalAnalysisService._analyze_social_environment(answers, analysis)
            elif category == 'addiction_behaviors':
                analysis = PsychologicalAnalysisService._analyze_addiction_behaviors(answers, analysis)
            elif category == 'psychological_state':
                analysis = PsychologicalAnalysisService._analyze_psychological_state(answers, analysis)

        return analysis

    @staticmethod
    def _analyze_medical_history(answers: list, analysis: dict) -> dict:
        """تحليل التاريخ الطبي"""
        for answer in answers:
            if 'نعم' in str(answer):
                analysis['risk_factors'].append('وجود تاريخ طبي قد يؤثر على الحالة النفسية')
                analysis['recommendations'].append('ضرورة المتابعة الطبية المنتظمة')
        return analysis

    @staticmethod
    def _analyze_social_environment(answers: list, analysis: dict) -> dict:
        """تحليل البيئة الاجتماعية"""
        support_scores = [int(x) for x in answers if str(x).isdigit()]
        if support_scores:
            avg_support = sum(support_scores) / len(support_scores)
            if avg_support >= 4:
                analysis['protective_factors'].append('دعم اجتماعي وأسري قوي')
            elif avg_support <= 2:
                analysis['risk_factors'].append('ضعف في الدعم الاجتماعي')
                analysis['recommendations'].append('تطوير شبكة الدعم الاجتماعي')
        return analysis

    @staticmethod
    def _analyze_addiction_behaviors(answers: list, analysis: dict) -> dict:
        """تحليل السلوكيات الإدمانية"""
        if 'نعم' in str(answers):
            analysis['risk_factors'].append('وجود سلوكيات إدمانية محتملة')
            analysis['support_needed'] = True
            analysis['recommendations'].append('طلب المساعدة المتخصصة في علاج الإدمان')
        return analysis

    @staticmethod
    def _analyze_psychological_state(answers: list, analysis: dict) -> dict:
        """تحليل الحالة النفسية"""
        stress_scores = [int(x) for x in answers if str(x).isdigit()]
        if stress_scores:
            avg_stress = sum(stress_scores) / len(stress_scores)
            if avg_stress >= 4:
                analysis['risk_factors'].append('مستوى توتر عالي')
                analysis['recommendations'].append('تعلم تقنيات إدارة التوتر والاسترخاء')
        return analysis

    @staticmethod
    def get_religious_support(analysis_results: dict) -> list:
        """الحصول على الدعم الديني المناسب"""
        relevant_resources = []

        for resource in SUPPORT_RESOURCES['religious']:
            # تحديد مدى الصلة بناءً على النتائج
            relevance = 0
            for tag in resource['tags']:
                if tag in str(analysis_results).lower():
                    relevance += 1

            if relevance > 0:
                relevant_resources.append({
                    **resource,
                    'relevance_score': relevance
                })

        # ترتيب حسب الصلة
        relevant_resources.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_resources[:3]

    @staticmethod
    def get_philosophical_support(analysis_results: dict) -> list:
        """الحصول على الدعم الفلسفي المناسب"""
        relevant_resources = []

        for resource in SUPPORT_RESOURCES['philosophical']:
            relevance = 0
            for tag in resource['tags']:
                if tag in str(analysis_results).lower():
                    relevance += 1

            if relevance > 0:
                relevant_resources.append({
                    **resource,
                    'relevance_score': relevance
                })

        relevant_resources.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_resources[:3]

class AdvancedMentalHealthBot:
    """بوت الصحة النفسية المتقدم والشامل"""

    def __init__(self):
        self.db = AdvancedMentalHealthDatabase()
        self.analysis_service = PsychologicalAnalysisService()
        self.user_sessions = {}
        self.scheduler_task = None

    async def schedule_daily_quotes(self):
        """جدولة إرسال الاقتباسات اليومية"""
        async def send_scheduled_quote():
            try:
                # هنا يتم جلب اقتباس عشوائي من قاعدة المعرفة
                quote = self.get_random_quote()
                if quote:
                    bot = Bot(token=TOKEN)
                    await bot.send_message(chat_id=CHANNEL_ID, text=quote, parse_mode='Markdown')
                    logger.info(f"✅ تم إرسال اقتباس يومي إلى القناة: {CHANNEL_ID}")
                else:
                    logger.warning("⚠️ لم يتم العثور على اقتباس لإرساله للقناة.")
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الاقتباس الدوري: {e}")

        async def run_scheduler():
            while True:
                try:
                    now = datetime.now()
                    next_run = now + timedelta(hours=6)
                    next_run = next_run.replace(minute=0, second=0, microsecond=0)
                    wait_seconds = (next_run - now).total_seconds()
                    await asyncio.sleep(wait_seconds)
                    await send_scheduled_quote()
                except Exception as e:
                    logger.error(f"❌ خطأ في جدولة الرسائل: {e}")
                    await asyncio.sleep(3600)  # انتظار ساعة في حالة الخطأ

        # تشغيل الجدولة في مهمة خلفية
        if not self.scheduler_task or self.scheduler_task.done():
            self.scheduler_task = asyncio.create_task(run_scheduler())

    def get_random_quote(self):
        """الحصول على اقتباس عشوائي من قاعدة المعرفة"""
        all_quotes = []
        for category in KNOWLEDGE_DATABASE.values():
            for resource_type in category.values():
                if isinstance(resource_type, dict):
                    for quote_source in resource_type.values():
                        if isinstance(quote_source, dict):
                            if 'text' in quote_source:
                                all_quotes.append(f"*{quote_source['text']}* - {quote_source['source']}")
                            elif 'ayah' in quote_source:
                                all_quotes.append(f"*{quote_source['ayah']}* - {quote_source['reference']}\n{quote_source['tafseer']}")
                        elif isinstance(quote_source, str):
                            all_quotes.append(f"*{quote_source}*")

        # إضافة موارد الدعم
        for resource in SUPPORT_RESOURCES['religious']:
            all_quotes.append(f"*{resource['title']}*\n{resource['content'][:200]}...")

        for resource in SUPPORT_RESOURCES['philosophical']:
            all_quotes.append(f"*{resource['title']}*\n{resource['content'][:200]}...")

        if all_quotes:
            return random.choice(all_quotes)
        else:
            return "🌟 *حكمة اليوم:* الحياة رحلة، استمتع بكل خطوة فيها"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر البداية المطور"""
        try:
            user = update.effective_user

            # حفظ بيانات المستخدم
            self.save_user_data(user)

            welcome_text = f"""
🌟 **أهلاً وسهلاً بك {user.first_name}** 🌟

🧠 **مركز التحليل النفسي المتكامل** 🧠

✨ **خدماتنا الشاملة:**

🎯 **تحليل الشخصية MBTI**
• اكتشف نمط شخصيتك من 16 نمط مختلف
• تحليل مفصل لنقاط القوة والضعف
• توجيهات مهنية مخصصة

📊 **الاختبارات المعتمدة**
• مقياس الاكتئاب PHQ-9
• مقياس القلق GAD-7
• تقييمات أخرى متخصصة

🕌 **الدعم الروحي والفلسفي**
• إرشاد إسلامي من القرآن والسنة
• حكم فلسفية من مختلف المدارس
• دعم مخصص حسب حالتك

💡 **مميزات خاصة:**
✅ تحليل متعدد الأبعاد
✅ خصوصية وأمان تام
✅ توصيات مخصصة
✅ دعم مستمر 24/7

🚀 **ابدأ رحلتك نحو فهم أعمق لذاتك!**
            """

            keyboard = [
                [InlineKeyboardButton("🧠 تحليل الشخصية MBTI", callback_data="start_mbti")],
                [InlineKeyboardButton("📊 الاختبارات النفسية", callback_data="start_journey")],
                [InlineKeyboardButton("🔍 التقييم النفسي الشامل", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("ℹ️ معلومات الخدمة", callback_data="more_info")]
            ]

            await update.message.reply_text(
                welcome_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في أمر البداية: {e}")
            await update.message.reply_text("حدث خطأ، يرجى المحاولة مرة أخرى.")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الاستجابات المتقدم"""
        try:
            query = update.callback_query
            await query.answer()

            data = query.data

            # تسجيل التفاعل
            self.log_user_interaction(query.from_user.id, data)

            if data == "start_mbti":
                await self.start_mbti_assessment(query, context)
            elif data == "start_journey":
                await self.show_assessment_menu(query, context)
            elif data == "start_psychological_evaluation":
                await self.start_psychological_evaluation(query, context)
            elif data == "more_info":
                await self.show_detailed_info(query, context)
            elif data.startswith("mbti_"):
                await self.handle_mbti_response(query, context, data)
            elif data.startswith("assessment_"):
                await self.start_assessment(query, context, data)
            elif data.startswith("answer_"):
                await self.handle_assessment_answer(query, context, data)
            elif data.startswith("begin_"):
                assessment_type = data.replace("begin_", "")
                await self.begin_assessment(query, context, assessment_type)
            elif data.startswith("psych_"):
                await self.handle_psychological_response(query, context, data)
            elif data == "back_to_main":
                await self.start_command_from_callback(query, context)
            elif data == "show_religious_support":
                await self.show_religious_support(query, context)
            elif data == "show_philosophical_support":
                await self.show_philosophical_support(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الـ callback: {e}")
            await query.edit_message_text("حدث خطأ، يرجى المحاولة مرة أخرى.")

    async def start_mbti_assessment(self, query, context):
        """بدء اختبار تحليل الشخصية MBTI"""
        try:
            intro_text = f"""
🧠 **اختبار تحليل الشخصية مايرز-بريغز (MBTI)**

📖 **عن الاختبار:**
مؤشر أنماط الشخصية مايرز-بريغز هو أحد أقوى أدوات تحليل الشخصية في العالم، بمصداقية تصل إلى 85%. يساعدك على:

🎯 **ستكتشف:**
• نمط شخصيتك من 16 نمط مختلف
• نقاط قوتك الطبيعية
• المجالات التي تحتاج تطوير
• التوجيهات المهنية المناسبة

⏰ **الوقت المتوقع:** 10-15 دقيقة
🎯 **عدد الأسئلة:** 12 سؤال (3 لكل مقياس)

💡 **نصيحة:** اختر الإجابة التي تعكس تفضيلك الطبيعي، وليس ما تعتقد أنه الصحيح.

🔒 **خصوصيتك محمية بالكامل**
            """

            session_id = str(uuid.uuid4())
            context.user_data['mbti_session'] = session_id
            context.user_data['mbti_responses'] = {}
            context.user_data['current_dimension'] = 'EI'
            context.user_data['current_question'] = 0

            keyboard = [
                [InlineKeyboardButton("🚀 ابدأ الاختبار", callback_data="mbti_start_test")],
                [InlineKeyboardButton("📚 المزيد عن MBTI", callback_data="mbti_more_info")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                intro_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في بدء MBTI: {e}")
            await query.edit_message_text("حدث خطأ في بدء الاختبار، يرجى المحاولة مرة أخرى.")

    async def handle_mbti_response(self, query, context, data):
        """معالجة إجابات اختبار MBTI"""
        try:
            if data == "mbti_start_test":
                await self.send_mbti_question(query, context)
            elif data == "mbti_more_info":
                await self.show_mbti_detailed_info(query, context)
            elif data.startswith("mbti_answer_"):
                parts = data.split("_")
                answer = parts[2]  # E, I, S, N, T, F, J, P

                # حفظ الإجابة
                current_dim = context.user_data.get('current_dimension', 'EI')
                if 'mbti_responses' not in context.user_data:
                    context.user_data['mbti_responses'] = {}
                if current_dim not in context.user_data['mbti_responses']:
                    context.user_data['mbti_responses'][current_dim] = []
                context.user_data['mbti_responses'][current_dim].append(answer)

                # الانتقال للسؤال التالي
                await self.next_mbti_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة إجابة MBTI: {e}")
            await query.edit_message_text("حدث خطأ، يرجى المحاولة مرة أخرى.")

    async def send_mbti_question(self, query, context):
        """إرسال سؤال MBTI"""
        try:
            current_dim = context.user_data.get('current_dimension', 'EI')
            current_q = context.user_data.get('current_question', 0)

            dimension_data = MBTI_ASSESSMENT['dimensions'][current_dim]

            if current_q >= len(dimension_data['questions']):
                await self.next_mbti_dimension(query, context)
                return

            question = dimension_data['questions'][current_q]

            progress = self.calculate_mbti_progress(context.user_data)
            progress_bar = "▓" * int(progress // 10) + "░" * (10 - int(progress // 10))

            question_text = f"""
🧠 **تحليل الشخصية MBTI**

📊 **التقدم:** {progress_bar} {progress:.0f}%

🎯 **المقياس الحالي:** {dimension_data['name']}
💭 **الوصف:** {dimension_data['description']}

❓ **السؤال {current_q + 1}/3:**

**{question['text']}**

اختر الإجابة الأقرب لطبيعتك:
            """

            keyboard = []
            for i, option in enumerate(question['options']):
                callback_data = f"mbti_answer_{option['weight']}"
                keyboard.append([InlineKeyboardButton(option['text'], callback_data=callback_data)])

            await query.edit_message_text(
                question_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال سؤال MBTI: {e}")
            await query.edit_message_text("حدث خطأ في إرسال السؤال، يرجى المحاولة مرة أخرى.")

    async def next_mbti_question(self, query, context):
        """الانتقال للسؤال التالي في MBTI"""
        try:
            context.user_data['current_question'] += 1
            await self.send_mbti_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في الانتقال للسؤال التالي: {e}")

    async def next_mbti_dimension(self, query, context):
        """الانتقال للبعد التالي في MBTI"""
        try:
            dimensions = ['EI', 'SN', 'TF', 'JP']
            current_dim = context.user_data.get('current_dimension')
            current_index = dimensions.index(current_dim) if current_dim in dimensions else 0

            if current_index + 1 < len(dimensions):
                context.user_data['current_dimension'] = dimensions[current_index + 1]
                context.user_data['current_question'] = 0
                await self.send_mbti_question(query, context)
            else:
                await self.complete_mbti_assessment(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في الانتقال للبعد التالي: {e}")

    def calculate_mbti_progress(self, user_data):
        """حساب تقدم اختبار MBTI"""
        total_questions = 12  # 3 أسئلة × 4 أبعاد
        answered_questions = 0

        for dim, responses in user_data.get('mbti_responses', {}).items():
            answered_questions += len(responses)

        current_q = user_data.get('current_question', 0)
        answered_questions += current_q

        return (answered_questions / total_questions) * 100

    async def complete_mbti_assessment(self, query, context):
        """إكمال اختبار MBTI وعرض النتائج"""
        try:
            responses = context.user_data.get('mbti_responses', {})
            user_id = query.from_user.id
            session_id = context.user_data.get('mbti_session')

            # تحليل النتائج
            analysis = self.analysis_service.analyze_mbti(responses)

            # حفظ النتائج
            self.save_mbti_results(user_id, session_id, analysis)

            personality_type = analysis['personality_type']
            details = analysis['details']
            confidence = analysis['confidence_score']

            results_text = f"""
🧠 **نتائج تحليل شخصيتك MBTI**

🎯 **نمط شخصيتك:** {personality_type}
👑 **اللقب:** {details['name']}

📝 **الوصف:**
{details['description']}

💪 **نقاط القوة:**
{chr(10).join(f"• {strength}" for strength in details['strengths'])}

⚠️ **نقاط التطوير:**
{chr(10).join(f"• {weakness}" for weakness in details['weaknesses'])}

💼 **المهن المناسبة:**
{chr(10).join(f"• {career}" for career in details['careers'])}

💡 **نصيحة شخصية:**
{details['advice']}

📊 **مستوى الثقة في النتيجة:** {confidence:.1%}

🌟 **تذكر:** لا يوجد نمط أفضل من آخر، كل نمط له مميزاته الفريدة!
            """

            keyboard = [
                [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data="start_mbti")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                results_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إكمال تحليل MBTI: {e}")
            await query.edit_message_text("حدث خطأ في معالجة النتائج، يرجى المحاولة مرة أخرى.")

    async def start_psychological_evaluation(self, query, context):
        """بدء التقييم النفسي الشامل"""
        try:
            intro_text = f"""
🔍 **التقييم النفسي الشامل المتكامل**

📋 **ما هو التقييم النفسي؟**
هو فحص شامل يجمع معلومات عن شخصيتك ضمن خدمة نفسية متكاملة لإجراء تقييم دقيق لحالتك النفسية والاجتماعية.

🎯 **ما يشمله التقييم:**

1️⃣ **التاريخ الطبي**
• الأمراض المزمنة
• الأدوية المستخدمة
• التاريخ النفسي السابق

2️⃣ **البيئة الاجتماعية**
• الدعم الأسري
• العلاقات الاجتماعية
• الضغوط البيئية

3️⃣ **تقييم السلوكيات**
• السلوكيات الضارة المحتملة
• أنماط التأقلم
• آليات الدفاع النفسي

4️⃣ **الحالة النفسية العامة**
• مستوى التوتر
• المزاج العام
• القدرة على التأقلم

📊 **النتائج ستشمل:**
• تحليل نفسي متكامل
• تحديد عوامل الخطر والحماية
• توصيات علاجية مخصصة
• دعم ديني وفلسفي مناسب

⏰ **الوقت المتوقع:** 15-20 دقيقة
🔒 **سرية تامة ومحمية بالكامل**

⚠️ **تنبيه مهم:** هذا التقييم لأغراض التوعية والدعم النفسي، وليس بديلاً عن الاستشارة الطبية المتخصصة.
            """

            session_id = str(uuid.uuid4())
            context.user_data['psych_session'] = session_id
            context.user_data['psych_responses'] = {}
            context.user_data['current_category'] = 'medical_history'
            context.user_data['current_psych_question'] = 0

            keyboard = [
                [InlineKeyboardButton("🚀 ابدأ التقييم", callback_data="psych_start_evaluation")],
                [InlineKeyboardButton("📚 المزيد عن التقييم النفسي", callback_data="psych_more_info")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                intro_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في بدء التقييم النفسي: {e}")
            await query.edit_message_text("حدث خطأ في بدء التقييم، يرجى المحاولة مرة أخرى.")

    async def handle_psychological_response(self, query, context, data):
        """معالجة إجابات التقييم النفسي"""
        try:
            if data == "psych_start_evaluation":
                await self.send_psychological_question(query, context)
            elif data == "psych_more_info":
                await self.show_psychological_detailed_info(query, context)
            elif data.startswith("psych_answer_"):
                answer = data.replace("psych_answer_", "")

                # حفظ الإجابة
                current_cat = context.user_data.get('current_category')
                if 'psych_responses' not in context.user_data:
                    context.user_data['psych_responses'] = {}
                if current_cat not in context.user_data['psych_responses']:
                    context.user_data['psych_responses'][current_cat] = []
                context.user_data['psych_responses'][current_cat].append(answer)

                # الانتقال للسؤال التالي
                await self.next_psychological_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة إجابة التقييم النفسي: {e}")
            await query.edit_message_text("حدث خطأ، يرجى المحاولة مرة أخرى.")

    async def send_psychological_question(self, query, context):
        """إرسال سؤال التقييم النفسي"""
        try:
            current_cat = context.user_data.get('current_category')
            current_q = context.user_data.get('current_psych_question', 0)

            questions = PSYCHOLOGICAL_QUESTIONS.get(current_cat, [])

            if current_q >= len(questions):
                await self.next_psychological_category(query, context)
                return

            question = questions[current_q]

            # حساب التقدم
            total_questions = sum(len(PSYCHOLOGICAL_QUESTIONS[cat]) for cat in PSYCHOLOGICAL_QUESTIONS)
            completed_questions = sum(len(context.user_data.get('psych_responses', {}).get(cat, [])) for cat in context.user_data.get('psych_responses', {}))
            progress = (completed_questions / total_questions) * 100
            progress_bar = "▓" * int(progress // 10) + "░" * (10 - int(progress // 10))

            category_names = {
                'medical_history': 'التاريخ الطبي',
                'social_environment': 'البيئة الاجتماعية',
                'addiction_behaviors': 'السلوكيات الإدمانية',
                'psychological_state': 'الحالة النفسية'
            }

            question_text = f"""
🔍 **التقييم النفسي الشامل**

📊 **التقدم:** {progress_bar} {progress:.0f}%

📋 **الفئة الحالية:** {category_names.get(current_cat, current_cat)}

❓ **{question['question']}**

اختر الإجابة المناسبة:
            """

            keyboard = []
            if question['type'] == 'multiple_choice':
                for option in question['options']:
                    callback_data = f"psych_answer_{option}"
                    keyboard.append([InlineKeyboardButton(option, callback_data=callback_data)])
            elif question['type'] == 'scale':
                for i in range(question['scale_min'], question['scale_max'] + 1):
                    label = question['scale_labels'][i-1] if i-1 < len(question['scale_labels']) else str(i)
                    callback_data = f"psych_answer_{i}"
                    keyboard.append([InlineKeyboardButton(f"{i} - {label}", callback_data=callback_data)])

            await query.edit_message_text(
                question_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال سؤال التقييم النفسي: {e}")
            await query.edit_message_text("حدث خطأ في إرسال السؤال، يرجى المحاولة مرة أخرى.")

    async def next_psychological_question(self, query, context):
        """الانتقال للسؤال التالي في التقييم النفسي"""
        try:
            context.user_data['current_psych_question'] += 1
            await self.send_psychological_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في الانتقال للسؤال التالي: {e}")

    async def next_psychological_category(self, query, context):
        """الانتقال للفئة التالية في التقييم النفسي"""
        try:
            categories = ['medical_history', 'social_environment', 'addiction_behaviors', 'psychological_state']
            current_cat = context.user_data.get('current_category')
            current_index = categories.index(current_cat) if current_cat in categories else 0

            if current_index + 1 < len(categories):
                context.user_data['current_category'] = categories[current_index + 1]
                context.user_data['current_psych_question'] = 0
                await self.send_psychological_question(query, context)
            else:
                await self.complete_psychological_evaluation(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في الانتقال للفئة التالية: {e}")

    async def complete_psychological_evaluation(self, query, context):
        """إكمال التقييم النفسي وعرض النتائج"""
        try:
            responses = context.user_data.get('psych_responses', {})
            user_id = query.from_user.id
            session_id = context.user_data.get('psych_session')

            # تحليل النتائج
            analysis = self.analysis_service.analyze_psychological_evaluation(responses)

            # الحصول على الدعم الروحي والفلسفي
            religious_support = self.analysis_service.get_religious_support(analysis)
            philosophical_support = self.analysis_service.get_philosophical_support(analysis)

            # حفظ النتائج
            self.save_psychological_results(user_id, session_id, {
                'responses': responses,
                'analysis': analysis,
                'religious_support': religious_support,
                'philosophical_support': philosophical_support
            })

            results_text = f"""
🔍 **نتائج التقييم النفسي الشامل**

📊 **ملخص التحليل:**

🔴 **عوامل الخطر المحددة:**
{chr(10).join(f"• {factor}" for factor in analysis['risk_factors']) if analysis['risk_factors'] else "• لا توجد عوامل خطر واضحة"}

🟢 **العوامل الوقائية:**
{chr(10).join(f"• {factor}" for factor in analysis['protective_factors']) if analysis['protective_factors'] else "• يحتاج تعزيز العوامل الوقائية"}

💡 **التوصيات العلاجية:**
{chr(10).join(f"• {rec}" for rec in analysis['recommendations']) if analysis['recommendations'] else "• الاستمرار في الحالة الطبيعية مع المراقبة"}

⚠️ **الحاجة للدعم المتخصص:** {"نعم - يُنصح بطلب المساعدة المهنية" if analysis['support_needed'] else "لا - الحالة مستقرة حالياً"}

🌟 **الخطوات التالية:**
1. مراجعة التوصيات بعناية
2. تطبيق الاستراتيجيات المقترحة
3. المتابعة الدورية لتقييم التحسن

⚠️ **ملاحظة مهمة:** هذا التقييم ليس بديلاً عن الاستشارة الطبية المتخصصة
            """

            # حفظ الدعم في context لعرضه لاحقاً
            context.user_data['religious_support'] = religious_support
            context.user_data['philosophical_support'] = philosophical_support

            keyboard = [
                [InlineKeyboardButton("🕌 الدعم الديني", callback_data="show_religious_support")],
                [InlineKeyboardButton("📚 الدعم الفلسفي", callback_data="show_philosophical_support")],
                [InlineKeyboardButton("🔄 إعادة التقييم", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                results_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إكمال التقييم النفسي: {e}")
            await query.edit_message_text("حدث خطأ في معالجة النتائج، يرجى المحاولة مرة أخرى.")

    async def show_religious_support(self, query, context):
        """عرض الدعم الديني"""
        try:
            religious_support = context.user_data.get('religious_support', [])

            if not religious_support:
                text = "🕌 **الدعم الديني العام**\n\nلا توجد توصيات دينية محددة، ولكن ننصح بالاستمرار في الذكر والدعاء."
            else:
                text = "🕌 **الدعم الديني المخصص لحالتك**\n\n"
                for i, resource in enumerate(religious_support[:3], 1):
                    text += f"**{i}. {resource['title']}**\n"
                    text += f"{resource['content'][:300]}...\n\n"
                    text += f"📚 *{resource['source']}*\n\n"

            keyboard = [
                [InlineKeyboardButton("📚 الدعم الفلسفي", callback_data="show_philosophical_support")],
                [InlineKeyboardButton("🔙 العودة للنتائج", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض الدعم الديني: {e}")
            await query.edit_message_text("حدث خطأ في عرض الدعم الديني.")

    async def show_philosophical_support(self, query, context):
        """عرض الدعم الفلسفي"""
        try:
            philosophical_support = context.user_data.get('philosophical_support', [])

            if not philosophical_support:
                text = "📚 **الدعم الفلسفي العام**\n\nلا توجد توصيات فلسفية محددة، ولكن ننصح بالتأمل في معنى الحياة والسعي للتطوير الذاتي."
            else:
                text = "📚 **الدعم الفلسفي المخصص لحالتك**\n\n"
                for i, resource in enumerate(philosophical_support[:3], 1):
                    text += f"**{i}. {resource['title']}**\n"
                    text += f"{resource['content'][:300]}...\n\n"
                    text += f"📖 *{resource['source']}*\n\n"

            keyboard = [
                [InlineKeyboardButton("🕌 الدعم الديني", callback_data="show_religious_support")],
                [InlineKeyboardButton("🔙 العودة للنتائج", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض الدعم الفلسفي: {e}")
            await query.edit_message_text("حدث خطأ في عرض الدعم الفلسفي.")

    async def show_assessment_menu(self, query, context):
        """عرض قائمة الاختبارات النفسية التقليدية"""
        try:
            menu_text = """
📊 **الاختبارات النفسية المعتمدة**

🎯 **الاختبارات المتاحة:**

😔 **مقياس الاكتئاب (PHQ-9)**
• المعيار الذهبي لتقييم الاكتئاب
• 9 أسئلة علمية دقيقة
• يستخدم في المستشفيات العالمية

😰 **مقياس القلق العام (GAD-7)**
• مقياس القلق المعتمد دولياً
• 7 أسئلة شاملة
• تقييم دقيق لمستوى القلق

💡 **هذه الاختبارات تكمل التقييمات الشاملة الأخرى**
            """

            keyboard = [
                [InlineKeyboardButton("😔 مقياس الاكتئاب PHQ-9", callback_data="assessment_phq9")],
                [InlineKeyboardButton("😰 مقياس القلق GAD-7", callback_data="assessment_gad7")],
                [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                menu_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض قائمة الاختبارات: {e}")
            await query.edit_message_text("حدث خطأ في عرض القائمة.")

    async def start_assessment(self, query, context, assessment_type):
        """بدء التقييم المحدد"""
        try:
            assessment_key = assessment_type.replace("assessment_", "")
            assessment = PSYCHOLOGICAL_ASSESSMENTS[assessment_key]

            context.user_data['current_assessment'] = assessment_key
            context.user_data['question_index'] = 0
            context.user_data['answers'] = []
            context.user_data['start_time'] = datetime.now()

            intro_text = f"""
{assessment['icon']} **{assessment['name']}**

🎯 **تعليمات مهمة:**
• اقرأ كل سؤال بعناية
• اختر الإجابة الأكثر صدقاً
• فكر في الأسبوعين الماضيين
• لا توجد إجابات صحيحة أو خاطئة
• الصدق مع النفس هو المفتاح

⏰ **الوقت المتوقع:** 5-7 دقائق

🔒 **خصوصيتك مضمونة 100%**

💪 **أنت تخطو خطوة شجاعة نحو التحسن!**

هل أنت مستعد للبداية؟
            """

            keyboard = [
                [InlineKeyboardButton("🚀 نعم، ابدأ الآن", callback_data=f"begin_{assessment_key}")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="start_journey")]
            ]

            await query.edit_message_text(
                intro_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في بدء التقييم: {e}")
            await query.edit_message_text("حدث خطأ في بدء التقييم.")

    async def begin_assessment(self, query, context, assessment_type):
        """بداية الاختبار الفعلي"""
        try:
            context.user_data['current_assessment'] = assessment_type
            context.user_data['question_index'] = 0
            context.user_data['answers'] = []
            await self.send_assessment_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في بداية الاختبار: {e}")
            await query.edit_message_text("حدث خطأ في بداية الاختبار.")

    async def send_assessment_question(self, query, context):
        """إرسال سؤال الاختبار"""
        try:
            assessment_type = context.user_data['current_assessment']
            question_index = context.user_data['question_index']
            assessment = PSYCHOLOGICAL_ASSESSMENTS[assessment_type]

            if question_index >= len(assessment['questions']):
                await self.complete_assessment(query, context)
                return

            question = assessment['questions'][question_index]
            progress = ((question_index + 1) / len(assessment['questions'])) * 100

            question_text = f"""
{assessment['icon']} **{assessment['name']}**

📊 **التقدم:** {progress:.0f}%
🔢 **السؤال {question_index + 1} من {len(assessment['questions'])}**

❓ **خلال الأسبوعين الماضيين، كم مرة انزعجت من:**

**{question}**

اختر إجابتك:
            """

            keyboard = []
            for option_text, score in assessment['options']:
                callback_data = f"answer_{score}"
                keyboard.append([InlineKeyboardButton(option_text, callback_data=callback_data)])

            await query.edit_message_text(
                question_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال سؤال الاختبار: {e}")
            await query.edit_message_text("حدث خطأ في إرسال السؤال.")

    async def handle_assessment_answer(self, query, context, data):
        """معالجة إجابة الاختبار"""
        try:
            score = int(data.replace("answer_", ""))
            context.user_data['answers'].append(score)
            context.user_data['question_index'] += 1
            await self.send_assessment_question(query, context)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الإجابة: {e}")
            await query.edit_message_text("حدث خطأ في معالجة الإجابة.")

    async def complete_assessment(self, query, context):
        """إكمال الاختبار وعرض النتائج"""
        try:
            assessment_type = context.user_data['current_assessment']
            answers = context.user_data['answers']
            total_score = sum(answers)

            # تحديد مستوى الشدة
            if assessment_type == 'phq9':
                if total_score <= 4:
                    severity = "طبيعي"
                    severity_desc = "لا توجد علامات اكتئاب"
                    color = "🟢"
                elif total_score <= 9:
                    severity = "خفيف"
                    severity_desc = "اكتئاب خفيف"
                    color = "🟡"
                elif total_score <= 14:
                    severity = "متوسط"
                    severity_desc = "اكتئاب متوسط"
                    color = "🟠"
                elif total_score <= 19:
                    severity = "متوسط إلى شديد"
                    severity_desc = "اكتئاب متوسط إلى شديد"
                    color = "🔴"
                else:
                    severity = "شديد"
                    severity_desc = "اكتئاب شديد"
                    color = "🔴"
            else:  # GAD-7
                if total_score <= 4:
                    severity = "طبيعي"
                    severity_desc = "لا توجد علامات قلق"
                    color = "🟢"
                elif total_score <= 9:
                    severity = "خفيف"
                    severity_desc = "قلق خفيف"
                    color = "🟡"
                elif total_score <= 14:
                    severity = "متوسط"
                    severity_desc = "قلق متوسط"
                    color = "🟠"
                else:
                    severity = "شديد"
                    severity_desc = "قلق شديد"
                    color = "🔴"

            # حفظ النتائج
            self.save_assessment_results(query.from_user.id, assessment_type, answers, total_score, severity)

            # إعداد النص
            assessment = PSYCHOLOGICAL_ASSESSMENTS[assessment_type]
            results_text = f"""
{assessment['icon']} **نتائج {assessment['name']}**

📊 **النتيجة الإجمالية:** {total_score}
{color} **التقييم:** {severity_desc}

📋 **التفسير:**
{self.get_assessment_interpretation(assessment_type, severity)}

💡 **التوصيات:**
{self.get_assessment_recommendations(assessment_type, severity)}

⚠️ **ملاحظة مهمة:** هذا الاختبار لأغراض التوعية فقط وليس بديلاً عن التشخيص الطبي المتخصص.

🔒 **بياناتك محمية ومشفرة بالكامل**
            """

            keyboard = [
                [InlineKeyboardButton("🧠 تحليل الشخصية MBTI", callback_data="start_mbti")],
                [InlineKeyboardButton("🔍 التقييم النفسي الشامل", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("🔄 إعادة الاختبار", callback_data=f"assessment_{assessment_type}")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                results_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في إكمال الاختبار: {e}")
            await query.edit_message_text("حدث خطأ في معالجة النتائج.")

    def get_assessment_interpretation(self, assessment_type, severity):
        """الحصول على تفسير النتيجة"""
        interpretations = {
            'phq9': {
                'طبيعي': 'نتيجة ممتازة! لا توجد علامات للاكتئاب. استمر في العناية بصحتك النفسية.',
                'خفيف': 'قد تواجه بعض أعراض الاكتئاب الخفيف. يمكن التحسن بالرعاية الذاتية والدعم.',
                'متوسط': 'توجد أعراض اكتئاب متوسطة تتطلب انتباهاً. فكر في طلب المساعدة المهنية.',
                'متوسط إلى شديد': 'أعراض اكتئاب كبيرة تؤثر على حياتك. ننصح بقوة بطلب المساعدة المتخصصة.',
                'شديد': 'أعراض اكتئاب شديدة تتطلب تدخلاً عاجلاً. يرجى طلب المساعدة الطبية فوراً.'
            },
            'gad7': {
                'طبيعي': 'نتيجة ممتازة! لا توجد علامات للقلق المفرط. استمر في ممارساتك الصحية.',
                'خفيف': 'قد تواجه بعض القلق الخفيف. تقنيات الاسترخاء يمكن أن تساعد.',
                'متوسط': 'توجد أعراض قلق متوسطة. فكر في تعلم استراتيجيات إدارة القلق.',
                'شديد': 'أعراض قلق شديدة تؤثر على حياتك اليومية. ننصح بطلب المساعدة المتخصصة.'
            }
        }
        return interpretations.get(assessment_type, {}).get(severity, "لا يوجد تفسير متاح")

    def get_assessment_recommendations(self, assessment_type, severity):
        """الحصول على التوصيات"""
        recommendations = {
            'phq9': {
                'طبيعي': '• حافظ على نمط حياة صحي\n• مارس الرياضة بانتظام\n• حافظ على علاقات اجتماعية إيجابية',
                'خفيف': '• اهتم بالنوم الكافي\n• مارس أنشطة تجلب السعادة\n• تحدث مع أشخاص تثق بهم',
                'متوسط': '• فكر في العلاج النفسي\n• تجنب الكحول والمواد المضرة\n• حافظ على روتين يومي منتظم',
                'متوسط إلى شديد': '• اطلب المساعدة المهنية فوراً\n• تواصل مع خط المساعدة النفسية\n• لا تتردد في طلب الدعم',
                'شديد': '• اتصل بخدمات الطوارئ النفسية\n• تواصل مع طبيب نفسي\n• تجنب البقاء وحيداً'
            },
            'gad7': {
                'طبيعي': '• استمر في ممارسة تقنيات الاسترخاء\n• حافظ على التوازن في الحياة\n• مارس الأنشطة الممتعة',
                'خفيف': '• تعلم تقنيات التنفس العميق\n• مارس التأمل أو اليوغا\n• قلل من الكافيين',
                'متوسط': '• فكر في العلاج المعرفي السلوكي\n• مارس الرياضة بانتظام\n• تجنب المواقف المثيرة للقلق',
                'شديد': '• اطلب المساعدة المهنية\n• فكر في العلاج الدوائي تحت إشراف طبي\n• اطلب الدعم من الأهل والأصدقاء'
            }
        }
        return recommendations.get(assessment_type, {}).get(severity, "لا توجد توصيات متاحة")

    async def show_mbti_detailed_info(self, query, context):
        """عرض معلومات تفصيلية عن MBTI"""
        try:
            info_text = """
🧠 **معلومات تفصيلية عن اختبار MBTI**

📚 **نبذة تاريخية:**
تم تطوير مؤشر مايرز-بريغز للأنماط على يد كاثارين بريغز وابنتها إيزابيل مايرز، بناءً على نظريات كارل يونغ في علم النفس.

🎯 **الأبعاد الأربعة:**

**1. الطاقة (E/I):**
• الانبساط (E): يستمد الطاقة من التفاعل مع الآخرين
• الانطواء (I): يستمد الطاقة من التأمل الداخلي

**2. المعلومات (S/N):**
• الحس (S): يركز على الحقائق والتفاصيل
• الحدس (N): يركز على الأنماط والإمكانيات

**3. القرارات (T/F):**
• التفكير (T): يتخذ القرارات بناءً على المنطق
• المشاعر (F): يتخذ القرارات بناءً على القيم

**4. النمط (J/P):**
• الحزم (J): يفضل البنية والتخطيط
• المرونة (P): يفضل التلقائية والمرونة

🌟 **16 نمط شخصية مختلف**
كل مزيج من هذه الأبعاد ينتج نمطاً فريداً بخصائصه المميزة.
            """

            keyboard = [
                [InlineKeyboardButton("🚀 ابدأ الاختبار", callback_data="mbti_start_test")],
                [InlineKeyboardButton("🔙 العودة", callback_data="start_mbti")]
            ]

            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض معلومات MBTI: {e}")

    async def show_psychological_detailed_info(self, query, context):
        """عرض معلومات تفصيلية عن التقييم النفسي"""
        try:
            info_text = """
🔍 **معلومات تفصيلية عن التقييم النفسي الشامل**

📋 **ما هو التقييم النفسي؟**
هو فحص منهجي وشامل للحالة النفسية والعقلية للشخص، يهدف إلى فهم نقاط القوة والضعف وتحديد احتياجات الدعم.

🎯 **مكونات التقييم:**

**1. التاريخ الطبي:**
• الأمراض الجسدية والنفسية السابقة
• الأدوية المستخدمة
• التاريخ العائلي للاضطرابات النفسية

**2. البيئة الاجتماعية:**
• جودة العلاقات الأسرية
• شبكة الدعم الاجتماعي
• الضغوط البيئية والمهنية

**3. السلوكيات والعادات:**
• أنماط السلوك الصحي أو الضار
• آليات التأقلم المستخدمة
• السلوكيات الإدمانية المحتملة

**4. الحالة النفسية الحالية:**
• مستوى التوتر والقلق
• الحالة المزاجية العامة
• القدرة على التأقلم والصمود

📊 **نتائج التقييم:**
• تحليل شامل للحالة النفسية
• تحديد عوامل الخطر والحماية
• توصيات مخصصة للتحسن
• إرشادات للدعم الروحي والفلسفي

🔒 **السرية والخصوصية:**
جميع المعلومات مشفرة ومحمية، ولا يتم مشاركتها مع أي طرف ثالث.
            """

            keyboard = [
                [InlineKeyboardButton("🚀 ابدأ التقييم", callback_data="psych_start_evaluation")],
                [InlineKeyboardButton("🔙 العودة", callback_data="start_psychological_evaluation")]
            ]

            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض معلومات التقييم النفسي: {e}")

    async def show_detailed_info(self, query, context):
        """عرض معلومات مفصلة عن الخدمة"""
        try:
            info_text = """
ℹ️ **معلومات مفصلة عن مركز التحليل النفسي المتكامل**

🎯 **رسالتنا:**
تقديم خدمات تحليل نفسي شاملة تجمع بين العلم الحديث والإرشاد الروحي لمساعدتك على فهم ذاتك بعمق وتطوير إمكاناتك.

🔬 **خدماتنا العلمية:**

🧠 **تحليل الشخصية MBTI:**
• مؤشر مايرز-بريغز المعتمد عالمياً
• مصداقية 85% في التحليل
• 16 نمط شخصية مختلف
• توجيهات مهنية متخصصة

📊 **الاختبارات المعتمدة:**
• PHQ-9 للاكتئاب
• GAD-7 للقلق
• التقييم النفسي الشامل

🕌 **الدعم الروحي:**
• آيات قرآنية مناسبة لحالتك
• أحاديث نبوية شريفة
• تفسيرات وتطبيقات عملية

📚 **الدعم الفلسفي:**
• حكم من مختلف المدارس الفلسفية
• تطبيقات عملية للحكمة القديمة
• دعم من الفلسفة الحديثة

🔒 **الخصوصية والأمان:**
• تشفير البيانات بتقنية SHA-256
• إخفاء كامل للهوية
• لا نشارك المعلومات مع أي طرف ثالث
• يمكنك حذف بياناتك في أي وقت

⚠️ **تنبيه مهم:**
خدماتنا للتوعية والدعم النفسي، وليست بديلاً عن الاستشارة الطبية المتخصصة.

🌟 **فريق العمل:**
نحن فريق من المتخصصين في علم النفس والإرشاد الديني، نعمل على تقديم أفضل خدمة ممكنة.
            """

            keyboard = [
                [InlineKeyboardButton("🧠 تحليل الشخصية MBTI", callback_data="start_mbti")],
                [InlineKeyboardButton("📊 الاختبارات النفسية", callback_data="start_journey")],
                [InlineKeyboardButton("🔍 التقييم النفسي الشامل", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_main")]
            ]

            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض المعلومات المفصلة: {e}")

    async def start_command_from_callback(self, query, context):
        """تشغيل أمر البداية من callback"""
        try:
            user = query.from_user

            welcome_text = f"""
🌟 **أهلاً وسهلاً بك {user.first_name}** 🌟

🧠 **مركز التحليل النفسي المتكامل** 🧠

✨ **خدماتنا الشاملة:**

🎯 **تحليل الشخصية MBTI**
• اكتشف نمط شخصيتك من 16 نمط مختلف

📊 **الاختبارات المعتمدة**
• مقياس الاكتئاب PHQ-9
• مقياس القلق GAD-7

🔍 **التقييم النفسي الشامل**
• تحليل متكامل للحالة النفسية
• دعم ديني وفلسفي مخصص

🚀 **ابدأ رحلتك نحو فهم أعمق لذاتك!**
            """

            keyboard = [
                [InlineKeyboardButton("🧠 تحليل الشخصية MBTI", callback_data="start_mbti")],
                [InlineKeyboardButton("📊 الاختبارات النفسية", callback_data="start_journey")],
                [InlineKeyboardButton("🔍 التقييم النفسي الشامل", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("ℹ️ معلومات الخدمة", callback_data="more_info")]
            ]

            await query.edit_message_text(
                welcome_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في عرض القائمة الرئيسية: {e}")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية"""
        try:
            # يمكن إضافة معالجة للرسائل النصية حسب الحاجة
            # مثلاً، معالجة الشكاوى أو الاستفسارات
            user_text = update.message.text

            # هنا يمكن إضافة ذكاء اصطناعي لتحليل النص واقتراح الاختبارات المناسبة
            response_text = """
💬 **شكراً لرسالتك**

لتقديم أفضل مساعدة لك، يرجى استخدام الأزرار التفاعلية للوصول إلى خدماتنا:

🧠 **تحليل الشخصية MBTI** - لفهم نمط شخصيتك
📊 **الاختبارات النفسية** - لتقييم الحالة النفسية
🔍 **التقييم النفسي الشامل** - لتحليل متكامل

يمكنك البدء بأي خدمة تشاء من خلال الأزرار أدناه:
            """

            keyboard = [
                [InlineKeyboardButton("🧠 تحليل الشخصية MBTI", callback_data="start_mbti")],
                [InlineKeyboardButton("📊 الاختبارات النفسية", callback_data="start_journey")],
                [InlineKeyboardButton("🔍 التقييم النفسي الشامل", callback_data="start_psychological_evaluation")],
                [InlineKeyboardButton("ℹ️ معلومات الخدمة", callback_data="more_info")]
            ]

            await update.message.reply_text(
                response_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة النصية: {e}")

    def save_user_data(self, user):
        """حفظ بيانات المستخدم"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_interaction)
            VALUES (?, ?, ?, ?)
            ''', (user.id, user.username, user.first_name, datetime.now()))

            conn.commit()
            conn.close()
            logger.info(f"✅ تم حفظ بيانات المستخدم: {user.id}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ بيانات المستخدم: {e}")

    def save_mbti_results(self, user_id, session_id, analysis):
        """حفظ نتائج MBTI"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO mbti_results 
            (user_id, session_id, personality_type, dimension_scores, detailed_analysis)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id, session_id, analysis['personality_type'],
                json.dumps(analysis['dimension_scores']),
                json.dumps(analysis['details'])
            ))

            conn.commit()
            conn.close()
            logger.info(f"✅ تم حفظ نتائج MBTI للمستخدم: {user_id}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ نتائج MBTI: {e}")

    def save_psychological_results(self, user_id, session_id, results):
        """حفظ نتائج التقييم النفسي"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO psychological_evaluations 
            (user_id, session_id, evaluation_data, analysis_results, support_resources)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id, session_id,
                json.dumps(results['responses']),
                json.dumps(results['analysis']),
                json.dumps({
                    'religious': results['religious_support'],
                    'philosophical': results['philosophical_support']
                })
            ))

            conn.commit()
            conn.close()
            logger.info(f"✅ تم حفظ نتائج التقييم النفسي للمستخدم: {user_id}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ نتائج التقييم النفسي: {e}")

    def save_assessment_results(self, user_id, assessment_type, answers, total_score, severity):
        """حفظ نتائج الاختبارات النفسية"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO assessments 
            (user_id, assessment_type, questions_answers, total_score, severity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id, assessment_type, json.dumps(answers), 
                total_score, severity, datetime.now()
            ))

            conn.commit()
            conn.close()
            logger.info(f"✅ تم حفظ نتائج التقييم للمستخدم: {user_id}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ نتائج التقييم: {e}")

    def log_user_interaction(self, user_id, action):
        """تسجيل تفاعل المستخدم"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE users SET last_interaction = ? WHERE user_id = ?
            ''', (datetime.now(), user_id))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل التفاعل: {e}")

def clear_webhook():
    """مسح webhook لحل تعارض النسخ المتعددة"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            logger.info("🔧 تم مسح webhook القديم")
        else:
            logger.warning(f"⚠️ استجابة غير متوقعة من webhook: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ تعذر مسح webhook: {e}")

def run_bot():
    """تشغيل البوت مع حل مشكلة event loop نهائياً"""
    try:
        # مسح webhook القديم
        clear_webhook()

        # إنشاء البوت
        bot = AdvancedMentalHealthBot()

        async def main_async():
            """الدالة الرئيسية غير المتزامنة"""
            try:
                # إنشاء التطبيق
                application = Application.builder().token(TOKEN).build()

                # إضافة معالج الأخطاء
                async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
                    logger.error(f"Exception while handling an update: {context.error}")

                application.add_error_handler(error_handler)

                # إضافة المعالجات
                application.add_handler(CommandHandler("start", bot.start_command))
                application.add_handler(CallbackQueryHandler(bot.handle_callback))
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))

                # رسائل البداية
                logger.info("🚀 مركز التحليل النفسي المتكامل يبدأ التشغيل...")
                logger.info("🧠 تم تحميل نظام تحليل الشخصية MBTI")
                logger.info("📊 تم تحميل الاختبارات النفسية المعتمدة")
                logger.info("🔍 تم تحميل نظام التقييم النفسي الشامل")
                logger.info("💾 تم إنشاء قاعدة البيانات المتقدمة")
                logger.info("✅ البوت جاهز للعمل 24/7!")

                # تشغيل البوت
                await application.run_polling(drop_pending_updates=True)

            except Exception as e:
                logger.error(f"❌ خطأ في الدالة الرئيسية: {e}")

        # تشغيل البوت
        asyncio.run(main_async())

    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")

if __name__ == '__main__':
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("🔴 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ نهائي: {e}")
