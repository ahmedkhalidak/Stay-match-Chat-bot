"""
Enhanced Price Extractor using the new PriceParser.
"""

from app.utils.price_parser import PriceParser
from app.utils.logger import debug_log


class PriceExtractor:
    """
    Price extractor that delegates to the enhanced PriceParser.
    """

    def extract(self, message: str):
        """
        Extract price information from message.
        Returns dict with min_price, max_price, and price_type.
        """
        result = PriceParser.extract_price(message)
        
        debug_log("FINAL_PRICE_FILTERS", f"min={result['min_price']}, max={result['max_price']}")
        
        return {
            "min_price": result["min_price"],
            "max_price": result["max_price"],
        }