import re
from functools import lru_cache

@lru_cache(maxsize=512)
def _translate_term_cached(term: str, translations_tuple: tuple) -> str:
    """Cached translation for repeated terms - O(1) after first lookup"""
    translations = dict(translations_tuple)
    for native, english in sorted(translations.items(), key=lambda x: len(x[0]), reverse=True):
        if native in term:
            return term.replace(native, english, 1)
    return term

def preprocess_question(question: str) -> str:
    if not question or not question.strip():
        return ""

    question = question.strip()
    original_question = question
    question_lower = question.lower()
    
    allowance_keywords = ['allowance', 'vehicle allowance', 'washing allowance', 'cash allowance', 
                         'footwear allowance', 'local supplementary allowance', 'भत्ता', 'भत्ते']
    pay_keywords = ['basic pay', 'grade pay', 'special pay', 'salary', 'compensation', 'मुळ वेतन', 'वेतन']
    post_keywords = ['posts', 'sanctioned posts', 'total posts', 'number of posts', 'पदे', 'पद']
    
    requires_district_filter = any(dist in question_lower for dist in ['mumbai city', 'mumbai suburban', 'thane', 'palghar', 'raigad', 'ratnagiri', 'sindhudurg'])
    requires_category_filter = any(cat in question_lower for cat in ['permanent', 'temporary', 'कायमस्वरूपी', 'तात्पुरते'])
    requires_class_filter = any(cls in question_lower for cls in ['class-1', 'class-2', 'class-3', 'class-4', 'वर्ग'])
    
    metadata = []
    if any(kw in question_lower for kw in allowance_keywords):
        metadata.append("REQUIRES_ALLOWANCE_FIELDS")
    if any(kw in question_lower for kw in pay_keywords):
        metadata.append("REQUIRES_PAY_FIELDS")  
    if any(kw in question_lower for kw in post_keywords):
        metadata.append("REQUIRES_POST_COUNTING")
    if requires_district_filter:
        metadata.append("REQUIRES_DISTRICT_FILTER")
    if requires_category_filter:
        metadata.append("REQUIRES_CATEGORY_FILTER")
    if requires_class_filter:
        metadata.append("REQUIRES_CLASS_FILTER")
    
    question = f"{question} {' '.join([f'[{m}]' for m in metadata])}" if metadata else question
    
    marathi_to_english = {
        'मुळ वेतन': 'basic pay', 'मुळवेतन': 'basic pay', 'पगार': 'salary', 'वेतन': 'salary',
        'उपसंकलक/तज्ञ अधिकारी': 'Deputy Collector/Expert Officer', 'उपसंकलक': 'Deputy Collector/Expert Officer', 'तज्ञ अधिकारी': 'Deputy Collector/Expert Officer',
        'शहर वास्तुविशारद': 'City Architect', 'वास्तुविशारद': 'City Architect',
        'सहाय्यक शहर वास्तुविशारद': 'Assistant City Architect', 'सहाय्यक वास्तुविशारद': 'Assistant City Architect',
        'अव्वल कारकून': 'Head Clerk', 'मुख्य कारकून': 'Head Clerk',
        'विभागीय अधिकारी': 'Divisional Officer', 'मंडळ अधिकारी': 'Divisional Officer', 'वर्तुळ अधिकारी': 'Divisional Officer',
        'लिपिक': 'Clerk', 'कारकून': 'Clerk', 'क्लर्क': 'Clerk',
        'वाहन चालक': 'Vehicle Driver', 'ड्रायव्हर': 'Vehicle Driver', 'चालक': 'Vehicle Driver',
        'सूचना वाहक': 'Notice Bearer', 'नोटिस वाहक': 'Notice Bearer',
        'शिपाई': 'Peon', 'चपडासी': 'Peon', 'चापडासी': 'Peon', 'चपरासी': 'Peon', 'चापरासी': 'Peon',
        'कर्मचारी': 'employee',
        'पद': 'post', 'पदे': 'posts', 'भरलेली पदे': 'filled posts', 'भरलेली': 'filled',
        'रिक्त पदे': 'vacant posts', 'रिक्त': 'vacant', 'खाली जागा': 'vacant position', 'रिक्त जागा': 'vacant position',
        'मंजूर पदे': 'sanctioned posts', 'मंजूर': 'sanctioned', 'कायमस्वरूपी': 'Permanent',
        'तात्पुरते': 'Temporary', 'तात्पुरत्या': 'temporary', 'खर्च': 'expenditure', 'व्यय': 'expense',
        'वैद्यकिय खर्च': 'medical expenses', 'वैद्यकिय': 'medical', 'महागाई भत्ता': 'dearness allowance',
        'भत्ते': 'allowances', 'भत्ता': 'allowance', 'अर्थसंकल्प': 'budget', 'निधी': 'fund', 'वाटप': 'allocation',
        'एकूण': 'total', 'सरासरी': 'average', 'वार्षिक': 'annual', 'तुलना': 'comparison', 'विश्लेषण': 'analysis',
        'कोकण विभाग': 'Konkan Division', 'कोकण': 'Konkan', 'मुंबई': 'Mumbai', 'मुंबई शहर': 'Mumbai City',
        'मुंबई उपनगर': 'Mumbai Suburban', 'ठाणे': 'Thane', 'पालघर': 'Palghar', 'रायगड': 'Raigad',
        'रत्नागिरी': 'Ratnagiri', 'सिंधुदुर्ग': 'Sindhudurg', 'वर्ग': 'class', 'श्रेणी': 'category'
    }
    
    hindi_to_english = {
        'मूल वेतन': 'basic pay', 'बेसिक पे': 'basic pay', 'तनख्वाह': 'salary',
        'चपरासी': 'Peon', 'क्लर्क': 'Clerk', 'चालक': 'Vehicle Driver',
        'भरे हुए पद': 'filled posts', 'खाली पद': 'vacant posts', 'रिक्त पद': 'vacant posts',
        'चिकित्सा व्यय': 'medical expenses', 'त्योहार अग्रिम': 'festival advance', 'उत्सव/सण अग्रिम': 'festival advance',
        'स्वग्राम/महाराष्ट्र दर्शन': 'swagram maharashtra darshan', '7 व्या वेतन आयोग फरक+ NPS': '7th pay commission difference nps',
        'कर्मचारी': 'employee', 'पद': 'post', 'पदों': 'posts', 'खर्च': 'expenditure', 'व्यय': 'expense',
        'बजट': 'budget', 'फंड': 'fund', 'आवंटन': 'allocation', 'कुल': 'total', 'औसत': 'average',
        'स्थायी': 'Permanent', 'अस्थायी': 'Temporary'
    }
    
    all_translations = {**marathi_to_english, **hindi_to_english}
    translations_tuple = tuple(all_translations.items())
    
    sorted_translations = sorted(all_translations.items(), key=lambda x: len(x[0]), reverse=True)
    for native_term, english_term in sorted_translations:
        if native_term in question:
            question = question.replace(native_term, english_term, 1)
    
    district_variants = {
        'mumbai suburban': 'Mumbai Suburban', 'mumbai sub': 'Mumbai Suburban', 
        'mumbai city': 'Mumbai City',
        'thane district': 'Thane',
        'palghar district': 'Palghar',
        'raigad district': 'Raigad',
        'mumbai': 'Mumbai City',
        'thane': 'Thane',
        'palghar': 'Palghar',
        'raigad': 'Raigad',
        'ratnagiri': 'Ratnagiri',
        'sindhudurg': 'Sindhudurg'
    }
    
    category_variants = {
        'permanent': 'Permanent',
        'perm': 'Permanent',
        'temporary': 'Temporary',
        'temp': 'Temporary'
    }
    
    designation_variants = {
        'deputy collector/expert officer': 'Deputy Collector/Expert Officer',
        'deputy collector': 'Deputy Collector/Expert Officer',
        'expert officer': 'Deputy Collector/Expert Officer',
        'city architect': 'City Architect',
        'assistant city architect': 'Assistant City Architect',
        'head clerk': 'Head Clerk',
        'divisional officer': 'Divisional Officer',
        'clerk': 'Clerk',
        'vehicle driver': 'Vehicle Driver',
        'notice bearer': 'Notice Bearer',
        'peon': 'Peon',
        'driver': 'Vehicle Driver'
    }
    
    class_variants = {
        'class 1 & 2': 'Class-1 & 2',
        'class 1 and 2': 'Class-1 & 2',
        'class-1 & 2': 'Class-1 & 2', 
        'class 4': 'Class-4',
        'class 3': 'Class-3',
        'class 2': 'Class-1 & 2',
        'class4': 'Class-4',
        'class3': 'Class-3',
        'class2': 'Class-1 & 2',
        'class1': 'Class-1 & 2',
        'class-4': 'Class-4',
        'class-3': 'Class-3',
        'class-2': 'Class-1 & 2',
        'class-1': 'Class-1 & 2'
    }
    
    division_variants = {
        'konkan division': ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg'],
        'mumbai division': ['Mumbai City', 'Mumbai Suburban'],
        'konkan': ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg']
    }
    
    unit_account_variants = {
        '01- salary': '01- Salary',
        'salary': '01- Salary',
        'salary expenditure': '01- Salary',
        'salary expenses': '01- Salary',
        '03- extra allowance': '03- Extra allowance',
        'extra allowance': '03- Extra allowance',
        'dearness allowance': '03- Extra allowance',
        'da': '03- Extra allowance',
        'da expenditure': '03- Extra allowance',
        '06- telephone electricity water and charges': '06- Telephone, Electricity, Water And Charges',
        'telephone electricity water': '06- Telephone, Electricity, Water And Charges',
        'telephone expenses': '06- Telephone, Electricity, Water And Charges',
        'telephone expenditure': '06- Telephone, Electricity, Water And Charges',
        'electricity expenses': '06- Telephone, Electricity, Water And Charges',
        'electricity expenditure': '06- Telephone, Electricity, Water And Charges',
        'water charges': '06- Telephone, Electricity, Water And Charges',
        '11- domestic travel expenses': '11- Domestic Travel Expenses',
        'domestic travel expenses': '11- Domestic Travel Expenses',
        'travel expenses': '11- Domestic Travel Expenses',
        'travel expenditure': '11- Domestic Travel Expenses',
        '13- office expenses': '13- Office Expenses',
        'office expenses': '13- Office Expenses',
        'office expenditure': '13- Office Expenses',
        '14- lease and tax': '14- Lease And Tax',
        'lease and tax': '14- Lease And Tax',
        'lease tax': '14- Lease And Tax',
        'lease': '14- Lease And Tax',
        '17- computer expenses': '17- Computer Expenses',
        'computer expenses': '17- Computer Expenses',
        'computer expenditure': '17- Computer Expenses',
        'computer cost': '17- Computer Expenses',
        'computer budget': '17- Computer Expenses',
        '26- advertising and publicity expenses': '26- Advertising And Publicity Expenses',
        'advertising and publicity expenses': '26- Advertising And Publicity Expenses',
        'advertising expenses': '26- Advertising And Publicity Expenses',
        'publicity expenses': '26- Advertising And Publicity Expenses',
        'advertising': '26- Advertising And Publicity Expenses',
        '51- motor vehicles': '51- Motor Vehicles',
        'motor vehicles': '51- Motor Vehicles',
        'motor vehicle': '51- Motor Vehicles',
        'vehicles': '51- Motor Vehicles'
    }
    
    medical_expense_keywords = [
        'medical expenses', 'medical expenditure', 'medical allowance',
        'Medical expenses', 'Medical expenditure', 'Medical allowance',
        'Medical Expenses', 'Medical Expenditure', 'Medical Allowance'
    ]
    
    district_expense_keywords = {
        'festival advance': ['festival advance', 'Festival advance', 'Festival Advance'],
        'nps': ['nps', 'NPS', 'Nps'],
        '7th pay commission': ['7th pay commission', '7th Pay Commission', 'seventh pay commission', 'Seventh Pay Commission'],
        'commission difference': ['commission difference', 'Commission difference', 'Commission Difference', '7th pay commission difference', '7th Pay Commission Difference']
    }
    
    question_lower = question.lower()
    
    sorted_districts = sorted(district_variants.items(), key=lambda x: len(x[0]), reverse=True)
    for variant, standard in sorted_districts:
        if variant != standard.lower() and standard not in question:
            pattern = r'\b' + re.escape(variant) + r'\b'
            question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    sorted_categories = sorted(category_variants.items(), key=lambda x: len(x[0]), reverse=True)  
    for variant, standard in sorted_categories:
        pattern = r'\b' + re.escape(variant) + r'\b'
        question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    sorted_designations = sorted(designation_variants.items(), key=lambda x: len(x[0]), reverse=True)
    for variant, standard in sorted_designations:
        pattern = r'\b' + re.escape(variant) + r'\b'
        question = re.sub(pattern, standard, question, count=1, flags=re.IGNORECASE)
    
    sorted_classes = sorted(class_variants.items(), key=lambda x: len(x[0]), reverse=True)
    for variant, standard in sorted_classes:
        if variant.lower() in question_lower and standard not in question:
            question = re.sub(re.escape(variant), standard, question, count=1, flags=re.IGNORECASE)
    
    for variant, districts in division_variants.items():
        if variant in question_lower:
            if 'konkan' in variant:
                question = question.replace(variant, 'Konkan Division', 1)
                question = question.replace(variant.title(), 'Konkan Division', 1)
                question = question.replace(variant.upper(), 'Konkan Division', 1)
            elif 'mumbai' in variant:
                question = question.replace(variant, 'Mumbai Division', 1)
                question = question.replace(variant.title(), 'Mumbai Division', 1)
                question = question.replace(variant.upper(), 'Mumbai Division', 1)
    
    sorted_unit_accounts = sorted(unit_account_variants.items(), key=lambda x: len(x[0]), reverse=True)
    for variant, standard in sorted_unit_accounts:
        if variant in question_lower:
            question = question.replace(variant, standard, 1)
            question = question.replace(variant.title(), standard, 1)
            question = question.replace(variant.upper(), standard, 1)
    
    for medical_keyword in medical_expense_keywords:
        if medical_keyword in question:
            question = question.replace(medical_keyword, 'medical expenses')
            break
    
    for expense_type, keywords in district_expense_keywords.items():
        for keyword in keywords:
            if keyword in question:
                question = question.replace(keyword, expense_type)
                break
    
    year_patterns = {
        '2021-22': '2021_22', '2021-2022': '2021_22',
        '2022-23': '2022_23', '2022-2023': '2022_23',
        '2023-24': '2023_24', '2023-2024': '2023_24',
        '2024-25': '2024_25', '2024-2025': '2024_25',
        '2025-26': '2025_26', '2025-2026': '2025_26'
    }
    
    for pattern, standard in year_patterns.items():
        if pattern in question:
            question = question.replace(pattern, standard)
    
    common_misspellings = {
        'mumbay': 'Mumbai City',
        'thane district': 'Thane',
        'palghar district': 'Palghar',
        'raigad district': 'Raigad',
        'basic salary': 'basic pay',
        'base pay': 'basic pay',
        'gross salary': 'salary',
        'net salary': 'salary',
        'expendeture': 'expenditure',
        'expend': 'expenditure',
        'budjet': 'budget'
    }
    
    question_words = question.split()
    for i, word in enumerate(question_words):
        word_lower = word.lower().strip('.,!?;:')
        if word_lower in common_misspellings:
            question_words[i] = word.replace(word_lower, common_misspellings[word_lower])
    
    question = ' '.join(question_words)
    question_lower = question.lower()
    
    budget_keywords = ['budget', 'allocation', 'fund', 'expenditure', 'spending', 'expense', 'cost', 'basic pay', 'अर्थसंकल्प', 'निधी', 'वाटप', 'खर्च']
    staff_keywords = ['staff', 'post', 'position', 'employee', 'personnel', 'vacant', 'filled', 'sanctioned', 'पद', 'पदे', 'कर्मचारी', 'भरलेली', 'रिक्त', 'मंजूर']
    salary_keywords = ['salary', 'pay', 'allowance', 'compensation', 'wage', 'remuneration', 'basic pay', 'पगार', 'वेतन', 'मुळ वेतन']
    financial_keywords = ['total', 'sum', 'average', 'count', 'compare', 'comparison', 'difference', 'एकूण', 'सरासरी']
    designation_keywords = ['Deputy Collector/Expert Officer', 'City Architect', 'Assistant City Architect', 'Head Clerk', 'Divisional Officer', 'Clerk', 'Vehicle Driver', 'Notice Bearer', 'Peon', 'उपसंकलक/तज्ञ अधिकारी', 'शहर वास्तुविशारद', 'सहाय्यक शहर वास्तुविशारद', 'अव्वल कारकून', 'विभागीय अधिकारी', 'लिपिक', 'वाहन चालक', 'सूचना वाहक', 'शिपाई']
    district_keywords = ['Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar', 'Raigad', 'Ratnagiri', 'Sindhudurg', 'DCO Staff', 'मुंबई', 'ठाणे', 'पालघर']
    
    all_context_keywords = budget_keywords + staff_keywords + salary_keywords + financial_keywords + designation_keywords + district_keywords
    
    has_relevant_context = any(keyword.lower() in question_lower for keyword in all_context_keywords)
    
    if not has_relevant_context:
        return original_question

    return question
