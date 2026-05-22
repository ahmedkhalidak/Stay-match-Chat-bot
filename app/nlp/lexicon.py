"""
Static NLP vocabulary used by the rule-based pipeline.
Keeping it separate from the pipeline makes behavior easier to inspect and extend.
"""

INTENT_KEYWORDS = {
    "room_search": [
        "غرفه", "room", "bedroom", "studio", "سنجل", "single",
        "اوضة", "اوضه", "غرفة", "خاص", "private", "فردي",
    ],
    "property_search": [
        "شقه", "apartment", "flat", "property", "house", "home",
        "villa", "منزل", "عقار", "وحده", "عماره", "مبني",
        "شقة", "شقق", "سكن",
    ],
    "follow_up": [
        "ارخص", "رخيص", "cheap", "اقل", "lower",
        "اغلى", "غالي", "expensive", "اعلى", "higher",
        "تحت", "فوق", "سعر", "price", "budget",
        "مفروش", "مكيف", "wifi", "واي", "انترنت",
        "بلكونه", "حمام", "مطبخ", "غساله", "ثلاجه",
        "قريب", "بعيد", "هادئ", "واسع", "نضيف",
        "بدل", "شيل", "غير", "مش عايز",
    ],
    "show_more": [
        "كمان", "المزيد", "تاني", "more", "next", "show",
        "باقي", "بقية", "كمل", "continue",
    ],
    "go_back": [
        "ارجع", "اللي فات", "قبل", "back", "previous",
        "رجوع", "السابق",
    ],
    "small_talk": [
        "ازيك", "اخبارك", "عامل", "صباح", "مساء", "هاي", "هلو",
        "اهلا", "مرحبا", "شكرا", "ميرسي", "تسلم", "سلام", "باي",
    ],
    "faq": [
        "ازاي", "ايه", "مين", "هل", "عندك", "بتعمل", "فلوس",
        "دفع", "امان", "سعر", "رسوم", "تكلفة", "مصاريف",
    ],
}

FULL_KEYWORDS = [
    "كامله",
    "كاملة",
    "full",
    "لوحدي",
    "لنفسي",
    "private apartment",
]

SHARED_KEYWORDS = [
    "مشترك",
    "shared",
    "roommate",
    "مع ناس",
    "مع حد",
    "سكن مشترك",
    "شقه مشتركه",
    "شقة مشتركة",
    "shared apartment",
    "shared flat",
]

AMENITY_KEYWORDS = {
    "wifi": ["wifi", "wi-fi", "واي", "انترنت", "نت"],
    "furnished": ["مفروش", "furnished"],
    "air_conditioning": ["مكيف", "تكييف", "ac"],
    "balcony": ["بلكونه", "balcony"],
    "private_bathroom": ["حمام_خاص", "private_bathroom", "ensuite"],
    "kitchen": ["مطبخ", "kitchen"],
    "washer": ["غساله", "washer"],
    "refrigerator": ["ثلاجه", "fridge"],
}

TENANT_KEYWORDS = {
    "student": ["طلبه", "طلاب", "student", "students", "سكن_طلبه"],
    "worker": ["موظف", "عامل", "worker", "موظفين", "employees"],
}

GENDER_KEYWORDS = {
    "male": ["شباب", "ولاد", "boys", "male", "رجاله", "رجالة"],
    "female": ["بنات", "girls", "female", "سيدات", "ladies"],
}

SORT_KEYWORDS = {
    "price_low": ["ارخص", "الارخص", "رخيص", "cheap", "اقل", "lower", "سعر_منخفض"],
    "price_high": ["اغلي", "الاغلي", "غالي", "expensive", "اعلي", "الاعلي", "higher", "سعر_مرتفع"],
}

ROOM_NOUNS = {
    "غرفه",
    "اوضه",
    "اوضة",
    "غرفة",
    "room",
    "bedroom",
    "studio",
}

PROPERTY_NOUNS = {
    "شقه",
    "شقة",
    "شقق",
    "apartment",
    "flat",
    "property",
    "house",
    "home",
}

SEARCH_TYPE_BLOCKED_INTENTS = {
    "small_talk",
    "show_more",
    "go_back",
}

SLOT_REPLY_YES_WORDS = {
    "اه",
    "ايوه",
    "نعم",
    "ياريت",
    "اكيد",
    "ايوا",
}

SLOT_REPLY_NO_WORDS = {
    "لا",
    "لأ",
    "مش",
    "بدون",
    "شكرا",
}

SLOT_REPLY_ANY_WORDS = {
    "اي",
    "اي حاجة",
    "مش فارقة",
    "اي حد",
    "كله شغال",
    "مش مهم",
}

NEGATION_WORDS = {
    "مش",
    "غير",
    "بدون",
    "without",
    "no",
    "not",
    "لا",
    "لأ",
}
