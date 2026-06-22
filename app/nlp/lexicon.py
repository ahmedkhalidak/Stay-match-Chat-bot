"""
Static NLP vocabulary used by the rule-based pipeline.
Comprehensive bilingual support (Arabic + English).
"""

INTENT_KEYWORDS = {
    "room_search": [
        "غرفه", "غرفة", "غرف", "اوضة", "اوضه",
        "room", "rooms", "bedroom", "studio",
        "سنجل", "single", "خاص", "private", "فردي",
        "private room", "single room",
    ],
    "property_search": [
        "شقه", "شقة", "شقق", "سكن",
        "apartment", "flat", "property", "house", "home",
        "villa", "منزل", "عقار", "وحده", "عماره", "مبني",
    ],
    "follow_up": [
        "ارخص", "رخيص", "اقل", "cheap", "cheaper", "lower", "lowest",
        "اغلى", "غالي", "expensive", "higher", "highest", "اعلى",
        "تحت", "فوق", "سعر", "price", "budget",
        "مفروش", "مكيف", "wifi", "واي", "انترنت",
        "بلكونه", "حمام", "مطبخ", "غساله", "ثلاجه",
        "قريب", "بعيد", "هادئ", "واسع", "نضيف",
        "بدل", "شيل", "غير", "مش عايز",
        "furnished", "unfurnished", "ac", "internet",
        "balcony", "bathroom", "kitchen", "washer", "fridge",
        "near", "quiet", "spacious", "clean", "change",
    ],
    "show_more": [
        "كمان", "المزيد", "تاني", "باقي", "بقية", "كمل",
        "more", "next", "show more", "continue", "another",
        "additional", "extra",
    ],
    "go_back": [
        "ارجع", "اللي فات", "قبل", "رجوع", "السابق",
        "back", "previous", "go back", "return",
    ],
    "small_talk": [
        "ازيك", "اخبارك", "عامل", "صباح", "مساء", "هاي", "هلو",
        "اهلا", "مرحبا", "شكرا", "ميرسي", "تسلم", "سلام", "باي",
        "hello", "hi", "hey", "good morning", "good evening",
        "thanks", "thank you", "bye", "goodbye", "see you",
        "how are you", "how's it going",
    ],
    "faq": [
        # كلمات الاستفهام الأساسية
        "ازاي", "إزاي", "ازاى", "ايه", "مين", "هل", "عندك",
        "how", "what", "who", "do you", "why", "when", "where",
        "tell me", "how to", "i want to know",

        # كلمات إجرائية (للاكتشاف الدقيق للأسئلة)
        "أضيف", "اضيف", "أنشر", "انشر", "ارفع", "رفع",
        "أسجل", "سجل", "احذف", "حذف", "غير", "عدل",
        "اطلع", "اعرف", "عايز اعرف", "عاوز اعرف",
        "add", "post", "upload", "create", "register",
        "delete", "change", "edit", "know", "learn",

        # كلمات متعلقة بالخدمة
        "بتعمل", "فلوس", "دفع", "امان", "سعر", "رسوم",
        "تكلفة", "مصاريف", "fee", "fees", "payment",
        "safe", "secure", "insurance", "cost",

        # كلمات متعلقة بإضافة العقارات (hosting)
        "أضيف عقار", "اضيف عقار", "أنشر عقار", "انشر عقار",
        "أصير هوست", "اصير هوست", "become host", "list property",
        "معلومات العقار", "property information", "تفاصيل العقار",
        "غرف مشتركة", "shared rooms", "غرفة مفردة", "private room",
        "نشر العقار", "publish property", "موافقة الأدمن", "admin approval",
        "مراجعة العقار", "property review", "قائمة العقارات", "property listing",

        # كلمات متعلقة بحجز الشقق (booking)
        "كيف أحجز", "how to book", "احجز شقة", "book apartment",
        "طلب حجز", "booking request", "حالة الحجز", "booking status",
        "موافقة الحجز", "booking approval", "رفض الحجز", "booking rejection",
        "تفاصيل الشقة", "apartment details", "ملف المالك", "host profile",
        "فلتر البحث", "search filters", "تتبع الحجز", "track booking",
    ],
}

FULL_KEYWORDS = [
    "كامله", "كاملة", "full",
    "لوحدي", "لنفسي",
    "private apartment", "entire apartment", "entire place",
]

SHARED_KEYWORDS = [
    "مشترك", "مشتركة", "مشتركه",
    "shared", "roommate", "room mates",
    "مع ناس", "مع حد", "سكن مشترك",
    "شقه مشتركه", "شقة مشتركة",
    "shared apartment", "shared flat",
    "روم ميت", "شير", "مشاركة",
    "co-living", "coliving",
]

HOUSING_TYPE_KEYWORDS = {
    "apartment": [
        "شقة", "شقه", "شقق",
        "apartment", "flat", "apartments", "flats",
        "كاملة", "كامله", "full",
        "وحدة", "وحده", "عقار", "منزل",
        "house", "home", "villa",
    ],
    "room": [
        "اوضة", "اوضه", "غرفة", "غرفه", "غرف",
        "room", "rooms", "bedroom", "studio",
        "سنجل", "single", "خاص", "private", "فردي", "لوحدي",
        "private room", "single room",
    ],
    "shared": [
        "مشترك", "مشتركة", "مشتركه",
        "shared", "roommate", "roommates",
        "مع ناس", "مع حد", "سكن مشترك",
        "شقه مشتركه", "شقة مشتركة",
        "shared apartment", "shared flat",
        "روم ميت", "شير", "مشاركة",
        "co-living", "coliving",
    ],
}

ANY_HOUSING_TYPE_PHRASES = {
    "اعرض الكل", "عرض الكل", "كلهم", "الكل", "اي نوع", "أي نوع",
    "show all", "all types", "everything", "any type", "all",
}

AMENITY_KEYWORDS = {
    "wifi": ["wifi", "wi-fi", "واي", "انترنت", "نت", "internet", "net"],
    "furnished": ["مفروش", "furnished", "furniture"],
    "air_conditioning": ["مكيف", "تكييف", "ac", "air conditioning", "aircon", "cooling"],
    "balcony": ["بلكونه", "balcony", "balconies", "terrace"],
    "private_bathroom": ["حمام_خاص", "private_bathroom", "ensuite", "private bathroom", "en suite"],
    "kitchen": ["مطبخ", "kitchen"],
    "washer": ["غساله", "washer", "washing machine"],
    "refrigerator": ["ثلاجه", "fridge", "refrigerator"],
}

TENANT_KEYWORDS = {
    "student": ["طلبه", "طلاب", "student", "students", "سكن_طلبه"],
    "worker": ["موظف", "عامل", "worker", "موظفين", "employees", "staff"],
}

GENDER_KEYWORDS = {
    "male": ["شباب", "ولاد", "boys", "male", "رجاله", "رجالة", "males"],
    "female": ["بنات", "girls", "female", "سيدات", "ladies", "females"],
}

SORT_KEYWORDS = {
    "price_low": [
        "ارخص", "الارخص", "رخيص", "اقل",
        "cheap", "cheapest", "cheaper", "lower", "lowest",
        "سعر_منخفض", "low price", "lowest price",
    ],
    "price_high": [
        "اغلي", "الاغلي", "غالي", "اعلي",
        "expensive", "most expensive", "higher", "highest",
        "سعر_مرتفع", "high price", "highest price",
    ],
}

ROOM_NOUNS = {
    "غرفه", "غرف", "اوضه", "اوضة", "غرفة",
    "room", "rooms", "bedroom", "studio",
}

PROPERTY_NOUNS = {
    "شقه", "شقة", "شقق",
    "apartment", "flat", "property", "house", "home",
}

SEARCH_TYPE_BLOCKED_INTENTS = {
    "small_talk", "show_more", "go_back",
}

SLOT_REPLY_YES_WORDS = {
    "اه", "ايوه", "نعم", "ياريت", "اكيد", "ايوا",
    "yes", "yeah", "sure", "ok", "okay", "please",
}

SLOT_REPLY_NO_WORDS = {
    "لا", "لأ", "مش", "بدون", "شكرا",
    "no", "nah", "without", "no thanks", "don't",
}

SLOT_REPLY_ANY_WORDS = {
    "اي", "اي حاجة", "مش فارقة", "اي حد", "كله شغال", "مش مهم",
    "any", "anything", "anywhere", "any price", "doesn't matter",
    "i don't mind", "whatever",
}

NEGATION_WORDS = {
    "مش", "غير", "بدون",
    "without", "no", "not", "don't", "dont",
    "لا", "لأ",
}

# Action keywords for FAQ intent detection
# These help distinguish procedural questions from search queries
ACTION_KEYWORDS = {
    "add": ["أضيف", "اضيف", "أنشر", "انشر", "ارفع", "رفع", "add", "post", "upload"],
    "delete": ["احذف", "حذف", "شيل", "delete", "remove"],
    "edit": ["غير", "عدل", "تعديل", "edit", "change"],
    "learn": ["اعرف", "اطلع", "عايز اعرف", "know", "learn", "tell me"],
}