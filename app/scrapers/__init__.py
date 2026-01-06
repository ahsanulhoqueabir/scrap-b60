"""
Scrapers package initialization
"""
# Import all scrapers for easy access
from . import prothomalo_bangla
from . import dailystar
from . import dailystar_bangla
from . import bd_pratidin
from . import bangla_tribune
from . import bbc_world
from . import bbc_topnews
from . import bd24live
from . import bd24live_bangla
from . import dailycampus_bangla
from . import jagonews24
from . import tbs_top
from . import tbs_bangladesh

__all__ = [
    'prothomalo_bangla',
    'prothomalo_english',
    'dailystar',
    'dailystar_bangla',
    'bd_pratidin',
    'bangla_tribune',
    'bbc_world',
    'bbc_topnews',
    'bd24live',
    'bd24live_bangla',
    'dailycampus_bangla',
    'jagonews24',
    'tbs_top',
    'tbs_bangladesh'
]
