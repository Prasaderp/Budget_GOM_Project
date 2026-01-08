"""Sub-schemes for 2053 - District Administration"""
from .s20530019 import SCHEME_CONFIG as s20530019_config
from .s20530028 import SCHEME_CONFIG as s20530028_config
from .s20530153 import SCHEME_CONFIG as s20530153_config
from .s20530162 import SCHEME_CONFIG as s20530162_config
from .s20530233 import SCHEME_CONFIG as s20530233_config
from .s20530242 import SCHEME_CONFIG as s20530242_config
from .s20530304 import SCHEME_CONFIG as s20530304_config
from .s20530313 import SCHEME_CONFIG as s20530313_config
from .s20530378 import SCHEME_CONFIG as s20530378_config
from .s20530387 import SCHEME_CONFIG as s20530387_config

IMPLEMENTED_SCHEMES = {
    '20530019': s20530019_config,
    '20530028': s20530028_config,
    '20530153': s20530153_config,
    '20530162': s20530162_config,
    '20530233': s20530233_config,
    '20530242': s20530242_config,
    '20530304': s20530304_config,
    '20530313': s20530313_config,
    '20530378': s20530378_config,
    '20530387': s20530387_config
}
