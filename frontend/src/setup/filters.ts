import Vue from 'vue';
import { isEmpty, formatTimeByTimezone } from '@/common/util';

export function filterEmpty(value: any, context = '--') {
  return isEmpty(value) ? context : value;
}

Vue.filter('filterEmpty', filterEmpty);
Vue.filter('filterTimezone', formatTimeByTimezone);
