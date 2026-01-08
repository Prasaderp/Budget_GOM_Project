"""Service for designation translation and search"""
from typing import Dict
from ...config import MARATHI_TO_ENGLISH_DESIGNATIONS


class DesignationService:
    """Service for handling designation translations"""
    
    @staticmethod
    def translate_marathi_designation_search(search_term: str) -> str:
        """
        Translate Marathi designation search to English
        
        Args:
            search_term: Search term (may be in Marathi or English)
            
        Returns:
            Translated designation or original if no match found
        """
        if not search_term:
            return search_term
        
        search_lower = search_term.lower().strip()
        
        # Direct match
        for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
            if m_term.lower() in search_lower or search_lower in m_term.lower():
                return e_desig
        
        # Partial word match
        for m_term, e_desig in MARATHI_TO_ENGLISH_DESIGNATIONS.items():
            m_words = m_term.lower().split()
            s_words = search_lower.split()
            for mw in m_words:
                for sw in s_words:
                    if len(sw) >= 3 and (mw.startswith(sw) or sw.startswith(mw)):
                        return e_desig
        
        return search_term

