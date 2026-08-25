/**
 * Post Levels Manager - Multi-level data entry for budget posts
 */
class PostLevelsManager {
    constructor(config) {
        this.budgetPostId = config.budgetPostId;
        this.apiBasePath = config.apiBasePath;
        this.payMatrixApiPath = config.payMatrixApiPath;
        this.subSchemeCode = config.subSchemeCode;
        this.tableName = config.tableName;
        this.fiscalYear = config.fiscalYear;
        
        this.DA_RATE = 0.64; // Default, will be updated from API
        this.HRA_RATES = { 'X': 0.30, 'Y': 0.20, 'Z': 0.10 };
        this.maxAllowed = config.maxLevelsAllowed || 0;
        this.currentCount = 0;
        this.levels = [];
        this.editingLevelId = null;
        this.fieldPrevValues = {}; // Track previous values for annual mode
        
        this.init();
    }
    
    async init() {
        this.bindEvents();
        await this.loadDaRate();
        await this.loadPayMatrixStages();
        await this.loadLevels(false);
        await this.loadLimitInfo();
    }
    
    async loadLimitInfo() {
        try {
            const res = await fetch(
                `${this.apiBasePath}/${this.budgetPostId}/limit-info`,
                { cache: 'no-store' }
            );
            if (!res.ok) return;
            const data = await res.json();
            this.maxAllowed = data.max_allowed || 0;
            this.currentCount = data.current_count || 0;
            this.updateAddButtonState();
        } catch (e) {
            console.error('Failed to load limit info:', e);
        }
    }
    
    updateAddButtonState() {
        const btn = document.getElementById('addLevelBtn');
        if (!btn) return;
        
        if (this.maxAllowed <= 0) {
            btn.textContent = '+ स्तर जोडा (मंजूर पदे भरा)';
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.title = 'कृपया प्रथम मंजूर पदे भरा';
            return;
        }
        
        const remaining = this.maxAllowed - this.levels.length;
        btn.textContent = `+ स्तर जोडा (${this.levels.length}/${this.maxAllowed})`;
        
        if (remaining <= 0) {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.title = `मंजूर पदे मर्यादा (${this.maxAllowed}) पूर्ण झाली`;
        } else {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
            btn.title = `${remaining} स्तर अजून जोडता येतील`;
        }
    }
    
    async loadDaRate() {
        try {
            const apiPath = this.apiBasePath.replace('/api/post-levels', '');
            const res = await fetch(`${apiPath}/api/da-rate`, { cache: 'no-store' });
            if (!res.ok) {
                console.warn('Failed to load DA rate, using default 64%');
                return;
            }
            const data = await res.json();
            if (data.da_rate !== undefined && data.da_rate !== null) {
                this.DA_RATE = data.da_rate;
                console.log(`DA rate loaded: ${(this.DA_RATE * 100).toFixed(2)}%`);
            }
        } catch (e) {
            console.error('Failed to load DA rate, using default 64%:', e);
        }
    }
    
    isAnnualMode() {
        return document.getElementById('annualModeToggle')?.checked ?? true;
    }
    
    bindEvents() {
        document.getElementById('addLevelBtn')?.addEventListener('click', () => this.showAddForm());
        document.getElementById('saveLevelBtn')?.addEventListener('click', () => this.saveLevel());
        document.getElementById('cancelLevelBtn')?.addEventListener('click', () => this.hideForm());
        document.getElementById('levelPayStage')?.addEventListener('change', () => this.onPayStageChange());
        document.getElementById('levelPayLevel')?.addEventListener('change', () => this.onPayLevelChange());
        document.getElementById('levelGradePay')?.addEventListener('input', () => this.recalcAllowances());
        document.getElementById('levelHraRate')?.addEventListener('change', () => this.recalcAllowances());
        
        // Apply multiplier on blur for salary fields (like s20530019)
        document.querySelectorAll('.salary-field').forEach(field => {
            field.addEventListener('blur', () => this.applyMultiplierOnBlur(field));
        });
    }
    
    applyMultiplierOnBlur(input) {
        if (!this.isAnnualMode()) return;
        
        const val = parseFloat(input.value) || 0;
        const prevVal = this.fieldPrevValues[input.id] || 0;
        
        // Only multiply if value changed and not already multiplied
        if (val === 0 || val === prevVal) return;
        
        const newVal = Math.round(val * 12);
        input.value = newVal;
        this.fieldPrevValues[input.id] = newVal;
        this.recalcAllowances();
        
        if (typeof showNotification === 'function') {
            showNotification(`वार्षिक: ${val} × 12 = ${newVal}`, 'info');
        }
    }
    
    async loadPayMatrixStages() {
        try {
            const res = await fetch(`${this.payMatrixApiPath}/stages`, { cache: 'no-store' });
            const data = await res.json();
            const select = document.getElementById('levelPayStage');
            if (select && data.stages) {
                select.innerHTML = '<option value="">-- श्रेणी निवडा --</option>' +
                    data.stages.map(s => `<option value="${s}">${s}</option>`).join('');
            }
        } catch (e) {
            console.error('Failed to load pay stages:', e);
        }
    }
    
    async onPayStageChange() {
        const stage = document.getElementById('levelPayStage').value;
        const levelSelect = document.getElementById('levelPayLevel');
        
        if (!stage) {
            levelSelect.innerHTML = '<option value="">-- स्तर निवडा --</option>';
            levelSelect.disabled = true;
            return;
        }
        
        try {
            const res = await fetch(`${this.payMatrixApiPath}/levels/${encodeURIComponent(stage)}`, { cache: 'no-store' });
            const data = await res.json();
            levelSelect.innerHTML = '<option value="">-- स्तर निवडा --</option>' +
                (data.levels || []).map(l => `<option value="${l}">${l}</option>`).join('');
            levelSelect.disabled = false;
        } catch (e) {
            console.error('Failed to load pay levels:', e);
        }
    }
    
    async onPayLevelChange() {
        const stage = document.getElementById('levelPayStage').value;
        const level = document.getElementById('levelPayLevel').value;
        if (!stage || !level) return;
        
        try {
            const res = await fetch(`${this.payMatrixApiPath}/basic-pay?stage=${encodeURIComponent(stage)}&level=${encodeURIComponent(level)}`, { cache: 'no-store' });
            const data = await res.json();
            
            if (data.found && data.basic_pay_full) {
                // Apply annual multiplier to pay matrix value if annual mode is ON
                const baseValue = data.basic_pay_full;
                const finalValue = this.isAnnualMode() ? baseValue * 12 : baseValue;
                const thousands = Math.round(finalValue / 1000);
                
                document.getElementById('levelBasicPay').value = thousands;
                this.fieldPrevValues['levelBasicPay'] = thousands;
                this.recalcAllowances();
                
                const modeLabel = this.isAnnualMode() ? ' (वार्षिक)' : ' (मासिक)';
                if (typeof showNotification === 'function') {
                    showNotification(`मुळ वेतन: ₹${finalValue.toLocaleString('en-IN')}${modeLabel}`, 'success');
                }
            }
        } catch (e) {
            console.error('Failed to load basic pay:', e);
        }
    }
    
    recalcAllowances() {
        const basicPay = parseFloat(document.getElementById('levelBasicPay')?.value) || 0;
        const gradePay = parseFloat(document.getElementById('levelGradePay')?.value) || 0;
        const hraRate = document.getElementById('levelHraRate')?.value || 'X';
        
        const base = basicPay + gradePay;
        const da = Math.round(base * this.DA_RATE);
        const hra = Math.round(base * this.HRA_RATES[hraRate]);
        
        document.getElementById('levelDaDisplay').value = da;
        document.getElementById('levelHraDisplay').value = hra;
    }
    
    async loadLevels(persist = true) {
        try {
            const res = await fetch(`${this.apiBasePath}/${this.budgetPostId}`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to load');
            this.levels = await res.json();
            this.renderLevels();
            this.updatePreview();
            this.updateAddButtonState();
            await this.syncMainForm(persist);
        } catch (e) {
            console.error('Failed to load levels:', e);
            this.levels = [];
            this.renderLevels();
            this.updatePreview();
        }
    }
    
    renderLevels() {
        const tbody = document.getElementById('levelsTableBody');
        if (!tbody) return;
        
        if (!this.levels.length) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:20px;">स्तर नाहीत. स्तर जोडण्यासाठी "+ स्तर जोडा" क्लिक करा.</td></tr>';
            return;
        }
        
        tbody.innerHTML = this.levels.map(l => `
            <tr>
                <td>${l.level_order}</td>
                <td>${this.escapeHtml(l.level_name)}</td>
                <td>${l.pay_stage || '-'} / ${l.pay_level || '-'}</td>
                <td>${l.basic_pay}</td>
                <td>${l.grade_pay}</td>
                <td>${l.dearness_allowance}</td>
                <td>${l.hra_amount} (${l.hra_rate})</td>
                <td>${l.vehicle_allowance}</td>
                <td><strong>${l.total}</strong></td>
                <td>
                    <button type="button" onclick="postLevelsManager.editLevel(${l.id})" class="btn-edit">संपादन</button>
                    <button type="button" onclick="postLevelsManager.deleteLevel(${l.id})" class="btn-delete">हटवा</button>
                </td>
            </tr>
        `).join('');
    }
    
    getNextLevelOrder() {
        if (!this.levels.length) return 1;
        return Math.max(...this.levels.map(l => l.level_order)) + 1;
    }
    
    showAddForm() {
        if (this.maxAllowed <= 0) {
            const msg = 'कृपया प्रथम मंजूर पदे भरा. मंजूर पदे 0 असताना स्तर जोडता येत नाहीत.';
            alert(msg);
            if (typeof showNotification === 'function') {
                showNotification(msg, 'error');
            }
            return;
        }
        if (this.levels.length >= this.maxAllowed) {
            const msg = `मंजूर पदे मर्यादा (${this.maxAllowed}) पूर्ण झाली आहे.\nआणखी स्तर जोडता येणार नाहीत.`;
            alert(msg);
            if (typeof showNotification === 'function') {
                showNotification(msg, 'error');
            }
            return;
        }
        this.editingLevelId = null;
        this.resetForm();
        document.getElementById('levelOrder').value = this.getNextLevelOrder();
        document.getElementById('levelFormSection').style.display = 'block';
        document.getElementById('levelFormSection').scrollIntoView({ behavior: 'smooth' });
    }
    
    async editLevel(id) {
        const level = this.levels.find(l => l.id === id);
        if (!level) return;
        
        this.editingLevelId = id;
        
        // Set form values
        document.getElementById('levelName').value = level.level_name || '';
        document.getElementById('levelOrder').value = level.level_order;
        document.getElementById('levelSpecialPay').value = level.special_pay || 0;
        document.getElementById('levelBasicPay').value = level.basic_pay || 0;
        document.getElementById('levelGradePay').value = level.grade_pay || 0;
        document.getElementById('levelLocalAllowance').value = level.local_supplementary_allowance || 0;
        document.getElementById('levelVehicleAllowance').value = level.vehicle_allowance || 0;
        document.getElementById('levelWashingAllowance').value = level.washing_allowance || 0;
        document.getElementById('levelCashAllowance').value = level.cash_allowance || 0;
        document.getElementById('levelFootwearAllowance').value = level.footwear_allowance_other || 0;
        document.getElementById('levelHraRate').value = level.hra_rate || 'X';
        document.getElementById('levelPayStage').value = level.pay_stage || '';
        
        // Store previous values to prevent re-multiplication
        this.fieldPrevValues = {
            'levelSpecialPay': level.special_pay || 0,
            'levelBasicPay': level.basic_pay || 0,
            'levelGradePay': level.grade_pay || 0,
            'levelLocalAllowance': level.local_supplementary_allowance || 0,
            'levelVehicleAllowance': level.vehicle_allowance || 0,
            'levelWashingAllowance': level.washing_allowance || 0,
            'levelCashAllowance': level.cash_allowance || 0,
            'levelFootwearAllowance': level.footwear_allowance_other || 0
        };
        
        // Load pay levels if stage is set
        const levelSelect = document.getElementById('levelPayLevel');
        if (level.pay_stage) {
            await this.onPayStageChange();
            levelSelect.value = level.pay_level || '';
        } else {
            levelSelect.innerHTML = '<option value="">-- स्तर निवडा --</option>';
            levelSelect.disabled = true;
        }
        
        this.recalcAllowances();
        document.getElementById('levelFormSection').style.display = 'block';
        document.getElementById('levelFormSection').scrollIntoView({ behavior: 'smooth' });
    }
    
    resetForm() {
        document.getElementById('levelName').value = '';
        document.getElementById('levelOrder').value = 1;
        document.getElementById('levelPayStage').value = '';
        document.getElementById('levelPayLevel').innerHTML = '<option value="">-- स्तर निवडा --</option>';
        document.getElementById('levelPayLevel').disabled = true;
        document.getElementById('levelSpecialPay').value = 0;
        document.getElementById('levelBasicPay').value = 0;
        document.getElementById('levelGradePay').value = 0;
        document.getElementById('levelLocalAllowance').value = 0;
        document.getElementById('levelVehicleAllowance').value = 0;
        document.getElementById('levelWashingAllowance').value = 0;
        document.getElementById('levelCashAllowance').value = 0;
        document.getElementById('levelFootwearAllowance').value = 0;
        document.getElementById('levelHraRate').value = 'X';
        document.getElementById('levelDaDisplay').value = 0;
        document.getElementById('levelHraDisplay').value = 0;
        this.fieldPrevValues = {};
    }
    
    hideForm() {
        document.getElementById('levelFormSection').style.display = 'none';
        this.editingLevelId = null;
    }
    
    async saveLevel() {
        const name = document.getElementById('levelName').value.trim();
        if (!name) {
            alert('कृपया स्तराचे नाव प्रविष्ट करा');
            return;
        }
        
        // All values are already annual (multiplied on blur) so save as-is
        const data = {
            budget_post_id: this.budgetPostId,
            sub_scheme_code: this.subSchemeCode,
            table_name: this.tableName,
            level_name: name,
            level_order: parseInt(document.getElementById('levelOrder').value) || this.getNextLevelOrder(),
            pay_stage: document.getElementById('levelPayStage').value || null,
            pay_level: parseInt(document.getElementById('levelPayLevel').value) || null,
            special_pay: parseInt(document.getElementById('levelSpecialPay').value) || 0,
            basic_pay: parseFloat(document.getElementById('levelBasicPay').value) || 0,
            grade_pay: parseInt(document.getElementById('levelGradePay').value) || 0,
            local_supplementary_allowance: parseInt(document.getElementById('levelLocalAllowance').value) || 0,
            vehicle_allowance: parseInt(document.getElementById('levelVehicleAllowance').value) || 0,
            washing_allowance: parseInt(document.getElementById('levelWashingAllowance').value) || 0,
            cash_allowance: parseInt(document.getElementById('levelCashAllowance').value) || 0,
            footwear_allowance_other: parseInt(document.getElementById('levelFootwearAllowance').value) || 0,
            hra_rate: document.getElementById('levelHraRate').value || 'X'
        };
        
        try {
            const url = this.editingLevelId ? `${this.apiBasePath}/${this.editingLevelId}` : this.apiBasePath;
            const method = this.editingLevelId ? 'PUT' : 'POST';
            
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                cache: 'no-store'
            });
            
            if (!res.ok) {
                const err = await res.json();
                if (res.status === 409) {
                    await this.loadLimitInfo();
                }
                throw new Error(err.detail || 'जतन अयशस्वी');
            }
            
            this.hideForm();
            await this.loadLevels();
            
            if (typeof showNotification === 'function') {
                showNotification('स्तर जतन केले', 'success');
            }
        } catch (e) {
            alert(e.message);
        }
    }
    
    async deleteLevel(id) {
        if (!confirm('हे स्तर हटवायचे आहे का?')) return;
        
        try {
            const res = await fetch(`${this.apiBasePath}/${id}`, { 
                method: 'DELETE',
                cache: 'no-store'
            });
            if (!res.ok) throw new Error('Delete failed');
            
            await this.loadLevels();
            await this.loadLimitInfo();
            
            if (typeof showNotification === 'function') {
                showNotification('स्तर हटवले', 'success');
            }
        } catch (e) {
            alert('स्तर हटवताना त्रुटी');
        }
    }
    
    updatePreview() {
        const preview = document.getElementById('aggregatePreview');
        if (!preview) return;
        
        if (!this.levels.length) {
            preview.innerHTML = '<strong>एकूण स्तर:</strong> 0 | <strong>मुळ वेतन:</strong> 0 | <strong>एकूण:</strong> 0';
            return;
        }
        
        const totals = this.levels.reduce((acc, l) => ({
            basic: acc.basic + (l.basic_pay || 0),
            total: acc.total + (l.total || 0)
        }), { basic: 0, total: 0 });
        
        const limitText = this.maxAllowed > 0 
            ? ` | <strong>मर्यादा:</strong> ${this.levels.length}/${this.maxAllowed}`
            : ' | <strong style="color:var(--danger,#dc2626)">⚠ मंजूर पदे भरा</strong>';
            
        preview.innerHTML = `<strong>एकूण स्तर:</strong> ${this.levels.length}${limitText} | <strong>मुळ वेतन:</strong> ${totals.basic} | <strong>एकूण:</strong> ${totals.total}`;
    }
    
    updateMaxAllowed(newMax) {
        this.maxAllowed = parseInt(newMax) || 0;
        this.updateAddButtonState();
        this.updatePreview();
    }
    
    async syncMainForm(persist) {
        try {
            const endpoint = persist ? 'apply-aggregates' : 'aggregates';
            const options = persist
                ? { method: 'POST', cache: 'no-store' }
                : { cache: 'no-store' };
            const res = await fetch(
                `${this.apiBasePath}/${this.budgetPostId}/${endpoint}`,
                options
            );
            if (!res.ok) return;
            
            const result = await res.json();
            const agg = persist ? result.aggregates : result;
            
            // Update main form fields
            this.setField('SpecialPay', agg.special_pay);
            this.setField('BasicPay', agg.basic_pay);
            this.setField('GradePay', agg.grade_pay);
            this.setField('LocalSupplemetoryAllowance', agg.local_supplementary_allowance);
            this.setField('VehicleAllowance', agg.vehicle_allowance);
            this.setField('WashingAllowance', agg.washing_allowance);
            this.setField('CashAllowance', agg.cash_allowance);
            this.setField('FootWareAllowanceOther', agg.footwear_allowance_other);
            this.setField('Da64', agg.dearness_allowance);
            this.setField('Hra', agg.hra_total);
        } catch (e) {
            console.error('Failed to sync main form:', e);
        }
    }
    
    setField(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value ?? 0;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

let postLevelsManager = null;
