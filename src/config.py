from typing import List, Dict

DCO_STAFF_IDENTIFIER = 'DCO Staff'

REGULAR_DISTRICTS: List[str] = [
    'Mumbai City', 'Mumbai Suburban', 'Thane', 'Palghar',
    'Raigad', 'Ratnagiri', 'Sindhudurg'
]

DISTRICTS: List[str] = REGULAR_DISTRICTS + [DCO_STAFF_IDENTIFIER]

CATEGORIES: List[str] = ['Permanent', 'Temporary']
CLASSES_SHEET1_2: List[str] = ['Class-1 & 2', 'Class-3', 'Class-4']
CLASSES_SHEET3: List[str] = ['1', '2', '3', '4']
STATUSES: List[str] = ['Filled', 'Vacant']

DESIGNATIONS: List[str] = [
    'Collector', 'Additional Collector', 'Deputy Collector',
    'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
    'Naib Tehsildar', 'Accounts Officer', 'Asst. Accounts Officer',
    'Deputy Accountant', 'Stenographer (Higher)',
    'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar',
    'Head Clerk (Awwal Karkun)', 'Clerk', 'Vehicle Driver',
    'Peon/Naik/Havaldar/Watchman/Cleaner', 'Law Officer (Honorarium)',
    'Head Clerk/Deputy Accountant', 'Circle Officer',
    'Clerk/Land Surveyor/Recovery Clerk',
    'Telephone Operator/Steno-Typist(Law Officer Asst.)'
]

PRIMARY_UNITS: List[str] = [
    '01- Salary', '03- Extra allowance',
    '06- Telephone, Electricity, Water And Charges',
    '10- Contractual Services', '11- Domestic Travel Expenses',
    '13- Office Expenses', '14- Lease And Tax', '16- Publications',
    '17- Computer Expenses', '20- Other Administrative Expenses',
    '24- Fuel Costs', '26- Advertising And Publicity Expenses',
    '36- Small Construction', '50- Other Expenses', '51- Motor Vehicles'
]

BUDGET_POST_DETAILS_ROW_LIMIT = 217
POST_STATUS_ROW_LIMIT = 87
POST_EXPENSES_ROW_LIMIT = 56
UNIT_EXPENDITURE_ROW_LIMIT = 104

POSITION_ORDER = [
    'Collector', 'Additional Collector', 'Deputy Collector',
    'Deputy Collector / Probationary Deputy Collector',
    'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
    'Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar',
    'Naib Tehsildar', 'Naib Tehsildar/Probationary Naib Tehsildar',
    'Accounts Officer', 'Asst. Accounts Officer', 'Law Officer (Honorarium)',
    'Deputy Accountant', 'Head Clerk/Deputy Accountant', 'Head Clerk (Awwal Karkun)',
    'Circle Officer', 'Stenographer (Higher)', 'Clerk',
    'Clerk/Land Surveyor/Recovery Clerk',
    'Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar',
    'Vehicle Driver', 'Telephone Operator/Steno-Typist(Law Officer Asst.)',
    'Peon/Naik/Havaldar/Watchman/Cleaner'
]
POSITION_SORT_MAP = {name: i for i, name in enumerate(POSITION_ORDER)}

POST_EXPENSES_DISTRICT_COMPONENT_FIELD: Dict[str, str] = {
    'Mumbai City': 'SeventhPayCommissionDifferenceNPS',
    'Mumbai Suburban': 'NPS',
    'Thane': 'SeventhPayCommissionDifference',
    'Palghar': 'SeventhPayCommissionDifferenceNPS',
    'Raigad': 'NPS',
    'Ratnagiri': 'NPS',
    'Sindhudurg': 'SeventhPayCommissionDifference',
    'DCO Staff': 'NPS',
}

DISTRICTS_MR = {
    "Mumbai City": "मुंबई शहर",
    "Mumbai Suburban": "मुंबई उपनगर", 
    "Thane": "ठाणे",
    "Palghar": "पालघर",
    "Raigad": "रायगड",
    "Ratnagiri": "रत्नागिरी",
    "Sindhudurg": "सिंधुदुर्ग",
    "DCO Staff": "जिल्हा संकलक कार्यालय कर्मचारी"
}

CATEGORIES_MR = {
    "Permanent": "स्थायी",
    "Temporary": "अस्थायी"
}

CLASSES_MR = {
    "Class-1 & 2": "वर्ग-१ व २",
    "Class-3": "वर्ग-३",
    "Class-4": "वर्ग-४"
}

CLASSES_SHEET3_MR = {
    "1": "१",
    "2": "२", 
    "3": "३",
    "4": "४"
}

STATUSES_MR = {
    "Filled": "भरलेली",
    "Vacant": "रिक्त"
}

DESIGNATIONS_MR = {
    "Collector": "जिल्हाधिकारी",
    "Additional Collector": "अपर जिल्हाधिकारी",
    "Deputy Collector": "उपजिल्हाधिकारी",
    "Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)": "तहसिलदार/अप्पर तहसिलदार/चिटणीस",
    "Naib Tehsildar": "नायब तहसिलदार",
    "Accounts Officer": "लेखाधिकारी",
    "Asst. Accounts Officer": "सहा. लेखाधिकारी",
    "Deputy Accountant": "उपलेखापाल",
    "Stenographer (Higher)": "लघुलेखक (उच्च)",
    "Stenographer (Lower)/Probationary Land Surveyor/Draftsman/Shirastedar": "लघुलेखक(निम्न)/परिक्षण भूमापक/आरेखक/शिरस्तेदार",
    "Head Clerk (Awwal Karkun)": "अव्वल कारकून",
    "Clerk": "लिपिक",
    "Vehicle Driver": "वाहन चालक",
    "Peon/Naik/Havaldar/Watchman/Cleaner": "शिपाई/नाईक/हवालदार/वॉचमन/स्वच्छक",
    "Law Officer (Honorarium)": "विधी अधिकारी (मानधन)",
    "Head Clerk/Deputy Accountant": "अव्वल कारकून/उपलेखापाल",
    "Circle Officer": "मंडळ अधिकारी",
    "Clerk/Land Surveyor/Recovery Clerk": "लिपिक/भूमापक/वसूली कारकून",
    "Telephone Operator/Steno-Typist(Law Officer Asst.)": "टेलि.ऑपरेटर/लघुटंकलेखक(विधी अधि.सहा.)",
    "Deputy Collector / Probationary Deputy Collector": "उपजिल्हाधिकारी/परिविक्षाधीन उपजिल्हाधिकारी",
    "Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar": "तहसिलदार/अप्पर तहसिलदार/चिटणीस/परिविक्षाधीन तहसिलदार",
    "Naib Tehsildar/Probationary Naib Tehsildar": "नायब तहसिलदार/परिविक्षाधीन ना.तहसिलदार"
}

MARATHI_TO_ENGLISH_DESIGNATIONS = {
    'जिल्हाधिकारी': 'Collector',
    'कलेक्टर': 'Collector',
    'अपर जिल्हाधिकारी': 'Additional Collector',
    'अप्पर जिल्हाधिकारी': 'Additional Collector',
    'उपजिल्हाधिकारी': 'Deputy Collector',
    'तहसिलदार': 'Tehsildar',
    'तहसीलदार': 'Tehsildar',
    'तहसीलदार/अप्पर': 'Tehsildar/Addl. Tehsildar/Chitnis (Secretary/Clerk)',
    'तहसिलदार/अप्पर': 'Tehsildar/Additional Tehsildar/Chitnis (Clerk/Secretary)/Probationary Tehsildar',
    'चिटणीस': 'Chitnis',
    'नायब तहसिलदार': 'Naib Tehsildar',
    'नायब तहसीलदार': 'Naib Tehsildar',
    'लेखाधिकारी': 'Accounts Officer',
    'सहा. लेखाधिकारी': 'Asst. Accounts Officer',
    'सहायक लेखाधिकारी': 'Asst. Accounts Officer',
    'उपलेखापाल': 'Deputy Accountant',
    'लघुलेखक': 'Stenographer',
    'लघुलेखक (उच्च)': 'Stenographer (Higher)',
    'स्टेनो': 'Stenographer',
    'अव्वल कारकून': 'Head Clerk (Awwal Karkun)',
    'मुख्य कारकून': 'Head Clerk (Awwal Karkun)',
    'लिपिक': 'Clerk',
    'कारकून': 'Clerk',
    'क्लर्क': 'Clerk',
    'वाहन चालक': 'Vehicle Driver',
    'ड्रायव्हर': 'Vehicle Driver',
    'चालक': 'Vehicle Driver',
    'शिपाई': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'चपरासी': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'चापरासी': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'नाईक': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'हवालदार': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'वॉचमन': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'पहारेकरी': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'स्वच्छक': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'सफाई कामगार': 'Peon/Naik/Havaldar/Watchman/Cleaner',
    'विधी अधिकारी': 'Law Officer (Honorarium)',
    'कायदा अधिकारी': 'Law Officer (Honorarium)',
    'मंडळ अधिकारी': 'Circle Officer',
    'वर्तुळ अधिकारी': 'Circle Officer',
    'भूमापक': 'Land Surveyor',
    'वसूली कारकून': 'Recovery Clerk',
    'आरेखक': 'Draftsman',
    'शिरस्तेदार': 'Shirastedar',
    'टेलिफोन ऑपरेटर': 'Telephone Operator',
    'टेली ऑपरेटर': 'Telephone Operator',
    'लघुटंकलेखक': 'Steno-Typist',
    'परिविक्षाधीन': 'Probationary',
    'परिक्षण': 'Probationary'
}

UNIT_ACCOUNT_MAP_MR = {
    "01- Salary": "01- वेतन",
    "03- Extra allowance": "03- अतिरिक्त भत्ता",
    "06- Telephone, Electricity, Water And Charges": "06- दूरध्वनी, वीज, पाणी शुल्क",
    "10- Contractual Services": "10- कंत्राटी सेवा",
    "11- Domestic Travel Expenses": "11- देशांतर्गत प्रवास खर्च",
    "13- Office Expenses": "13- कार्यालयीन खर्च",
    "14- Lease And Tax": "14- भाडेपट्टी व कर",
    "16- Publications": "16- प्रकाशने",
    "17- Computer Expenses": "17- संगणक खर्च",
    "20- Other Administrative Expenses": "20- इतर प्रशासकीय खर्च",
    "24- Fuel Costs": "24- इंधन खर्च",
    "26- Advertising And Publicity Expenses": "26- जाहिरात व प्रसिद्धी खर्च",
    "36- Small Construction": "36- लहान बांधकाम",
    "50- Other Expenses": "50- इतर खर्च",
    "51- Motor Vehicles": "51- मोटार वाहने"
}

import os
ORIGINAL_XLSX_PATH = os.getenv("ORIGINAL_XLSX_PATH", "excel_templates/original_template.xlsx")

ORIGINAL_SHEET_NAMES = {
    "budget_post_details": os.getenv("ORIGINAL_SHEET_BUDGET_POST_DETAILS", "Page-1"),
    "post_status": os.getenv("ORIGINAL_SHEET_POST_STATUS", "Page-2"),
    "post_expenses": os.getenv("ORIGINAL_SHEET_POST_EXPENSES", "Page-3"),
    "unit_expenditure": os.getenv("ORIGINAL_SHEET_UNIT_EXPENDITURE", "Page-4"),
}