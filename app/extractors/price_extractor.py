import re


class PriceExtractor:

    def extract(self, message: str):

        msg = message.lower()

        result = {
            "min_price": None,
            "max_price": None,
        }

        # ── Range extraction ─────────────────────
        range_patterns = [
            r"من\s*(\d+)\s*لـ?\s*(\d+)",
            r"من\s*(\d+)\s*الى\s*(\d+)",
            r"بين\s*(\d+)\s*و\s*(\d+)",
            r"between\s+(\d+)\s+and\s+(\d+)",
            r"(\d+)\s*-\s*(\d+)",
        ]

        for pattern in range_patterns:

            match = re.search(pattern, msg)

            if match:

                result["min_price"] = int(
                    match.group(1)
                )

                result["max_price"] = int(
                    match.group(2)
                )

                return result

        # ── Max price extraction ─────────────────
        max_patterns = [
            r"تحت\s*(\d+)",
            r"اقل من\s*(\d+)",
            r"اخري\s*(\d+)",
            r"بالكتير\s*(\d+)",
            r"ميزانيتي\s*(\d+)",
            r"budget\s*(\d+)",
            r"under\s*(\d+)",
            r"لحد\s*(\d+)",
            r"لحاد\s*(\d+)",
        ]

        for pattern in max_patterns:

            match = re.search(pattern, msg)

            if match:

                result["max_price"] = int(
                    match.group(1)
                )

                return result

        # ── Min price extraction ─────────────────
        min_patterns = [
            r"فوق\s*(\d+)",
            r"اكثر من\s*(\d+)",
            r"اكبر من\s*(\d+)",
            r"بداية من\s*(\d+)",
            r"من\s*(\d+)",
            r"above\s*(\d+)",
        ]

        for pattern in min_patterns:

            match = re.search(pattern, msg)

            if match:

                result["min_price"] = int(
                    match.group(1)
                )

                return result

        return result