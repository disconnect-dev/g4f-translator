class AITranslator {
    constructor() {
        this.initializeElements();
        this.initializeEventListeners();
        this.debounceTimer = null;
        this.currentTranslation = '';
        this.isTranslating = false;
        
        console.log('⚡ AI Translator initialized');
    }

    initializeElements() {
        this.sourceText = document.getElementById('sourceText');
        this.translationOutput = document.getElementById('translationOutput');
        
        this.sourceLang = document.getElementById('sourceLang');
        this.targetLang = document.getElementById('targetLang');
        
        this.translateBtn = document.getElementById('translateBtn');
        this.swapBtn = document.getElementById('swapBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.copyBtn = document.getElementById('copyBtn');
        this.pasteBtn = document.getElementById('pasteBtn');
        
        this.charCount = document.getElementById('charCount');
        this.translationStatus = document.getElementById('translationStatus');
        this.btnLoader = document.getElementById('btnLoader');
        this.notifications = document.getElementById('notifications');

        this.btnText = this.translateBtn.querySelector('.btn-text');
    }

    initializeEventListeners() {
        this.sourceText.addEventListener('input', () => this.handleTextInput());
        this.sourceText.addEventListener('paste', () => this.handlePaste());
        
        this.sourceLang.addEventListener('change', () => this.handleLanguageChange());
        this.targetLang.addEventListener('change', () => this.handleLanguageChange());
        
        this.translateBtn.addEventListener('click', () => this.handleTranslate());
        this.swapBtn.addEventListener('click', () => this.handleSwapLanguages());
        this.clearBtn.addEventListener('click', () => this.handleClear());
        this.copyBtn.addEventListener('click', () => this.handleCopy());
        this.pasteBtn.addEventListener('click', () => this.handlePasteButton());
        
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        this.sourceText.addEventListener('input', () => this.debounceTranslate());
        
        this.sourceText.addEventListener('input', () => this.updateCharCount());
        
        this.updateCharCount();
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('translator-theme') || 'light';
        this.setTheme(savedTheme);
    }

    handleTextInput() {
        const text = this.sourceText.value;
        
        this.updateCharCount();
        
        this.translateBtn.disabled = !text.trim() || text.length > 5000;
        
        if (this.sourceLang.value === 'auto' && text.trim()) {
            this.detectLanguage(text);
        }
    }

    handlePaste() {
        setTimeout(() => {
            this.handleTextInput();
            this.showNotification('success', 'Текст вставлен', 'Готов к переводу');
        }, 100);
    }

    handleLanguageChange() {
        const sourceText = this.sourceText.value.trim();
        if (sourceText && !this.isTranslating) {
            this.debounceTranslate();
        }
    }

    async handleTranslate() {
        const text = this.sourceText.value.trim();
        
        if (!text) {
            this.showNotification('warning', 'Предупреждение', 'Введите текст для перевода');
            return;
        }
        
        if (text.length > 5000) {
            this.showNotification('error', 'Ошибка', 'Текст слишком длинный (максимум 5000 символов)');
            return;
        }
        
        await this.performTranslation(text);
    }

    async performTranslation(text) {
        if (this.isTranslating) return;
        
        this.isTranslating = true;
        this.setTranslateButtonLoading(true);
        this.updateTranslationStatus('Переводим...');
        
        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    source_lang: this.sourceLang.value,
                    target_lang: this.targetLang.value
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.displayTranslation(data.translation);
                
                const statusText = this.sourceLang.value === 'auto' 
                    ? `${data.source_language_name} → ${data.target_language_name}`
                    : `${data.source_language_name} → ${data.target_language_name}`;
                    
                this.updateTranslationStatus(statusText);
                
                this.copyBtn.disabled = false;
                
                this.showNotification('success', 'Готово', 'Текст переведен успешно');
                
            } else {
                throw new Error(data.error || 'Ошибка перевода');
            }

        } catch (error) {
            console.error('Translation error:', error);
            this.showNotification('error', 'Ошибка', error.message || 'Не удалось выполнить перевод');
            this.updateTranslationStatus('Ошибка перевода');
            
        } finally {
            this.isTranslating = false;
            this.setTranslateButtonLoading(false);
        }
    }

    displayTranslation(translation) {
        this.currentTranslation = translation;
        this.translationOutput.innerHTML = `<div class="translation-text">${this.escapeHtml(translation)}</div>`;
        this.translationOutput.classList.add('fade-in');
    }

    handleSwapLanguages() {
        if (this.sourceLang.value === 'auto') {
            this.showNotification('warning', 'Внимание', 'Нельзя поменять местами при автоопределении языка');
            return;
        }

        const sourceValue = this.sourceLang.value;
        const targetValue = this.targetLang.value;
        
        this.sourceLang.value = targetValue;
        this.targetLang.value = sourceValue;

        const sourceTextValue = this.sourceText.value;
        const currentTranslation = this.currentTranslation;
        
        this.sourceText.value = currentTranslation;
        this.currentTranslation = sourceTextValue;
        
        if (currentTranslation) {
            this.displayTranslation(sourceTextValue);
        } else {
            this.clearTranslation();
        }

        this.updateCharCount();
        
        if (this.sourceText.value.trim()) {
            this.debounceTranslate();
        }
        
        this.showNotification('success', 'Готово', 'Языки поменяны местами');
    }

    handleClear() {
        this.sourceText.value = '';
        this.clearTranslation();
        this.updateCharCount();
        this.updateTranslationStatus('Готов к переводу');
        this.translateBtn.disabled = true;
        this.copyBtn.disabled = true;
        this.sourceText.focus();
        
        this.showNotification('success', 'Очищено', 'Текст удален');
    }

    async handleCopy() {
        if (!this.currentTranslation) return;
        
        try {
            await navigator.clipboard.writeText(this.currentTranslation);
            this.showNotification('success', 'Скопировано', 'Перевод скопирован в буфер обмена');
        } catch (error) {
            console.error('Copy error:', error);
            
            const textArea = document.createElement('textarea');
            textArea.value = this.currentTranslation;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            this.showNotification('success', 'Скопировано', 'Перевод скопирован');
        }
    }

    async handlePasteButton() {
        try {
            const text = await navigator.clipboard.readText();
            this.sourceText.value = text;
            this.handleTextInput();
            this.sourceText.focus();
            
            this.showNotification('success', 'Вставлено', 'Текст вставлен из буфера обмена');
        } catch (error) {
            console.error('Paste error:', error);
            this.showNotification('error', 'Ошибка', 'Не удалось вставить текст');
        }
    }

    handleKeyboard(event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            if (!this.isTranslating && this.sourceText.value.trim()) {
                this.handleTranslate();
            }
        }
        
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            this.handleClear();
        }
        
        if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'S') {
            event.preventDefault();
            this.handleSwapLanguages();
        }
        
        if (event.key === 'Escape') {
            document.activeElement.blur();
        }
    }

    debounceTranslate() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            const text = this.sourceText.value.trim();
            if (text && !this.isTranslating) {
                this.performTranslation(text);
            }
        }, 1500);
    }

    updateCharCount() {
        const count = this.sourceText.value.length;
        this.charCount.textContent = count;
        
        if (count > 4500) {
            this.charCount.className = 'error';
        } else if (count > 4000) {
            this.charCount.className = 'warning';
        } else {
            this.charCount.className = '';
        }
        
        this.translateBtn.disabled = count === 0 || count > 5000;
    }

    setTranslateButtonLoading(loading) {
        if (loading) {
            this.translateBtn.classList.add('loading');
            this.translateBtn.disabled = true;
        } else {
            this.translateBtn.classList.remove('loading');
            this.translateBtn.disabled = !this.sourceText.value.trim() || this.sourceText.value.length > 5000;
        }
    }

    updateTranslationStatus(status) {
        this.translationStatus.textContent = status;
    }

    clearTranslation() {
        this.currentTranslation = '';
        this.translationOutput.innerHTML = '<div class="placeholder">Перевод появится здесь...</div>';
        this.translationOutput.classList.remove('fade-in');
    }

    detectLanguage(text) {
        const cyrillic = /[\u0400-\u04FF]/.test(text);
        const chinese = /[\u4e00-\u9fff]/.test(text);
        const arabic = /[\u0600-\u06FF]/.test(text);
        const korean = /[\uAC00-\uD7AF]/.test(text);
        const japanese = /[\u3040-\u309F\u30A0-\u30FF]/.test(text);
        
        let detectedLang = 'en';
        
        if (cyrillic) detectedLang = 'ru';
        else if (chinese) detectedLang = 'zh';
        else if (arabic) detectedLang = 'ar';
        else if (korean) detectedLang = 'ko';
        else if (japanese) detectedLang = 'ja';
        
        if (detectedLang !== 'en') {
            this.updateTranslationStatus(`Определен язык: ${this.getLanguageName(detectedLang)}`);
        }
    }

    getLanguageName(code) {
        const option = this.sourceLang.querySelector(`option[value="${code}"]`);
        return option ? option.textContent : code.toUpperCase();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(type, title, message) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        notification.innerHTML = `
            <div class="notification-icon">${icons[type] || icons.info}</div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
        `;
        
        this.notifications.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AITranslator();
});

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(console.error);
}
