"""
ConversationFlow — State Machine for smart chatbot flow.
Manages the logical sequence of questions to minimize LLM usage.
"""

import random
from app.models.search_models import SearchFilters
from app.core.session_context import SessionContext, UserPreferences
from app.utils.logger import debug_log


class ConversationFlow:
    """
    State machine for the bot conversation.
    Flow: initial → search_type → location → price → amenities → results → follow_up
    """

    ASK_SEARCH_TYPE = (
        "أهلاً بيك في StayMatch! 😄\n"
        "عايز تسكن إزاي؟\n\n"
        "1️⃣ شقة كاملة (ليك لوحدك أو مع صحابك)\n"
        "2️⃣ شقة مشتركة (مع roommates — كل واحد ليه أوضة)\n"
        "3️⃣ أوضة في شقة مشتركة\n\n"
        'قولي "شقة" أو "شقة مشتركة" أو "أوضة" وانا هساعدك 👇'
    )

    ASK_LOCATION = (
        "تمام، عايزها فين؟ 📍\n\n"
        "ممكن تقولي اسم المدينة أو المنطقة، مثلاً:\n"
        "• الإسماعيلية\n"
        "• الإسكندرية\n"
        "• طنطا\n"
        "• أسوان\n\n"
        "أو اكتب أي منطقة انت عايزها في أي محافظة 👇"
    )

    ASK_PRICE = (
        "كويس! 💰\n"
        "ميزانيتك قد إيه بالشهر؟\n\n"
        'مثلاً: "تحت 5000" أو "من 3000 لـ 7000"\n'
        "أو قولي \"أي سعر\" 👇"
    )

    ASK_TENANT_TYPE = (
        "عايزها لـ مين بالظبط؟ 👤\n\n"
        "• طلاب\n"
        "• موظفين\n"
        "• شباب\n"
        "• بنات\n\n"
        "أو قولي \"أي حد\" 👇"
    )

    ASK_FURNISHED = (
        "عايزها مفروشة ولا لأ؟ 🛋️\n\n"
        '• "مفروشة"\n'
        '• "غير مفروشة"\n'
        '• "أي حاجة"'
    )

    def get_next_clarification(
        self,
        context: SessionContext,
        filters: SearchFilters,
    ) -> tuple[str | None, str | None]:
        """
        Returns (clarification_message, slot_name) or (None, None) if ready.
        Uses user preferences from context to auto-fill when possible.
        """
        debug_log("FLOW_CHECK", f"turn={context.turn_count}, filters={filters.model_dump()}")

        # 1. Search type
        if not filters.search_type:
            context.last_clarification = "search_type"
            return self.ASK_SEARCH_TYPE, "search_type"

        # 2. Location — always needed
        if not filters.city and not filters.governorate:
            # Try to fill from user preferences
            if context.user_preferences.preferred_location:
                # Check if it's a city or governorate
                from app.utils.location_mapping import location_mapping
                loc = location_mapping.get_governorate(context.user_preferences.preferred_location)
                if loc:
                    # It's a governorate name used as city
                    if context.user_preferences.preferred_location.lower() == loc.lower():
                        filters.governorate = loc
                    else:
                        filters.city = context.user_preferences.preferred_location
                else:
                    filters.city = context.user_preferences.preferred_location
                debug_log("FLOW_AUTO", f"Filled location from prefs: {filters.city or filters.governorate}")
            else:
                context.last_clarification = "location"
                return self.ASK_LOCATION, "location"

        # 3. Price — smart: if no price given, ask (but not mandatory)
        if filters.min_price is None and filters.max_price is None:
            # Don't ask for price every time — only in early turns or if no preference stored
            if context.turn_count <= 3 and context.no_results_count == 0:
                context.last_clarification = "price"
                return self.ASK_PRICE, "price"
            # Try fill from preferences
            if context.user_preferences.max_budget:
                filters.max_price = context.user_preferences.max_budget
                debug_log("FLOW_AUTO", f"Filled max_price from prefs: {filters.max_price}")
            elif context.user_preferences.min_budget:
                filters.min_price = context.user_preferences.min_budget
                debug_log("FLOW_AUTO", f"Filled min_price from prefs: {filters.min_price}")

        # 4. Tenant type & gender — ask once
        if context.turn_count <= 5 and filters.search_type in ("room", "shared"):
            if filters.tenant_type is None and filters.gender is None:
                if context.user_preferences.tenant_type:
                    filters.tenant_type = context.user_preferences.tenant_type
                    debug_log("FLOW_AUTO", f"Filled tenant_type from prefs: {filters.tenant_type}")
                elif context.user_preferences.gender:
                    filters.gender = context.user_preferences.gender
                    debug_log("FLOW_AUTO", f"Filled gender from prefs: {filters.gender}")
                else:
                    context.last_clarification = "tenant_type"
                    return self.ASK_TENANT_TYPE, "tenant_type"

        # 5. Furnished — ask once
        if context.turn_count <= 4 and filters.furnished is None:
            if context.user_preferences.furnished is not None:
                filters.furnished = context.user_preferences.furnished
                debug_log("FLOW_AUTO", f"Filled furnished from prefs: {filters.furnished}")
            else:
                context.last_clarification = "furnished"
                return self.ASK_FURNISHED, "furnished"

        # All required info collected
        context.last_clarification = None
        return None, None

    def build_smart_followup(
        self,
        context: SessionContext,
        filters: SearchFilters,
        results_count: int,
        has_more: bool,
    ) -> str:
        """
        Build a context-aware smart follow-up message after search results.
        No LLM needed — pure logic.
        """
        parts = []
        p = context.user_preferences

        # A. No results → suggest expanding
        if results_count == 0:
            if context.no_results_count >= 2:
                parts.append(
                    "مش لاقي حاجة مناسبة ليك في المناطق دي 😅\n"
                    "ممكن تجرب محافظة تانية زي الإسماعيلية أو الإسكندرية!"
                )
            else:
                parts.append(
                    "مش لاقي نتائج بالمواصفات دي 🤔\n"
                    "ممكن تجرب:\n"
                    "• غيّر السعر (مثلاً \"تحت 10000\")\n"
                    "• مدينة تانية\n"
                    '• أو قولي \"أي مكان\"'
                )
            return "\n\n".join(parts)

        # B. Results found → smart suggestions based on context
        suggestions = []

        if has_more:
            suggestions.append('"المزيد" عشان تشوف كمان')

        # Suggest price filter if not set
        if p.max_budget is None and p.min_budget is None:
            suggestions.append('"أرخص" لو عايز نتائج أقل سعراً')

        # Suggest amenities if not filtered yet
        if p.furnished is None:
            suggestions.append('"مفروشة"')
        if p.wifi is None:
            suggestions.append('"فيها واي فاي"')
        if p.air_conditioning is None:
            suggestions.append('"فيها تكييف"')

        # Suggest location change
        if context.total_searches >= 2:
            suggestions.append('محافظة تانية زي "الإسماعيلية"')

        # Suggest tenant type
        if filters.search_type in ("room", "shared") and p.tenant_type is None:
            suggestions.append('"للطلاب" أو "للموظفين"')

        if suggestions:
            random.shuffle(suggestions)
            picked = suggestions[:3]
            parts.append(f"💬 ممكن تجرب: {', '.join(picked)}")

        return "\n\n".join(parts) if parts else ""

    def apply_preferences_to_filters(
        self,
        context: SessionContext,
        filters: SearchFilters,
    ) -> SearchFilters:
        """
        Auto-fill missing filter fields from stored user preferences.
        Called before every search.
        """
        p = context.user_preferences
        if not p:
            return filters

        # Location
        if not filters.city and not filters.governorate and p.preferred_location:
            from app.utils.location_mapping import location_mapping
            gov = location_mapping.get_governorate(p.preferred_location)
            if gov and gov.lower() == p.preferred_location.lower():
                filters.governorate = gov
            else:
                filters.city = p.preferred_location

        # Price
        if filters.min_price is None and p.min_budget is not None:
            filters.min_price = p.min_budget
        if filters.max_price is None and p.max_budget is not None:
            filters.max_price = p.max_budget

        # Tenant
        if filters.tenant_type is None and p.tenant_type:
            filters.tenant_type = p.tenant_type
        if filters.gender is None and p.gender:
            filters.gender = p.gender

        # Amenities
        if filters.furnished is None and p.furnished is not None:
            filters.furnished = p.furnished
        if filters.wifi is None and p.wifi is not None:
            filters.wifi = p.wifi
        if filters.air_conditioning is None and p.air_conditioning is not None:
            filters.air_conditioning = p.air_conditioning
        if filters.balcony is None and p.balcony is not None:
            filters.balcony = p.balcony
        if filters.private_bathroom is None and p.private_bathroom is not None:
            filters.private_bathroom = p.private_bathroom
        if filters.shared_room is None and p.shared_room is not None:
            filters.shared_room = p.shared_room

        return filters
