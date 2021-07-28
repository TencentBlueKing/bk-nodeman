import Vue from 'vue';

// 全量引入
// import './fully-import'

// 按需引入
import './demand-import';

const bkMessage = Vue.prototype.$bkMessage as Function;

let messageInstance: any = null;

export const messageError = (message: string, delay = 3000) => {
  messageInstance?.close();
  messageInstance = bkMessage({
    ellipsisLine: 2,
    message,
    delay,
    theme: 'error',
  });
};

export const messageSuccess = (message: string, delay = 3000) => {
  messageInstance?.close();
  messageInstance = bkMessage({
    message,
    delay,
    theme: 'success',
  });
};

export const messageInfo = (message: string, delay = 3000) => {
  messageInstance?.close();
  messageInstance = bkMessage({
    message,
    delay,
    theme: 'primary',
  });
};

export const messageWarn = (message: string, delay = 3000) => {
  messageInstance?.close();
  messageInstance = bkMessage({
    message,
    delay,
    theme: 'warning',
    hasCloseIcon: true,
  });
};

Vue.prototype.messageError = messageError;
Vue.prototype.messageSuccess = messageSuccess;
Vue.prototype.messageInfo = messageInfo;
Vue.prototype.messageWarn = messageWarn;
