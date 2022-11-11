import Vue from 'vue';
import { i18n } from './i18n-setup';
import './global-components-setup';
import './global';
import './directives';
import './filters';
import { RSA } from './encrypt';
import { textTool } from './text-tool';
import { setIpProp, initIpProp } from './ipv6';

Vue.prototype.$filters = function (filterName: string, value: any) {
  return this._f(filterName)(value);
};
Vue.prototype.$RSA = RSA;
Vue.prototype.$textTool = textTool;
Vue.prototype.$setIpProp = setIpProp;
Vue.prototype.$initIpProp = initIpProp;

export default i18n;
