import Vue from 'vue';
import cursor from '@/common/cursor';
import freezingPage from '@/common/freezing-page';
import authority from '@/common/authority';
import testAnchor from '@/common/test-anchor';
import VueClipboard from 'vue-clipboard2';

Vue.use(cursor);
Vue.use(freezingPage);
Vue.use(authority);
Vue.use(testAnchor);
VueClipboard.config.autoSetContainer = true;
Vue.use(VueClipboard);
