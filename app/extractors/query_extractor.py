import json

from groq import Groq

from app.core.config import Settings

from app.models.search_models import (
    SearchFilters
)

from app.prompts.extraction_prompt import (
    EXTRACTION_PROMPT
)


settings = Settings()

client = Groq(
    api_key=settings.groq_api_key
)


class QueryExtractor:

    def clean_json(
        self,
        text: str,
    ):

        text = text.strip()

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        return text.strip()

    # ──────────────────────────────────────
    # Extract AI Filters
    # ──────────────────────────────────────

    def extract(
        self,
        message: str,
    ) -> SearchFilters:

        try:

            response = (
                client.chat.completions.create(

                    model="llama-3.1-8b-instant",

                    temperature=0,

                    messages=[

                        {
                            "role": "system",

                            "content": (
                                EXTRACTION_PROMPT
                            ),
                        },

                        {
                            "role": "user",

                            "content": (
                                message
                            ),
                        },
                    ],
                )
            )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            print(
                "\nAI RAW RESPONSE:"
            )

            print(content)

            cleaned = self.clean_json(
                content
            )

            data = json.loads(
                cleaned
            )

            # ──────────────────────────────
            # Intent Validation
            # ──────────────────────────────

            valid_intents = [

                "room_search",

                "property_search",

                "follow_up",

                "faq",

                "small_talk",

                "invalid",
            ]

            if (
                data.get("intent")
                not in valid_intents
            ):

                data["intent"] = (
                    "invalid"
                )

            # ──────────────────────────────
            # Search Type Validation
            # ──────────────────────────────

            valid_search_types = [

                "room",

                "property",
            ]

            if (
                data.get("search_type")
                not in valid_search_types
            ):

                data["search_type"] = (
                    None
                )

            # ──────────────────────────────
            # Return Filters
            # ──────────────────────────────

            return SearchFilters(

                intent=data.get(
                    "intent"
                ),

                search_type=data.get(
                    "search_type"
                ),

                city=data.get(
                    "city"
                ),

                governorate=data.get(
                    "governorate"
                ),

                min_price=data.get(
                    "min_price"
                ),

                max_price=data.get(
                    "max_price"
                ),

                tenant_type=data.get(
                    "tenant_type"
                ),

                furnished=data.get(
                    "furnished"
                ),

                wifi=data.get(
                    "wifi"
                ),

                private_bathroom=data.get(
                    "private_bathroom"
                ),

                balcony=data.get(
                    "balcony"
                ),

                gender=data.get(
                    "gender"
                ),

                shared_room=data.get(
                    "shared_room"
                ),

                sort_by=data.get(
                    "sort_by"
                ),
            )

        except Exception as e:

            print(
                "\nAI EXTRACTION ERROR:"
            )

            print(e)

            return SearchFilters()

    # ──────────────────────────────────────
    # Merge Filters
    # ──────────────────────────────────────

    def merge_filters(
        self,
        old_filters: SearchFilters,
        new_filters: SearchFilters,
    ) -> SearchFilters:

        merged = (
            old_filters.model_copy(
                deep=True
            )
        )

        for field, value in (
            new_filters
            .model_dump()
            .items()
        ):

            if value is not None:

                setattr(
                    merged,
                    field,
                    value,
                )

        return merged