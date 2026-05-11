from app.nlp.room_tokens import (
    ROOM_TOKENS
)

from app.nlp.property_tokens import (
    PROPERTY_TOKENS
)

from app.nlp.price_tokens import (
    PRICE_TOKENS
)

from app.nlp.facility_tokens import (
    FACILITY_TOKENS
)

from app.nlp.sharing_tokens import (
    SHARING_TOKENS
)

from app.nlp.quality_tokens import (
    QUALITY_TOKENS
)

from app.nlp.misc_tokens import (
    MISC_TOKENS
)

TOKEN_MAP = {

    **ROOM_TOKENS,

    **PROPERTY_TOKENS,

    **PRICE_TOKENS,

    **FACILITY_TOKENS,

    **SHARING_TOKENS,

    **QUALITY_TOKENS,

    **MISC_TOKENS,
}