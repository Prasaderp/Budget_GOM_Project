"""Configuration for sub-scheme 2245."""
from src.core.base_config import BaseSchemeConfig, FormConfig
from src.schemes.common.utils import GLOBAL_DISTRICTS

KONKAN_DISTRICTS = GLOBAL_DISTRICTS

SECTION3_DISTRICTS = ["Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"]

EXTRA_DISTRICT = "DCO Staff"
EXTRA_DISTRICT_MR = "उप आयुक्त (सामान्य) कोकण विभाग"

ROW_TYPE_DC = "DC"
ROW_TYPE_ZP = "ZP"
ROW_TYPE_SUBTOTAL = "SUBTOTAL"
ROW_TYPE_DIVISION = "DIVISION"
ROW_TYPE_GRAND_TOTAL = "GRAND_TOTAL"

TABLE_SECTIONS = [
    {
        "code": "22450155",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91)(01) रोख भत्ता, मृत व्यक्तींच्या कुटुंबियांना सहाय्य व जखमींना मदत, 31 सहायक अनुदाने (वेतनेत्तर) (22450155)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Cash allowance, assistance to families of deceased and injured, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450182",
        "text_mr": "02 पुर चक्रीवादळे इ., 101 अनुग्रह सहाय्य (93) इतर (03) पुरामुळे बाधीत झालेल्या व्यक्तींच्या पुनर्वसनाकरीता रस्ते व घरे इत्यादी बांधकामासाठी संपादन केलेल्या/अधिग्रहित केलेल्या जमिनी बद्दल नुकसान भरपाई देणे (अनिवार्य)31, सहायक अनुदाने (वेतनेत्तर) (22450182)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, Other, Compensation for land acquired for construction of roads and houses etc. for rehabilitation of flood affected persons (Compulsory), Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450191",
        "text_mr": "02 पुर चक्रीवादळे इ., 101 अनुग्रह सहाय्य (93) इतर (03) पुरामुळे बाधीत झालेल्या व्यक्तींच्या गृहनिर्माणासाठी‍ जमिनीचा विकास करण्यावरील खर्च (अनिवार्य)31, सहायक अनुदाने (वेतनेत्तर) (22450191)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, Other, Expenditure on land development for housing of flood affected persons (Compulsory), Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450217",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91)(02) राहत केंद्रामध्ये निवारा, अन्न, वस्त्र, औषधे इत्यादी चा पुरवठा, 31 सहायक अनुदाने (वेतनेत्तर) (22450217)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Provision of shelter, food, clothing, medicines etc. in relief centers, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450244",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका नुसार खर्च, (91)(04) इतर बाबी 31 सहाय्यक अनुदाने (वेतनेत्तर)(22450244)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Other matters, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450271",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 113 घरांची दुरुस्ती/पुनर्बाधंणी यासाठी सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91)(01) घरांची दुरुस्ती/पुर्नबांधणी यासाठी सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22450271)",
        "text_en": "Flood, Cyclones etc., Assistance for house repair/reconstruction, State Disaster Response Fund norms, Assistance for house repair/reconstruction, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450291",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 115 जमिनीतील वाळू , चिकणमाती व क्षार काढून टाकण्यासाठी शेतकरी यांना सहाय्य (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91)(01) शेतकरी यांना जमिनीतील वाळू , चिकणमाती व क्षार काढून टाकण्यासाठी  सहाय्य डोंगराळ भागातील शेतीवरील गाळ काढणे,  मत्स्य संवर्धन क्षेत्रातील गाळ काढणे व ती पुर्ववत करुन त्याची दुरुस्ती करणे, 31 सहायक अनुदाने (वेतनेत्तर) 22450291",
        "text_en": "Flood, Cyclones etc., Assistance to farmers for removal of sand, silt and saline from land, State Disaster Response Fund norms, Assistance for removal of silt from agricultural land in hilly areas, removal of silt from fish culture areas and its restoration/repair, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450315",
        "text_mr": "2 पूर चक्रीवादळे इत्यादी, 117 पशुधन खरेदीसाठी शेतक-यांना सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91)(01) मृत जनावरां ऐवजी पशुधन खरेदीसाठी अल्प व अत्यल्प भूधारक शेतक-यांना सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22450315)",
        "text_en": "Flood, Cyclones etc., Assistance to farmers for livestock purchase, State Disaster Response Fund norms, Assistance to small and marginal landholder farmers for livestock purchase in place of deceased animals, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450324",
        "text_mr": "02 पुर चक्रीवादळे इत्यादी, 91 राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च, (91) (01) हानी पोहचलेल्या होडया व मासेमारी साधनसामग्री यांची दुरुस्ती / ती नव्याने पुरवणे यासाठी सहाय्य (22450324) ",
        "text_en": "Flood, Cyclones etc., State Disaster Response Fund norms, Assistance for repair of damaged boats and fishing equipment or providing new ones",
        "has_extra_district": False,
    },
    {
        "code": "22450333",
        "text_mr": "मागणी क्र.सी-6, 2245 नैसर्गिक आपत्तीच्या निवारणासाठी सहाय्य, 02 पुर चक्रीवादळे इ., 119 हानी पोहोचलेली हत्यारे व साधनसामग्री यांची दुरुस्ती/ती नव्याने पुरविणे यासाठी हस्तकला/हातमाग कारागिराना सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका नुसार खर्च, (91) (01) हानी पोहोचलेली हत्यारे व साधनसामग्री यांची दुरुस्ती/ती नव्याने पुरविणे तसेच कच्चा प्रक्रीयाधीन तयार मालाच्या नुकसानीसाठी कारागिराना सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22450333)",
        "text_en": "Flood, Cyclones etc., Assistance to handicraft/handloom artisans for repair of damaged tools and equipment or providing new ones, State Disaster Response Fund norms, Assistance to artisans for repair of damaged tools and equipment or providing new ones and for loss of raw material and finished goods, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22450988",
        "text_mr": "02 पुर चक्रीवादळे इ., 101 अनुग्रह सहाय्य (93) इतर (03) पुरामुळे बाधीत झालेल्या व्यक्तींच्या पुनर्वसनाकरीता रस्ते, पाणी पुरवठा, शाळा, चावडी, विद्युत पुरवठा इत्यादी नागरी सुविंधावरील खर्च (अनिवार्य)31, सहायक अनुदाने (वेतनेत्तर) (22450988)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, Other, Expenditure on restoration of civic amenities like roads, water supply, schools, chavdi, electric supply etc. for rehabilitation of flood affected persons (Compulsory), Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452194",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (92) राज्य आपत्ती प्रतिसाद निधीच्या मानका व्यतिरीक्त खर्च, (91)(01) रोख भत्ता, मृत व्यक्तींच्या कुटुंबियांना सहाय्य व जखमींना मदत, 31 सहायक अनुदाने (वेतनेत्तर) (22452194)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, Expenditure beyond State Disaster Response Fund norms, Cash allowance, assistance to families of deceased and injured, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452247",
        "text_mr": "(02) पूर चक्रीवादळे, इ. 101, अनुग्रह सहाय्य (92) राज्य आपत्ती प्रतिसाद निधीच्या मानका व्यतिरीक्त खर्च (92) (06) राहत केंद्रामध्ये निवारा, अन्न, वस्त्र, औषधे इत्यादींचा पुरवठा (22452247)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, Expenditure beyond State Disaster Response Fund norms, Provision of shelter, food, clothing, medicines etc. in relief centers",
        "has_extra_district": False,
    },
    {
        "code": "22452309",
        "text_mr": "02, पुर चक्रीवादळे इ.101, अनुग्रह सहाय्य (92) राज्य प्रतिसाद निधीच्या मानकानुसार खर्च (92) (12) पीक नुकसानीमुळे शेतक-यांना सहाय्य 31 सहाय्यक अनुदाने (वेतनेत्तर) (22452309)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Assistance to farmers due to crop loss, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452327",
        "text_mr": "02 पुर चक्रीवादळे इ.,113 घरांची दुरुस्ती/पुनर्बांधणी यासाठी सहाय्य, (92) राज्य आपत्ती प्रतिसाद निधीच्या मानका व्यतिरीक्त खर्च, (92) (01) घरांची दुरुस्ती/पुनर्बांधणी यासाठी सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22452327)",
        "text_en": "Flood, Cyclones etc., Assistance for house repair/reconstruction, Expenditure beyond State Disaster Response Fund norms, Assistance for house repair/reconstruction, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452363",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 117 पशुधन खरेदीसाठी शेतकरी यांना सहाय्य, (92) राज्य आपत्ती प्रतिसाद निधीच्या मानका व्यतिरीक्त खर्च, (92)(01) मृत जनावरांऐवजी पशुधन खरेदीसाठी अल्प व अत्यल्प भूधारक शेतकरी यांना सहाय्य, 31 सहायक अनुदाने  (22452363)",
        "text_en": "Flood, Cyclones etc., Assistance for livestock purchase, Expenditure beyond State Disaster Response Fund norms, Assistance to small and marginal farmers for livestock purchase in place of deceased animals, Grant-in-aid",
        "has_extra_district": False,
    },
    {
        "code": "22452372",
        "text_mr": "02, पूर चक्रीवादळे इ., 118 हानी पोहोचलेल्या होडया व मासेमारी साधनसामग्री यांची दुरुस्ती / ती नव्याने पुरविणे यासाठी सहाय्य (92) राज्य आपत्ती प्रतिसाद निधीच्या मानकाव्यतिरिक्त खर्च (92) (01) हानी पोहोचलेल्या होडया व मासेमारी साधनसामग्री यांची दुरुस्ती / ती नव्याने पुरविणे  तसेच मासे बियाणे यासाठी सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22452372)",
        "text_en": "Flood, Cyclones etc., Assistance for repair/providing new damaged boats and fishing equipment, Expenditure beyond State Disaster Response Fund norms, Assistance for repair/providing new damaged boats and fishing equipment and fish seeds, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452381",
        "text_mr": "02 पुर चक्रीवादळे इ., 119 हानी पोहोचलेली हत्यारे व साधनसामग्री यांची दुरुस्ती/ती नव्याने पुरविणे यासाठी हस्तकला/हातमाग कारागिराना सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका व्यतिरिक्त खर्च, (91) (01) हानी पोहोचलेली हत्यारे व साधनसामग्री यांची दुरुस्ती/ती नव्याने पुरविणे तसेच कच्चा प्रक्रीयाधीन तयार मालाच्या नुकसानीसाठी कारागिराना सहाय्य, 31 सहायक अनुदाने (वेतनेत्तर) (22452381)",
        "text_en": "Flood, Cyclones etc., Assistance to handicraft/handloom artisans for repair of damaged tools and equipment or providing new ones, Expenditure beyond State Disaster Response Fund norms, Assistance to artisans for repair of damaged tools and equipment or providing new ones and for loss of raw material and finished goods, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452407",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी,  800 इतर खर्च, (92) राज्य आपत्ती प्रतिसाद निधीच्या मानकाव्यतिरीक्त खर्च (92)(01) इतर खर्च 31 सहाय्यक अनुदाने (वेतनत्तेर) (22452407) दत्तमत",
        "text_en": "Flood, Cyclones etc., Other expenditure, Expenditure beyond State Disaster Response Fund norms, Other expenditure, Grant-in-aid (Non-salary) - Adopted Vote",
        "has_extra_district": True,
    },
    {
        "code": "22452434",
        "text_mr": "01 अवर्षण, (91)राज्य आपत्ती प्रतिसाद निधीच्या मानकांनुसार खर्च (91)(05) पीक नुकसानीमुळे शेतक-यांना मदत (22452434), 31 सहाय्यक अनुदाने",
        "text_en": "Drought, State Disaster Response Fund norms, Assistance to farmers due to crop loss, Grant-in-aid",
        "has_extra_district": False,
    },
    {
        "code": "22452452",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका नुसार खर्च, (91)(05) पिक नुकसानीमुळे शेतक-यांना मदत, 31 सहाय्य अनुदाने (वेतनेत्तर) (22452452)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Assistance to farmers due to crop loss, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452461",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका नुसार खर्च, (91)(06) नैसर्गिक आपत्तीमुळे अनुज्ञेय विभागातील आपत्ती्‌ग्रस्त पायाभूत सुविधांच्या तातडीच्या स्वरुपाच्या दुरुस्ती / पुर्नस्थापनेसाठी खर्च,31सहायक अनुदाने(वेतनेत्तर)(22452461)",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Expenditure for urgent repair/restoration of disaster-affected infrastructure in authorized departments, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452472",
        "text_mr": "06 भूकंप, 101 अनग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकानुसार खर्च (91) (01) भूकंपग्रस्तांसाठी सहाय्य, 31 सहाय्यक अनुदाने (वेतनेत्तर) (22452472)",
        "text_en": "Earthquake, Ex-gratia assistance, State Disaster Response Fund norms, Assistance to earthquake-affected, Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452499",
        "text_mr": "80 सर्वसाधारण, 800 इतर खर्च (91) राज्य आपत्ती प्रतिसाद निधीच्या मानकांनुसार खर्च (91)(01) शोध, बचाव कार्य, व लोकांना सुरक्षित स्थळी हलविण्यासाठी आपत्तीच्या प्रतिसादासाठी (संपर्कसाधनासह) खरेदी करावयाची साधनसामुग्री (आपत्ती प्रतिसाद निधीच्या 5 टक्के मर्यादेपर्यंत) 22452499 अंतर्गत, 31 सहाय्यक अनुदाने (वेतनेत्तर)",
        "text_en": "General, Other expenditure, State Disaster Response Fund norms, Purchase of equipment for disaster response (with communication facilities) for search, rescue work, and moving people to safe places (up to 5% limit of Disaster Response Fund), Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22452603",
        "text_mr": "मागणी क्र.सी-6,नैसर्गिक आपत्तीच्या निवारणासाठी सहाय्य, 80 सर्व साधारण 102 आपत्तीप्रवण क्षेत्रामध्ये नैसर्गिक आपत्कालीन परिस्थितीबाबतच्या तातडीच्या योजनांचे व्यवस्थापन करणे (06) चक्रीवादळ रोधक बांधकाम करणे (06) (01) चक्रीवादळ रोधक बांधकाम करणे (75 टक्के केंद्र हिस्सा) (कार्यक्रम) (22452603) 31 सहाय्यक अनुदाने (वेतनेत्तर)",
        "text_en": "Demand C-6, Natural Calamity Relief, General, Management of urgent schemes regarding natural calamity situation in disaster prone areas, Cyclone resistant construction (75% Central Share), Grant-in-aid (Non-salary)",
        "has_extra_district": False,
    },
    {
        "code": "22454141",
        "text_mr": "02 पूर चक्रीवादळे इत्यादी, 101 अनुग्रह सहाय्य, (91) राज्य आपत्ती प्रतिसाद निधीच्या मानका नुसार खर्च, (91)(04) इतर बाबी 31 सहाय्यक अनुदाने (वेतनेत्तर)  (22454141) COVID-19",
        "text_en": "Flood, Cyclones etc., Ex-gratia assistance, State Disaster Response Fund norms, Other matters, Grant-in-aid (Non-salary) - COVID-19",
        "has_extra_district": True,
    },
    {
        "code": "22454188",
        "text_mr": "(91) (01) पूर्व तयारी व क्षमता बांधणी (वित्त आयोग) (अनिवार्य)  (2245 4188) 31 सहायक अनुदाने",
        "text_en": "Preparedness and Capacity Building (Finance Commission) (Compulsory), Grant-in-aid",
        "has_extra_district": True,
    },
    {
        "code": "22451761_10",
        "text_mr": "80 सर्वसाधारण-पंचवार्षिक योजनांतर्गत योजना राज्य योजनांतर्गत योजना-001 संचालन व प्रशासन (01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर,साधनसामुग्रीसह सुसज्जीकरण करणे 22451761-10 - कंत्राटीसेवा",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 10 - Contractual Services",
        "has_extra_district": True,
    },
    {
        "code": "22451761_11",
        "text_mr": "80 सर्व साधारण (01) (01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर व साधन सामुग्रीसह सुसज्जीकरण करणे (2245 1761) 11-देशांतर्गत प्रवास खर्च",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 11 - Domestic Travel Expenses",
        "has_extra_district": True,
    },
    {
        "code": "22451761_21",
        "text_mr": "80 सर्व साधारण (01) (01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर व साधन सामुग्रीसह सुसज्जीकरण करणे (2245 1761) 21-पुरवठा व सामुग्री",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 21 - Supplies and Materials",
        "has_extra_district": True,
    },
    {
        "code": "22451761_27",
        "text_mr": "80 सर्व साधारण (01) (01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर व साधन सामुग्रीसह सुसज्जीकरण करणे (2245 1761) 27-लहान बांधकामे",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 27 - Minor Works",
        "has_extra_district": True,
    },
    {
        "code": "22451761_31",
        "text_mr": "80 सर्वसाधारण-पंचवार्षिक योजनांतर्गत योजना-राज्य योजनांतर्गत योजना-001 संचालन व प्रशासन-(01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर,साधनसामुग्रीसह सुसज्जीकरण करणे 22451761-31, सहायक अनुदाने",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 31, Grant-in-aid",
        "has_extra_district": True,
    },
    {
        "code": "22451761_52",
        "text_mr": "80 सर्व साधारण (01) (01) महाराष्ट्र राज्य आपत्ती व्यवस्थापन प्राधिकरणाचे कार्यालय स्थापन करणे व फर्निचर व साधन सामुग्रीसह सुसज्जीकरण करणे (2245 1761) 52-यंत्र सामुग्री",
        "text_en": "General-Five Year Plan-State Plan-001 Administration and Management-(01) Establishment of Maharashtra State Disaster Management Authority office and furnishing with furniture and equipment (22451761) 52 - Machinery and Equipment",
        "has_extra_district": True,
    },
    {
        "code": "22450093",
        "text_mr": "2245-नैसर्गिक आपत्तीच्या निवारणासाठी सहाय्य-01-अवर्षण-102- पिण्याच्या पाण्याचा पुरवठा, (91)(01) पिण्याच्या पाण्याचा आकस्मिक निकडीचा पुरवठा 31 सहाय्यक अनुदाने (वेतनेत्तर)(22450093)",
        "text_en": "2245-Natural Calamity Relief-01-Drought-102-Drinking Water Supply, (91)(01) Emergency Drinking Water Supply 31 Aid Grants (Non-Salary) (22450093)",
        "has_extra_district": False,
        "is_section3": True,
    },
    {
        "code": "22452185",
        "text_mr": "2245-नैसर्गिक आपत्तीच्या निवारणा साठी सहाय्य-01- अवर्षण- 102- पिण्याच्या पाण्याचा पुरवठा, (92)) (01) पिण्याच्या पाण्याचा आकस्मिक निकडीचा पुरवठा 31 सहाय्यक अनुदाने (वेतनेत्तर) (22452185)",
        "text_en": "2245-Natural Calamity Relief-01-Drought-102-Drinking Water Supply, (92)) (01) Emergency Drinking Water Supply 31 Aid Grants (Non-Salary) (22452185)",
        "has_extra_district": False,
        "is_section3": True,
    },
]

def get_table_section(code: str) -> dict:
    for section in TABLE_SECTIONS:
        if section["code"] == code:
            return section
    return None

def get_all_table_sections() -> list:
    return TABLE_SECTIONS.copy()

def get_districts_for_section(table_section_code: str) -> list:
    section = get_table_section(table_section_code)
    if not section:
        return KONKAN_DISTRICTS
    if section.get("is_section3"):
        return SECTION3_DISTRICTS
    if section["has_extra_district"]:
        return KONKAN_DISTRICTS + [EXTRA_DISTRICT]
    return KONKAN_DISTRICTS

def get_section3_table_sections() -> list:
    return [s for s in TABLE_SECTIONS if s.get("is_section3")]

SCHEME_CONFIG = BaseSchemeConfig(
    code="2245",
    parent_scheme="2245",
    scheme_type="voted",
    name_en="Natural Calamity Relief - Section 1",
    name_mr="नैसर्गिक आपत्तीच्या निवारणासाठी सहाय्य - विभाग 1",
    implemented=True,
    entry_point="/ui/s2245/section1",
    completion_enabled=True,
    designations=[],
    designations_mr={},
    categories=[],
    categories_mr={},
    classes=[],
    classes_mr={},
    primary_units=[],
    primary_units_mr={},
    forms={
        "district_expenditure": FormConfig(
            name="district_expenditure",
            table_name="district_expenditure_2245",
            label_mr="जिल्हानिहाय खर्च",
            label_en="District-wise Expenditure",
        ),
    },
)

