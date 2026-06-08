const LanguageManager = {

  // Get saved language or default to English
  getCurrentLang() {
    return localStorage.getItem('agrismart_lang') || 'en';
  },

  // Switch language and save preference
  toggleLanguage() {
    const current = this.getCurrentLang();
    const newLang = current === 'en' ? 'gu' : 'en';
    localStorage.setItem('agrismart_lang', newLang);
    this.applyLanguage(newLang);
  },

  // Apply language to all elements on page
  applyLanguage(lang) {
    if (typeof translations === 'undefined') return;
    const t = translations[lang];
    if (!t) return;

    // Update all elements with data-lang or data-i18n attribute
    document.querySelectorAll('[data-lang], [data-i18n]').forEach(el => {
      const key = el.getAttribute('data-lang') || el.getAttribute('data-i18n');
      if (t[key]) {
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          if (el.hasAttribute('placeholder')) {
            el.setAttribute('placeholder', t[key]);
          } else {
            el.value = t[key];
          }
        } else {
          el.textContent = t[key];
        }
      }
    });

    // 3D Language Toggle Button text is automatically updated by the data-i18n loop above.

    // Update html lang attribute
    document.documentElement.lang = lang === 'gu' ? 'gu' : 'en';

    // Update font for Gujarati
    if (lang === 'gu') {
      document.body.style.fontFamily = "'Noto Sans Gujarati', 'sans-serif'";
    } else {
      document.body.style.fontFamily = "";
    }
    
    // Notify any dynamic page elements that language has updated
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
  },

  // Initialize on page load
  init() {
    const lang = this.getCurrentLang();
    this.applyLanguage(lang);
  }
};

// Global helper anyone can call
function getCurrentLanguage() {
  return localStorage.getItem('agrismart_lang') || 'en';
}

// Auto-initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  LanguageManager.init();
});