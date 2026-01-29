"""Sub-scheme 20450251 - Education Cess Grants to Village Panchayats

Konkan Division - 5 districts (No Mumbai City/Suburban).
मागणी क्र. सी-१- 2045-विक्रेय वस्तु व सेवा यावरील इतर कर व शुल्क
(योजनेत्तर) 200 (दोन) महा. शिक्षण उपकर अधि कलम 23 अन्वये ग्रामपंचायतीना
प्रदाने (2045 0251), बाब क्र.50-इतर खर्च
"""
from .config import SCHEME_CONFIG
from .router import api_router, ui_router

__all__ = [
    "SCHEME_CONFIG",
    "api_router",
    "ui_router",
]
