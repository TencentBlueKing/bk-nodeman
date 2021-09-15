import Vue from 'vue';
// 全局组件
import '@/common/bkmagic';
import Exception from '@/components/exception/index.vue';
import AuthLogin from '@/components/auth/index.vue';
import AuthComponent from '@/components/auth/auth.vue';
import BkBizSelect from '@/components/common/bk-biz-select.vue';

Vue.component('AppException', Exception);
Vue.component('AppAuth', AuthLogin);
Vue.component('AuthComponent', AuthComponent);
Vue.component('BkBizSelect', BkBizSelect);
