from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database import get_db
from src import models
from src.utils_cache import memory_cache
import logging
import re

router = APIRouter(prefix="/training", tags=["Training"], include_in_schema=False)

TRAINING_CONTENT = {
    "dco": {
        "dco": """<h3>DCO मुख्य प्रशासक मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण संपूर्ण कोकण विभागाचे मुख्य प्रशासक आहात. आपल्याकडे सर्व जिल्हे आणि तालुक्यांच्या डेटाची पूर्ण माहिती आणि नियंत्रण आहे.</p>

<h4>मुख्य वैशिष्ट्ये:</h4>
<ul>
<li><strong>संवर्गनिहाय माहिती:</strong> हे फक्त DCO साठी उपलब्ध आहे. येथे आपण सर्व जिल्ह्यांच्या संवर्गनिहाय माहिती पाहू शकता.</li>
<li><strong>अंदाजपत्रक सद्यस्थिती:</strong> सर्व जिल्हे आणि तालुक्यांच्या बजेट स्थितीचे मॉनिटरिंग करा.</li>
<li><strong>वेळ व्यवस्थापन:</strong> जिल्हा आणि तालुका स्तरावर डेटा भरण्याचे कालावधी सेट करा.</li>
<li><strong>तालुका सक्रियता:</strong> तालुका वापरकर्त्यांना सक्रिय/निष्क्रिय करा.</li>
<li><strong>आर्थिक वर्ष व्यवस्थापन:</strong> नवीन आर्थिक वर्ष जोडा किंवा हटवा.</li>
</ul>

<h4>सर्व प्रपत्रांची पहुंच:</h4>
<ul>
<li><strong>प्रपत्र ड:</strong> बजेट पोस्ट तपशील - सर्व जिल्ह्यांचा डेटा</li>
<li><strong>प्रपत्र क:</strong> पोस्ट स्थिती - सर्व जिल्ह्यांचा डेटा</li>
<li><strong>प्रपत्र ब:</strong> पोस्ट खर्च - सर्व जिल्ह्यांचा डेटा</li>
<li><strong>प्रपत्र अ:</strong> युनिट खर्च - सर्व जिल्ह्यांचा डेटा</li>
</ul>

<h4>कामाचा क्रम:</h4>
<ol>
<li>जिल्हा स्तरावरील अधिकाऱ्यांकडून डेटा प्राप्त करा</li>
<li>AI Assistant वापरून डेटाचे विश्लेषण करा</li>
<li>Chat प्रणालीद्वारे अधिकाऱ्यांशी संवाद साधा</li>
<li>संवर्गनिहाय माहिती पाहून सर्व जिल्ह्यांची तुलना करा</li>
<li>अंदाजपत्रक सद्यस्थिती मॉनिटर करा</li>
</ol>

<h4>AI Assistant वापर:</h4>
<p>AI Assistant च्या मदतीने आपण डेटा विश्लेषण, प्रश्न विचारू शकता. उदाहरणार्थ: "मुंबई सिटी जिल्ह्याचा एकूण खर्च किती आहे?"</p>

<h4>Chat प्रणाली:</h4>
<p>आपण DCO Officer 1 शी थेट संवाद साधू शकता. हे संदेश प्रणाली आपल्याला कामाच्या प्रवाहात मदत करते.</p>""",

        "officer1": """<h3>DCO Officer 1 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण DCO च्या थेट अधीनस्थ आहात आणि DCO Officer 2 च्या वरिष्ठ आहात. आपण DCO आणि Officer 2 दरम्यान संवादाचा पूल आहात.</p>

<h4>मुख्य जबाबदाऱ्या:</h4>
<ul>
<li>DCO कडून मिळालेल्या कामाचे वितरण Officer 2 ला करणे</li>
<li>Officer 2 कडून मिळालेला डेटा तपासून DCO ला सादर करणे</li>
<li>सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे आणि तपासणे</li>
<li>डेटा वैधता सुनिश्चित करणे</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>आपल्याला सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> बजेट पोस्ट तपशील - जिल्हा, श्रेणी, वर्ग नुसार फिल्टर करा</li>
<li><strong>प्रपत्र क:</strong> पोस्ट स्थिती - भरलेली/रिकामी पोस्ट्सची माहिती</li>
<li><strong>प्रपत्र ब:</strong> पोस्ट खर्च - वैद्यकीय खर्च, NPS, इतर खर्च</li>
<li><strong>प्रपत्र अ:</strong> युनिट खर्च - विविध युनिट खात्यांचा खर्च</li>
</ul>

<h4>संवाद प्रणाली:</h4>
<p>आपण DCO आणि Officer 2 शी Chat प्रणालीद्वारे संवाद साधू शकता. हे आपल्याला कामाच्या प्रवाहात मदत करते.</p>

<h4>AI Assistant:</h4>
<p>डेटा विश्लेषणासाठी AI Assistant वापरा. उदाहरणार्थ: "कोणत्या जिल्ह्यात सर्वाधिक रिकामी पोस्ट्स आहेत?"</p>

<h4>डेटा तपासणी:</h4>
<p>Officer 2 कडून मिळालेला डेटा तपासा, त्रुटी असल्यास त्यांना सुधारण्यास सांगा. डेटा योग्य असल्यास DCO ला सादर करा.</p>""",

        "officer2": """<h3>DCO Officer 2 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण Officer 1 च्या अधीनस्थ आणि Assistant च्या वरिष्ठ आहात. आपण मुख्यतः डेटा प्रविष्टी आणि तपासणीची जबाबदारी बजावता.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 1 कडून मिळालेल्या कामाचे वितरण Assistant ला करणे</li>
<li>Assistant कडून मिळालेला डेटा तपासणे</li>
<li>सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>डेटा वैधता तपासणे</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>सर्व 4 प्रपत्रांमध्ये आपण डेटा प्रविष्ट करू शकता:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> इनलाइन संपादन - सेलवर क्लिक करून मूल्य बदला</li>
<li><strong>प्रपत्र क:</strong> फिल्टर वापरा - जिल्हा, श्रेणी, वर्ग, स्थिती नुसार</li>
<li><strong>प्रपत्र ब:</strong> पृष्ठांकन वापरा - मोठ्या डेटासेटसाठी</li>
<li><strong>प्रपत्र अ:</strong> युनिट खात्यानुसार फिल्टर करा</li>
</ul>

<h4>संवाद:</h4>
<p>आपण Officer 1 आणि Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>डेटा प्रविष्टी टिप्स:</h4>
<ul>
<li>फिल्टर वापरून आवश्यक डेटा शोधा</li>
<li>इनलाइन संपादन वापरा - ते जलद आहे</li>
<li>बदल केल्यानंतर स्वयंचलितपणे सेव्ह होते</li>
<li>त्रुटी असल्यास लाल रंगात दिसते</li>
</ul>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा. उदाहरणार्थ: "प्रपत्र ड मध्ये किती पंक्ती आहेत?"</p>""",

        "assistant": """<h3>DCO Assistant मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण DCO स्तरावरील Assistant आहात. आपली मुख्य जबाबदारी डेटा प्रविष्टी आहे. तसेच आपण जिल्हा स्तरावरील Officer 1 आणि Assistant शी संवाद साधू शकता.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 2 कडून मिळालेल्या कामाची अंमलबजावणी</li>
<li>सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>जिल्हा स्तरावरील अधिकाऱ्यांशी संवाद</li>
<li>डेटा तपासणी</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>आपल्याला सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> बजेट पोस्ट तपशील - जिल्हा निवडून डेटा प्रविष्ट करा</li>
<li><strong>प्रपत्र क:</strong> पोस्ट स्थिती - भरलेली/रिकामी पोस्ट्स</li>
<li><strong>प्रपत्र ब:</strong> पोस्ट खर्च - विविध खर्च प्रविष्ट करा</li>
<li><strong>प्रपत्र अ:</strong> युनिट खर्च - युनिट खात्यानुसार</li>
</ul>

<h4>संवाद प्रणाली:</h4>
<p>आपण Officer 2, जिल्हा Officer 1 आणि जिल्हा Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता. हे आपल्याला जिल्हा स्तराशी जोडण्यात मदत करते.</p>

<h4>डेटा प्रविष्टी:</h4>
<ul>
<li>फिल्टर वापरून योग्य डेटा शोधा</li>
<li>इनलाइन संपादन वापरा</li>
<li>बदल स्वयंचलितपणे सेव्ह होतात</li>
<li>त्रुटी टाळण्यासाठी काळजीपूर्वक प्रविष्ट करा</li>
</ul>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा. उदाहरणार्थ: "कोणत्या जिल्ह्यात सर्वाधिक डेटा प्रविष्ट केला आहे?"</p>"""
    },
    "district": {
        "officer1": """<h3>जिल्हा Officer 1 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण आपल्या जिल्ह्याचे मुख्य अधिकारी आहात. आपल्याकडे आपल्या जिल्ह्याच्या सर्व डेटाची जबाबदारी आहे.</p>

<h4>मुख्य वैशिष्ट्ये:</h4>
<ul>
<li><strong>तालुका निवड:</strong> आपल्या जिल्ह्यातील तालुक्यांची निवड आणि व्यवस्थापन</li>
<li><strong>तालुका वापरकर्ते सक्रियता:</strong> तालुका स्तरावरील वापरकर्त्यांना सक्रिय/निष्क्रिय करणे</li>
<li><strong>जिल्हानिहाय गोषवारा:</strong> आपल्या जिल्ह्याची संपूर्ण माहिती</li>
<li><strong>सूचना:</strong> महत्त्वाच्या सूचना आणि चेतावण्या</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>आपल्याला आपल्या जिल्ह्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> आपल्या जिल्ह्याचा बजेट पोस्ट तपशील</li>
<li><strong>प्रपत्र क:</strong> आपल्या जिल्ह्याची पोस्ट स्थिती</li>
<li><strong>प्रपत्र ब:</strong> आपल्या जिल्ह्याचे पोस्ट खर्च</li>
<li><strong>प्रपत्र अ:</strong> आपल्या जिल्ह्याचा युनिट खर्च</li>
</ul>

<h4>तालुका व्यवस्थापन:</h4>
<ol>
<li>तालुका निवड पृष्ठावर जा</li>
<li>आपल्या जिल्ह्यातील तालुके निवडा</li>
<li>तालुका वापरकर्त्यांना सक्रिय करा</li>
<li>तालुका स्तरावरील डेटा मॉनिटर करा</li>
</ol>

<h4>संवाद:</h4>
<p>आपण Officer 2, Assistant, DCO Assistant आणि तालुका Officer 1 शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>AI Assistant:</h4>
<p>आपल्या जिल्ह्याच्या डेटाचे विश्लेषण करण्यासाठी AI Assistant वापरा. उदाहरणार्थ: "आमच्या जिल्ह्यात एकूण किती रिकामी पोस्ट्स आहेत?"</p>

<h4>सूचना पृष्ठ:</h4>
<p>सूचना पृष्ठावर महत्त्वाच्या चेतावण्या आणि सूचना पहा. हे आपल्याला डेटा भरण्याच्या कालावधीबद्दल माहिती देते.</p>""",

        "officer2": """<h3>जिल्हा Officer 2 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण Officer 1 च्या अधीनस्थ आणि Assistant च्या वरिष्ठ आहात. आपण मुख्यतः डेटा प्रविष्टी आणि तपासणीची जबाबदारी बजावता.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 1 कडून मिळालेल्या कामाचे वितरण Assistant ला करणे</li>
<li>Assistant कडून मिळालेला डेटा तपासणे</li>
<li>आपल्या जिल्ह्यासाठी सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>डेटा वैधता तपासणे</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>आपल्याला आपल्या जिल्ह्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> जिल्हा फिल्टर आधीच सेट केलेला असतो</li>
<li><strong>प्रपत्र क:</strong> श्रेणी, वर्ग, स्थिती नुसार फिल्टर करा</li>
<li><strong>प्रपत्र ब:</strong> पृष्ठांकन वापरा</li>
<li><strong>प्रपत्र अ:</strong> युनिट खात्यानुसार फिल्टर करा</li>
</ul>

<h4>संवाद:</h4>
<p>आपण Officer 1 आणि Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>डेटा प्रविष्टी:</h4>
<ul>
<li>इनलाइन संपादन वापरा - ते जलद आहे</li>
<li>फिल्टर वापरून आवश्यक डेटा शोधा</li>
<li>बदल स्वयंचलितपणे सेव्ह होतात</li>
<li>त्रुटी टाळण्यासाठी काळजीपूर्वक प्रविष्ट करा</li>
</ul>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा. उदाहरणार्थ: "आमच्या जिल्ह्यात कोणत्या श्रेणीत सर्वाधिक पोस्ट्स आहेत?"</p>

<h4>सूचना:</h4>
<p>सूचना पृष्ठावर डेटा भरण्याच्या कालावधीबद्दल माहिती पहा.</p>""",

        "assistant": """<h3>जिल्हा Assistant मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण जिल्हा स्तरावरील Assistant आहात. आपली मुख्य जबाबदारी डेटा प्रविष्टी आहे. <strong>महत्त्वाचे:</strong> आपल्याला फक्त निर्धारित कालावधीत डेटा प्रविष्ट करता येते.</p>

<h4>महत्त्वाची सूचना:</h4>
<p><strong>डेटा भरण्याचा कालावधी:</strong> आपल्याला फक्त DCO द्वारे निर्धारित केलेल्या कालावधीत डेटा प्रविष्ट करता येते. कालावधी संपल्यानंतर आपण डेटा संपादित करू शकत नाही.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 2 कडून मिळालेल्या कामाची अंमलबजावणी</li>
<li>निर्धारित कालावधीत सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>तालुका स्तरावरील अधिकाऱ्यांशी संवाद</li>
<li>तालुका वापरकर्त्यांना सक्रिय करणे</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>कालावधी सक्रिय असताना आपल्याला आपल्या जिल्ह्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> बजेट पोस्ट तपशील</li>
<li><strong>प्रपत्र क:</strong> पोस्ट स्थिती</li>
<li><strong>प्रपत्र ब:</strong> पोस्ट खर्च</li>
<li><strong>प्रपत्र अ:</strong> युनिट खर्च</li>
</ul>

<h4>कालावधी मॉनिटरिंग:</h4>
<ul>
<li>पृष्ठाच्या वरच्या बाजूला Alert Banner पहा</li>
<li>सूचना पृष्ठावर कालावधीची माहिती पहा</li>
<li>कालावधी संपल्यानंतर आपण फक्त डेटा पाहू शकता, संपादित करू शकत नाही</li>
</ul>

<h4>तालुका व्यवस्थापन:</h4>
<ol>
<li>तालुका निवड पृष्ठावर जा</li>
<li>तालुका निवडा</li>
<li>तालुका वापरकर्त्यांना सक्रिय करा</li>
<li>तालुका स्तरावरील डेटा मॉनिटर करा</li>
</ol>

<h4>संवाद:</h4>
<p>आपण Officer 2, DCO Assistant, तालुका Officer 1 आणि तालुका Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा. उदाहरणार्थ: "आमच्या जिल्ह्यात किती तालुके सक्रिय आहेत?"</p>

<h4>टिप्स:</h4>
<ul>
<li>कालावधी सुरू होण्यापूर्वी तयारी करा</li>
<li>कालावधीत सर्व डेटा प्रविष्ट करा</li>
<li>Alert Banner नेहमी पहा</li>
<li>त्रुटी टाळण्यासाठी काळजीपूर्वक प्रविष्ट करा</li>
</ul>"""
    },
    "taluka": {
        "officer1": """<h3>तालुका Officer 1 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण आपल्या तालुक्याचे मुख्य अधिकारी आहात. आपल्याकडे आपल्या तालुक्याच्या सर्व डेटाची जबाबदारी आहे.</p>

<h4>महत्त्वाची सूचना:</h4>
<p><strong>सक्रियता आवश्यक:</strong> आपल्या तालुक्याला जिल्हा Assistant द्वारे सक्रिय केले जाणे आवश्यक आहे. सक्रिय नसल्यास आपण सिस्टम वापरू शकत नाही.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 2 कडून मिळालेल्या कामाचे वितरण Assistant ला करणे</li>
<li>Assistant कडून मिळालेला डेटा तपासणे</li>
<li>आपल्या तालुक्यासाठी सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>जिल्हा Assistant शी संवाद</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>सक्रिय असताना आपल्याला आपल्या तालुक्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> आपल्या तालुक्याचा बजेट पोस्ट तपशील</li>
<li><strong>प्रपत्र क:</strong> आपल्या तालुक्याची पोस्ट स्थिती</li>
<li><strong>प्रपत्र ब:</strong> आपल्या तालुक्याचे पोस्ट खर्च</li>
<li><strong>प्रपत्र अ:</strong> आपल्या तालुक्याचा युनिट खर्च</li>
</ul>

<h4>संवाद:</h4>
<p>आपण Officer 2, Assistant आणि जिल्हा Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>AI Assistant:</h4>
<p>आपल्या तालुक्याच्या डेटाचे विश्लेषण करण्यासाठी AI Assistant वापरा. उदाहरणार्थ: "आमच्या तालुक्यात एकूण किती पोस्ट्स आहेत?"</p>

<h4>सूचना:</h4>
<p>सूचना पृष्ठावर महत्त्वाच्या चेतावण्या आणि सूचना पहा. डेटा भरण्याच्या कालावधीबद्दल माहिती पहा.</p>

<h4>टिप्स:</h4>
<ul>
<li>जिल्हा Assistant शी संवाद साधून आपल्या तालुक्याला सक्रिय करा</li>
<li>सक्रिय झाल्यानंतर लगेच डेटा प्रविष्ट करणे सुरू करा</li>
<li>कालावधी संपण्यापूर्वी सर्व डेटा प्रविष्ट करा</li>
</ul>""",

        "officer2": """<h3>तालुका Officer 2 मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण Officer 1 च्या अधीनस्थ आणि Assistant च्या वरिष्ठ आहात. आपण मुख्यतः डेटा प्रविष्टी आणि तपासणीची जबाबदारी बजावता.</p>

<h4>महत्त्वाची सूचना:</h4>
<p><strong>सक्रियता आवश्यक:</strong> आपल्या तालुक्याला जिल्हा Assistant द्वारे सक्रिय केले जाणे आवश्यक आहे.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 1 कडून मिळालेल्या कामाचे वितरण Assistant ला करणे</li>
<li>Assistant कडून मिळालेला डेटा तपासणे</li>
<li>आपल्या तालुक्यासाठी सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>सक्रिय असताना आपल्याला आपल्या तालुक्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> तालुका फिल्टर आधीच सेट केलेला असतो</li>
<li><strong>प्रपत्र क:</strong> श्रेणी, वर्ग, स्थिती नुसार फिल्टर करा</li>
<li><strong>प्रपत्र ब:</strong> पृष्ठांकन वापरा</li>
<li><strong>प्रपत्र अ:</strong> युनिट खात्यानुसार फिल्टर करा</li>
</ul>

<h4>संवाद:</h4>
<p>आपण Officer 1 आणि Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता.</p>

<h4>डेटा प्रविष्टी:</h4>
<ul>
<li>इनलाइन संपादन वापरा</li>
<li>फिल्टर वापरून आवश्यक डेटा शोधा</li>
<li>बदल स्वयंचलितपणे सेव्ह होतात</li>
<li>त्रुटी टाळण्यासाठी काळजीपूर्वक प्रविष्ट करा</li>
</ul>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा.</p>

<h4>सूचना:</h4>
<p>सूचना पृष्ठावर डेटा भरण्याच्या कालावधीबद्दल माहिती पहा.</p>""",

        "assistant": """<h3>तालुका Assistant मार्गदर्शन</h3>
<p><strong>आपली भूमिका:</strong> आपण तालुका स्तरावरील Assistant आहात. आपली मुख्य जबाबदारी डेटा प्रविष्टी आहे. <strong>महत्त्वाचे:</strong> आपल्याला फक्त निर्धारित कालावधीत डेटा प्रविष्ट करता येते आणि तालुका सक्रिय असणे आवश्यक आहे.</p>

<h4>महत्त्वाची सूचना:</h4>
<p><strong>दोन अटी:</strong></p>
<ol>
<li>आपल्या तालुक्याला जिल्हा Assistant द्वारे सक्रिय केले जाणे आवश्यक आहे</li>
<li>DCO द्वारे निर्धारित केलेल्या कालावधीत आपण डेटा प्रविष्ट करू शकता</li>
</ol>
<p>या दोन्ही अटी पूर्ण झाल्याशिवाय आपण डेटा संपादित करू शकत नाही.</p>

<h4>मुख्य कामे:</h4>
<ul>
<li>Officer 2 कडून मिळालेल्या कामाची अंमलबजावणी</li>
<li>निर्धारित कालावधीत सर्व प्रपत्रांमध्ये डेटा प्रविष्ट करणे</li>
<li>जिल्हा Assistant शी संवाद</li>
</ul>

<h4>प्रपत्र वापर:</h4>
<p>तालुका सक्रिय आणि कालावधी सक्रिय असताना आपल्याला आपल्या तालुक्यासाठी सर्व 4 प्रपत्रांमध्ये संपादन करता येते:</p>
<ul>
<li><strong>प्रपत्र ड:</strong> बजेट पोस्ट तपशील</li>
<li><strong>प्रपत्र क:</strong> पोस्ट स्थिती</li>
<li><strong>प्रपत्र ब:</strong> पोस्ट खर्च</li>
<li><strong>प्रपत्र अ:</strong> युनिट खर्च</li>
</ul>

<h4>कालावधी मॉनिटरिंग:</h4>
<ul>
<li>पृष्ठाच्या वरच्या बाजूला Alert Banner पहा</li>
<li>सूचना पृष्ठावर कालावधीची माहिती पहा</li>
<li>कालावधी संपल्यानंतर आपण फक्त डेटा पाहू शकता</li>
</ul>

<h4>संवाद:</h4>
<p>आपण Officer 2 आणि जिल्हा Assistant शी Chat प्रणालीद्वारे संवाद साधू शकता. जिल्हा Assistant शी संवाद साधून आपल्या तालुक्याला सक्रिय करा.</p>

<h4>AI Assistant:</h4>
<p>डेटा प्रश्नांसाठी AI Assistant वापरा.</p>

<h4>टिप्स:</h4>
<ul>
<li>जिल्हा Assistant शी संवाद साधून आपल्या तालुक्याला सक्रिय करा</li>
<li>कालावधी सुरू होण्यापूर्वी तयारी करा</li>
<li>कालावधीत सर्व डेटा प्रविष्ट करा</li>
<li>Alert Banner नेहमी पहा</li>
<li>त्रुटी टाळण्यासाठी काळजीपूर्वक प्रविष्ट करा</li>
</ul>"""
    }
}

def _get_training_content_for_user(auth_user: str, auth_role: str, auth_level: str, db: Session):
    """Internal function to get training content with caching support."""
    cache_key = f"training_content:{auth_user}:{auth_role}:{auth_level}"
    cached = memory_cache.get(cache_key)
    if cached is not None:
        return cached
    
    if auth_role == 'admin':
        level = 'dco'
        role = 'dco'
    else:
        try:
            user = db.query(models.User).filter(
                models.User.username == auth_user,
                (models.User.level != 'taluka') | (models.User.is_active == True)
            ).first()
            
            if not user:
                if auth_level == 'taluka':
                    raise HTTPException(
                        status_code=403,
                        detail="तालुका वापरकर्ता सक्रिय नाही. कृपया जिल्हा Assistant शी संपर्क साधा."
                    )
                raise HTTPException(status_code=401, detail="Unauthorized")
            
            level = user.level
            role = user.role
        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logging.error(f"Database error in training content for user {auth_user}: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        except Exception as e:
            logging.error(f"Unexpected error in training content for user {auth_user}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    instructions = TRAINING_CONTENT.get(level, {}).get(role)
    if not instructions or instructions == "मार्गदर्शन सामग्री लवकरच उपलब्ध होईल.":
        logging.warning(f"Missing training content: level={level}, role={role}, user={auth_user}")
        instructions = "मार्गदर्शन सामग्री लवकरच उपलब्ध होईल."
    
    result = (level, role, instructions)
    memory_cache.set(cache_key, result, ttl=300)
    return result

def _sanitize_html(html: str) -> str:
    """Basic HTML sanitization - remove script tags and dangerous attributes."""
    if not html:
        return ""
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'on\w+\s*=', '', html, flags=re.IGNORECASE)
    return html

@router.get("/content", response_class=JSONResponse)
async def get_training_content(request: Request, db: Session = Depends(get_db)):
    auth_user = request.cookies.get('auth_user', '')
    auth_role = request.cookies.get('auth_role', '')
    auth_level = request.cookies.get('auth_level', '')
    
    if not auth_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        level, role, instructions = _get_training_content_for_user(auth_user, auth_role, auth_level, db)
        instructions = _sanitize_html(instructions)
        video_url = ""
        
        return JSONResponse({
            "level": level,
            "role": role,
            "video_url": video_url,
            "instructions": instructions
        }, headers={
            "Cache-Control": "public, max-age=3600"
        })
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in get_training_content for user {auth_user}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

