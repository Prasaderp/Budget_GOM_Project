/**
 * Post Levels Manager - JavaScript module for managing multi-level data entry
 * Handles CRUD operations, salary calculations, and aggregation for budget post levels
 */

class PostLevelsManager {
    constructor(config) {
        this.budgetPostId = config.budgetPostId;
        this.apiBasePath = config.apiBasePath || '/ui/s20530028/budget-post-details/api/post-levels';
        this.payMatrixApiPath = config.payMatrixApiPath || '/ui/s20530028/budget-post-details/api/pay-matrix';
        this.onAggregateApplied = config.onAggregateApplied || (() => {});
        
        // Constants
        this.DA_RATE = 0.64;
        this.HRA_RATES = { 'X': 0.30, 'Y': 0.20, 'Z': 0.10 };
        
        // State
        this.levels = [];
        this.editingLevelId = null;
        
        this.init();
    }
    
    async init() {
        this.bindEvents();
        await this.loadPayMatrixStages();
        await this.loadLevels();
    }
    
    bindEvents() {
        // Add level button
        const addBtn = document.getElementById('addLevelBtn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showLevelForm());
        }
        
        // Save level button
        const saveBtn = document.getElementById('saveLevelBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveLevel());
        }
        
        // Cancel level button
        const cancelBtn = document.getElementById('cancelLevelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideLevelForm());
        }
        
        // Apply aggregates button
        const applyBtn = document.getElementById('applyAggregatesBtn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyAggregates());
        }
        
        // Pay stage/level dropdowns
        const stageSelect = document.getElementById('levelPayStage');
        const levelSelect = document.getElementById('levelPayLevel');
        
        if (stageSelect) {
            stageSelect.addEventListener('change', () => this.onPayStageChange());
        }
        
        if (levelSelect) {
            levelSelect.addEventListener('change', () => this.onPayLevelChange());
        }
        
        // Salary fields for real-time calculation
        const basicPayInput = document.getElementById('levelBasicPay');
        const gradePayInput = document.getElementById('levelGradePay');
        const hraRateSelect = document.getElementById('levelHraRate');
        
        if (basicPayInput) basicPayInput.addEventListener('input', () => this.calculateAllowances());
        if (gradePayInput) gradePayInput.addEventListener('input', () => this.calculateAllowances());
        if (hraRateSelect) hraRateSelect.addEventListener('change', () => this.calculateAllowances());
    }
    
    async loadPayMatrixStages() {
        try {
            const response = await fetch(`${this.payMatrixApiPath}/stages`);
            const data = await response.json();
            
            const stageSelect = document.getElementById('levelPayStage');
            if (stageSelect && data.stages) {
                stageSelect.innerHTML = '<option value="">-- श्रेणी निवडा --</option>';
                data.stages.forEach(stage => {
                    stageSelect.innerHTML += `<option value="${stage}">${stage}</option>`;
                });
            }
        } catch (error) {
            console.error('Failed to load pay matrix stages:', error);
        }
    }
    
    async onPayStageChange() {
        const stageSelect = document.getElementById('levelPayStage');
        const levelSelect = document.getElementById('levelPayLevel');
        const stage = stageSelect.value;
        
        if (!stage) {
            levelSelect.innerHTML = '<option value="">-- स्तर निवडा --</option>';
            levelSelect.disabled = true;
            return;
        }
        
        try {
            const response = await fetch(`${this.payMatrixApiPath}/levels/${encodeURIComponent(stage)}`);
            const data = await response.json();
            
            levelSelect.innerHTML = '<option value="">-- स्तर निवडा --</option>';
            if (data.levels) {
                data.levels.forEach(level => {
                    levelSelect.innerHTML += `<option value="${level}">${level}</option>`;
                });
            }
            levelSelect.disabled = false;
        } catch (error) {
            console.error('Failed to load pay matrix levels:', error);
        }
    }
    
    async onPayLevelChange() {
        const stageSelect = document.getElementById('levelPayStage');
        const levelSelect = document.getElementById('levelPayLevel');
        const basicPayInput = document.getElementById('levelBasicPay');
        
        const stage = stageSelect.value;
        const level = levelSelect.value;
        
        if (!stage || !level) return;
        
        try {
            const response = await fetch(
                `${this.payMatrixApiPath}/basic-pay?stage=${encodeURIComponent(stage)}&level=${encodeURIComponent(level)}`
            );
            const data = await response.json();
            
            if (data.found && data.basic_pay) {
                basicPayInput.value = data.basic_pay;
                this.calculateAllowances();
                
                if (typeof showNotification === 'function') {
                    showNotification(`मुळ वेतन: ₹${data.basic_pay_full?.toLocaleString('en-IN')}`, 'success');
                }
            }
        } catch (error) {
            console.error('Failed to load basic pay:', error);
        }
    }
    
    calculateAllowances() {
        const basicPay = parseFloat(document.getElementById('levelBasicPay')?.value || 0);
        const gradePay = parseFloat(document.getElementById('levelGradePay')?.value || 0);
        const hraRate = document.getElementById('levelHraRate')?.value || 'X';
        
        const base = basicPay + gradePay;
        const da = Math.round(base * this.DA_RATE);
        const hra = Math.round(base * this.HRA_RATES[hraRate]);
        
        const daDisplay = document.getElementById('levelDaDisplay');
        const hraDisplay = document.getElementById('levelHraDisplay');
        
        if (daDisplay) daDisplay.value = da;
        if (hraDisplay) hraDisplay.value = hra;
    }
    
    async loadLevels() {
        try {
            const response = await fetch(`${this.apiBasePath}/${this.budgetPostId}`);
            if (!response.ok) throw new Error('Failed to load levels');
            
            this.levels = await response.json();
            this.renderLevels();
            await this.updateAggregatePreview();
        } catch (error) {
            console.error('Failed to load levels:', error);
            if (typeof showNotification === 'function') {
                showNotification('स्तर लोड करताना त्रुटी', 'error');
            }
        }
    }
    
    renderLevels() {
        const tbody = document.getElementById('levelsTableBody');
        if (!tbody) return;
        
        if (this.levels.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;">स्तर उपलब्ध नाहीत</td></tr>';
            return;
        }
        
        tbody.innerHTML = this.levels.map(level => `
            <tr>
                <td>${level.level_order}</td>
                <td>${this.escapeHtml(level.level_name)}</td>
                <td>${level.pay_stage || '-'} / ${level.pay_level || '-'}</td>
                <td>${level.basic_pay || 0}</td>
                <td>${level.grade_pay || 0}</td>
                <td>${level.dearness_allowance || 0}</td>
                <td>${level.hra_amount || 0} (${level.hra_rate})</td>
                <td>${level.vehicle_allowance || 0}</td>
                <td>${level.total || 0}</td>
                <td>
                    <button onclick="postLevelsManager.editLevel(${level.id})" class="btn-edit">संपादन</button>
                    <button onclick="postLevelsManager.deleteLevel(${level.id})" class="btn-delete">हटवा</button>
                </td>
            </tr>
        `).join('');
    }
    
    showLevelForm(level = null) {
        this.editingLevelId = level?.id || null;
        const form = document.getElementById('levelFormSection');
        if (!form) return;
        
        // Reset form
        document.getElementById('levelName').value = level?.level_name || '';
        document.getElementById('levelOrder').value = level?.level_order || (this.levels.length + 1);
        document.getElementById('levelPayStage').value = level?.pay_stage || '';
        document.getElementById('levelPayLevel').value = level?.pay_level || '';
        document.getElementById('levelSpecialPay').value = level?.special_pay || 0;
        document.getElementById('levelBasicPay').value = level?.basic_pay || 0;
        document.getElementById('levelGradePay').value = level?.grade_pay || 0;
        document.getElementById('levelLocalAllowance').value = level?.local_supplementary_allowance || 0;
        document.getElementById('levelVehicleAllowance').value = level?.vehicle_allowance || 0;
        document.getElementById('levelWashingAllowance').value = level?.washing_allowance || 0;
        document.getElementById('levelCashAllowance').value = level?.cash_allowance || 0;
        document.getElementById('levelFootwearAllowance').value = level?.footwear_allowance_other || 0;
        document.getElementById('levelHraRate').value = level?.hra_rate || 'X';
        
        if (level?.pay_stage) {
            this.onPayStageChange();
        }
        
        this.calculateAllowances();
        form.style.display = 'block';
    }
    
    hideLevelForm() {
        const form = document.getElementById('levelFormSection');
        if (form) form.style.display = 'none';
        this.editingLevelId = null;
    }
    
    async saveLevel() {
        const levelData = {
            budget_post_id: this.budgetPostId,
            sub_scheme_code: '20530028',
            table_name: 'budget_post_details_20530028',
            level_name: document.getElementById('levelName').value.trim(),
            level_order: parseInt(document.getElementById('levelOrder').value) || 1,
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
        
        if (!levelData.level_name) {
            if (typeof showNotification === 'function') {
                showNotification('कृपया स्तराचे नाव प्रविष्ट करा', 'error');
            }
            return;
        }
        
        try {
            let response;
            if (this.editingLevelId) {
                // Update existing
                response = await fetch(`${this.apiBasePath}/${this.editingLevelId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(levelData)
                });
            } else {
                // Create new
                response = await fetch(`${this.apiBasePath}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(levelData)
                });
            }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save level');
            }
            
            await this.loadLevels();
            this.hideLevelForm();
            
            if (typeof showNotification === 'function') {
                showNotification('स्तर यशस्वीरित्या जतन केले', 'success');
            }
        } catch (error) {
            console.error('Failed to save level:', error);
            if (typeof showNotification === 'function') {
                showNotification(error.message || 'स्तर जतन करताना त्रुटी', 'error');
            }
        }
    }
    
    editLevel(levelId) {
        const level = this.levels.find(l => l.id === levelId);
        if (level) {
            this.showLevelForm(level);
        }
    }
    
    async deleteLevel(levelId) {
        if (!confirm('हे स्तर हटवायचे आहे का?')) return;
        
        try {
            const response = await fetch(`${this.apiBasePath}/${levelId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) throw new Error('Failed to delete level');
            
            await this.loadLevels();
            
            if (typeof showNotification === 'function') {
                showNotification('स्तर हटवले', 'success');
            }
        } catch (error) {
            console.error('Failed to delete level:', error);
            if (typeof showNotification === 'function') {
                showNotification('स्तर हटवताना त्रुटी', 'error');
            }
        }
    }
    
    async updateAggregatePreview() {
        try {
            const response = await fetch(`${this.apiBasePath}/${this.budgetPostId}/aggregates`);
            if (!response.ok) return;
            
            const aggregates = await response.json();
            
            // Update preview display
            const preview = document.getElementById('aggregatePreview');
            if (preview) {
                preview.innerHTML = `
                    <strong>एकूण स्तर:</strong> ${aggregates.count} | 
                    <strong>मुळ वेतन:</strong> ${aggregates.basic_pay} | 
                    <strong>एकूण:</strong> ${aggregates.grand_total}
                `;
            }
        } catch (error) {
            console.error('Failed to calculate aggregates:', error);
        }
    }
    
    async applyAggregates() {
        if (!confirm('सर्व स्तरांचे एकूण मुख्य रेकॉर्डमध्ये लागू करायचे आहे का?')) return;
        
        try {
            const response = await fetch(`${this.apiBasePath}/${this.budgetPostId}/apply-aggregates`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to apply aggregates');
            }
            
            const result = await response.json();
            
            if (typeof showNotification === 'function') {
                showNotification('एकूण यशस्वीरित्या लागू केले', 'success');
            }
            
            // Callback to refresh main form if provided
            if (this.onAggregateApplied) {
                this.onAggregateApplied(result.aggregates);
            }
            
            // Optionally reload page to reflect changes
            setTimeout(() => window.location.reload(), 1500);
        } catch (error) {
            console.error('Failed to apply aggregates:', error);
            if (typeof showNotification === 'function') {
                showNotification(error.message || 'एकूण लागू करताना त्रुटी', 'error');
            }
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global instance (will be initialized by template)
let postLevelsManager = null;

