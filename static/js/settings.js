(function() {
    const form = document.getElementById('settings-form');
    const messageContainer = document.getElementById('message-container');
    const saveBtn = document.getElementById('save-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const phoneInput = document.getElementById('phone_number');
    
    // Extract scheme code from URL path (supports 4-8 digit codes, e.g., /ui/s62450017/settings or /ui/s2215/settings)
    function getSchemeCode() {
        const match = window.location.pathname.match(/\/ui\/s(\d{4,8})\//);
        return match ? match[1] : null;
    }
    
    function getApiBasePath() {
        const schemeCode = getSchemeCode();
        return schemeCode ? `/ui/s${schemeCode}/settings` : '/settings';
    }
    
    function showMessage(message, type = 'success') {
        messageContainer.textContent = message;
        messageContainer.style.display = 'block';
        messageContainer.style.background = type === 'success' ? '#d1fae5' : '#fee2e2';
        messageContainer.style.color = type === 'success' ? '#065f46' : '#991b1b';
        messageContainer.style.border = `1px solid ${type === 'success' ? '#10b981' : '#ef4444'}`;
        
        setTimeout(() => {
            messageContainer.style.display = 'none';
        }, 5000);
    }
    
    function validateEmail(email) {
        const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return pattern.test(email);
    }
    
    function validatePhone(phone) {
        if (!phone) return true;
        const cleaned = phone.replace(/\D/g, '');
        return cleaned.length === 10;
    }
    
    function formatPhoneDisplay(phone) {
        const cleaned = phone.replace(/\D/g, '').slice(0, 10);
        if (cleaned.length === 0) return '';
        if (cleaned.length <= 5) return cleaned;
        return `${cleaned.slice(0, 5)} ${cleaned.slice(5)}`;
    }
    
    function getPhoneDigits(phone) {
        return phone.replace(/\D/g, '').slice(0, 10);
    }
    
    async function loadSettings() {
        try {
            const response = await fetch(`${getApiBasePath()}/profile`);
            if (!response.ok) throw new Error('Failed to load settings');
            
            const data = await response.json();
            
            document.getElementById('email').value = data.email || '';
            const phoneNumber = data.phone_number || '';
            const phoneDigits = getPhoneDigits(phoneNumber);
            if (phoneDigits.length === 10) {
                phoneInput.value = formatPhoneDisplay(phoneDigits);
            } else if (phoneDigits.length > 0) {
                phoneInput.value = phoneDigits;
            } else {
                phoneInput.value = '';
            }
            phoneInput.setCustomValidity('');
            document.getElementById('pref_data_filling_period').checked = data.notification_preferences?.data_filling_period !== false;
            document.getElementById('pref_taluka_activation').checked = data.notification_preferences?.taluka_activation !== false;
            document.getElementById('pref_fiscal_year_changes').checked = data.notification_preferences?.fiscal_year_changes !== false;
        } catch (error) {
            console.error('Error loading settings:', error);
            showMessage('सेटिंग्ज लोड करताना त्रुटी / Error loading settings', 'error');
        }
    }
    
    phoneInput.addEventListener('input', (e) => {
        const digits = getPhoneDigits(e.target.value);
        if (digits.length <= 10) {
            e.target.value = formatPhoneDisplay(digits);
        } else {
            e.target.value = formatPhoneDisplay(digits.slice(0, 10));
        }
        e.target.setCustomValidity('');
    });
    
    phoneInput.addEventListener('keydown', (e) => {
        const digits = getPhoneDigits(phoneInput.value);
        if (digits.length >= 10 && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Home', 'End'].includes(e.key) && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
        }
    });
    
    phoneInput.addEventListener('paste', (e) => {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const digits = getPhoneDigits(pastedText).slice(0, 10);
        phoneInput.value = formatPhoneDisplay(digits);
        phoneInput.setCustomValidity('');
    });
    
    phoneInput.addEventListener('focus', (e) => {
        const digits = getPhoneDigits(e.target.value);
        e.target.value = digits;
        e.target.setCustomValidity('');
    });
    
    phoneInput.addEventListener('blur', (e) => {
        const digits = getPhoneDigits(e.target.value);
        if (digits.length === 10) {
            e.target.value = formatPhoneDisplay(digits);
            e.target.setCustomValidity('');
        } else if (digits.length > 0 && digits.length < 10) {
            e.target.value = digits;
            e.target.setCustomValidity('कृपया 10 अंक प्रविष्ट करा / Please enter 10 digits');
        } else {
            e.target.setCustomValidity('');
        }
    });
    
    phoneInput.addEventListener('invalid', (e) => {
        const digits = getPhoneDigits(e.target.value);
        if (digits.length > 0 && digits.length !== 10) {
            e.target.setCustomValidity('कृपया 10 अंक प्रविष्ट करा / Please enter 10 digits');
        } else {
            e.target.setCustomValidity('');
        }
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        const phoneNumberRaw = phoneInput.value.trim();
        const phoneNumber = getPhoneDigits(phoneNumberRaw);
        const dataFillingPeriod = document.getElementById('pref_data_filling_period').checked;
        const talukaActivation = document.getElementById('pref_taluka_activation').checked;
        const fiscalYearChanges = document.getElementById('pref_fiscal_year_changes').checked;
        
        if (email && !validateEmail(email)) {
            showMessage('अवैध ईमेल पत्ता / Invalid email address', 'error');
            return;
        }
        
        if (phoneNumber && phoneNumber.length > 0 && !validatePhone(phoneNumber)) {
            showMessage('अवैध फोन नंबर (10 अंक आवश्यक) / Invalid phone number (10 digits required)', 'error');
            phoneInput.setCustomValidity('कृपया 10 अंक प्रविष्ट करा / Please enter 10 digits');
            phoneInput.reportValidity();
            phoneInput.focus();
            return;
        }
        
        phoneInput.setCustomValidity('');
        
        const formData = new FormData();
        formData.append('email', email || '');
        formData.append('phone_number', phoneNumber || '');
        formData.append('data_filling_period', dataFillingPeriod ? 'true' : 'false');
        formData.append('taluka_activation', talukaActivation ? 'true' : 'false');
        formData.append('fiscal_year_changes', fiscalYearChanges ? 'true' : 'false');
        
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.textContent = 'सेव्ह करत आहे... / Saving...';
        saveBtn.style.opacity = '0.7';
        
        try {
            const response = await fetch(`${getApiBasePath()}/profile`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showMessage(data.message || 'सेटिंग्ज यशस्वीरित्या अपडेट केले / Settings updated successfully', 'success');
                if (phoneNumber.length === 10) {
                    phoneInput.value = formatPhoneDisplay(phoneNumber);
                }
            } else {
                showMessage(data.detail || 'त्रुटी / Error', 'error');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            showMessage('सेटिंग्ज सेव्ह करताना त्रुटी / Error saving settings', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
            saveBtn.style.opacity = '1';
        }
    });
    
    cancelBtn.addEventListener('click', () => {
        loadSettings();
    });
    
    loadSettings();
})();
