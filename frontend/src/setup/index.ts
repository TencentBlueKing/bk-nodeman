import Vue from 'vue';
import type { TranslateResult } from 'vue-i18n';
import { i18n } from './i18n-setup';
import './global-components-setup';
import './global';
import './directives';
import './filters';
import NmSafety from './safety';
import { textTool } from './text-tool';
import { setIpProp, initIpProp } from './ipv6';
import './mixins';

Vue.prototype.$filters = function (filterName: string, value: any) {
  return this._f(filterName)(value);
};
Vue.prototype.$safety = new NmSafety();
Vue.prototype.$textTool = textTool;
Vue.prototype.$setIpProp = setIpProp;
Vue.prototype.$initIpProp = initIpProp;

export { TranslateResult };
export default i18n;
