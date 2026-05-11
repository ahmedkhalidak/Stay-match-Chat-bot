import random
import re


class ChatService:

    def normalize(
        self,
        text: str,
    ):

        text = (
            text
            .lower()
            .strip()
        )

        text = (
            text
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
        )

        text = re.sub(
            r"(.)\1+",
            r"\1",
            text
        )

        return text

    def generate_reply(
        self,
        message: str,
    ):

        text = self.normalize(
            message
        )

        # Greetings

        greeting_words = [

            "عامل",
            "اخبارك",
            "ازيك",
            "عامل اي",
            "عامل ايه",
            "اهلا",
            "هاي",
            "هلو",
        ]

        if any(
            word in text
            for word in greeting_words
        ):

            replies = [

                "الحمدلله 😄 وانت؟",

                "زي الفل   😎",

                "كله تمام 😄",

                "الدنيا ماشية الحمدلله 🙌",

                "تمام 😎",
            ]

            return random.choice(
                replies
            )

        # Thanks

        thanks_words = [

            "شكرا",

            "شكر",

            "ميرسي",

            "مرسي",

            "ثانكس",

            "متشكر",

            "متشكرين",

            "تسلم",

            "تسلملي",

            "حبيبي",
            "thanks",
            "thx",
            "شكراااا",
        ]

        if any(
            word in text
            for word in thanks_words
        ):

            replies = [

                "العفو يا نجم 😄",

                "تحت أمرك ❤️",

                "أي وقت 🙌",

                "حبيبي 😄",
            ]

            return random.choice(
                replies
            )

        # Bye

        bye_words = [

            "سلام",

            "باي",

            "اشوفك",

            "مع السلامه",
        ]

        if any(
            word in text
            for word in bye_words
        ):

            replies = [

                "مع السلامه يا نجم 😄",

                "اشوفك قريب 🙌",

                "نورت StayMatch 😎",
            ]

            return random.choice(
                replies
            )

        return "😄"