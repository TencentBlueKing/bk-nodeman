import Vue from 'vue';
// 全局组件
import '@/common/bkmagic';
import Exception from '@/components/exception/index.vue';
import AuthLogin from '@/components/auth/index.vue';
import AuthComponent from '@/components/auth/auth.vue';
import BkBizSelect from '@/components/common/bk-biz-select.vue';
import NmColumn from '@/components/common/nm-column.vue';
import DollForm from '@/components/RussianDolls/DollForm.vue';
import DollIndex from '@/components/RussianDolls/item/DollIndex.vue';
import DollBase from '@/components/RussianDolls/item/DollBase.vue';
import DollObject from '@/components/RussianDolls/item/DollObject.vue';
import DollArray from '@/components/RussianDolls/item/DollArray.vue';
import DollKeyValue from '@/components/RussianDolls/item/DollKeyValue.vue';

Vue.component('AppException', Exception);
Vue.component('AppAuth', AuthLogin);
Vue.component('AuthComponent', AuthComponent);
Vue.component('BkBizSelect', BkBizSelect);
Vue.component('NmColumn', NmColumn);

// 套娃的表单
Vue.component('DollForm', DollForm);
Vue.component('DollIndex', DollIndex);
Vue.component('DollBase', DollBase);
Vue.component('DollObject', DollObject);
Vue.component('DollArray', DollArray);
Vue.component('DollKeyValue', DollKeyValue);
