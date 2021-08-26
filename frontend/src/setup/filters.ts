import Vue from 'vue';
import { isEmpty, formatTimeByTimezone } from '@/common/util';

Vue.prototype.$filters = function (filterName: string, value: any) {
  return this._f(filterName)(value);
};

export function filterEmpty(value: any, context = '--') {
  return isEmpty(value) ? context : value;
}

Vue.filter('filterEmpty', filterEmpty);
Vue.filter('filterTimezone', formatTimeByTimezone);
