import { MainStore } from '@/store/index';

const ANONYMOUS_USER = {
  id: null,
  isAuthenticated: false,
  username: 'anonymous',
};

let currentUser: { [key: string]: any } = {
  id: '',
  username: '',
  isAuthenticated: false,
};

export default {
  /**
   * 未登录状态码
   */
  HTTP_STATUS_UNAUTHORIZED: 401,

  /**
   * 获取当前用户
   *
   * @return {Object} 当前用户信息
   */
  getCurrentUser() {
    return currentUser;
  },

  /**
   * 请求当前用户信息
   *
   * @return {Promise} promise 对象
   */
  requestCurrentUser() {
    let promise = null;
    if (currentUser.isAuthenticated) {
      promise = new Promise((resolve) => {
        resolve(currentUser);
      });
    } else {
      if (!MainStore.user || !Object.keys(MainStore.user).length) {
        // store action userInfo 里，如果请求成功会更新 state.user
        const req = MainStore.userInfo();
        promise = new Promise((resolve, reject) => {
          req.then(() => {
            // 存储当前用户信息(全局)
            currentUser = MainStore.user;
            currentUser.isAuthenticated = true;
            resolve(currentUser);
          }, (err) => {
            if (err.response.status === this.HTTP_STATUS_UNAUTHORIZED || err.crossDomain) {
              resolve({ ...ANONYMOUS_USER });
            } else {
              reject(err);
            }
          });
        });
      }
    }

    return promise;
  },
};
