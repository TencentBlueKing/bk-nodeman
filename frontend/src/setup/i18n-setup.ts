import Vue from 'vue';
import VueI18n from 'vue-i18n';
import zh from '@/i18n/zh.js';
import en, { langDialog } from '@/i18n/en.js';
import { locale, lang } from 'bk-magic-vue';
import cookie from 'cookie';

// vue组件国际化
// const bkLang = lang

// 设置初始化语言（中文、英文）
Vue.use(VueI18n);
let currentLang = cookie.parse(document.cookie).blueking_language
  ? cookie.parse(document.cookie).blueking_language
  : 'zh-cn';

if (['zh-CN', 'zh-cn', 'cn', 'zhCN', 'zhcn', 'None', 'none'].indexOf(currentLang) > -1) {
  currentLang = 'zhCN';
  window.language = 'zh-cn';
} else {
  currentLang = 'enUS';
  window.language = 'en';
}

Object.assign(lang.enUS?.bk?.dialog || {}, langDialog); // 合并组件库的默认翻译
const messages = {
  zhCN: Object.assign(lang.zhCN, zh),
  enUS: Object.assign(lang.enUS, en),
};

export const i18n = new VueI18n({
  // 语言标识
  locale: currentLang,
  fallbackLocale: 'zhCN',
  messages,
  // silentTranslationWarn: false
});
locale.use(lang[currentLang]);
// locale.i18n((key, value) => i18n.t(key, value))

// 默认语言
const loadedLanguages = ['zhCN', 'enUS'];
/**
 * 设置语言
 * @param {String} lang
 */
function setI18nLanguage(lang: string) {
  i18n.locale = lang;
    document.querySelector('html')?.setAttribute('lang', lang);
    return lang;
}
/**
 * 异步加载语言
 * @param {String} lang
 */
export function loadLanguageAsync(lang: string) {
  if (i18n.locale !== lang) {
    if (!loadedLanguages.includes(lang)) {
      return import(/* webpackChunkName: "lang-[request]" */ `@/i18n/${lang}`).then((msgs) => {
        const messages = msgs.default;
        i18n.setLocaleMessage(lang, messages);
        // vue组件设置
        locale.i18n((key: string, value: string) => i18n.t(key, value));
        loadedLanguages.push(lang);
        return setI18nLanguage(lang);
      });
    }
    return Promise.resolve(setI18nLanguage(lang));
  }
  return Promise.resolve(lang);
}

window.i18n = i18n;

export default i18n;
