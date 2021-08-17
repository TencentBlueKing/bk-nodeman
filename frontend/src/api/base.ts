import axios from '@/api';
import { json2Query } from '@/common/util';
import { IAxiosConfig } from '@/types/index';

const defaultConfig = { checkData: false, needRes: false, hasBody: false };
const methodsWithoutData = ['delete', 'get', 'head', 'options'];

export const request = (method: string, url: string) => (pk?: any, params?: any, config: IAxiosConfig = {}) => {
  method = method.toLowerCase();
  let data = {};
  let newUrl = url;
  if (typeof pk === 'number' || typeof pk === 'string') {
    newUrl = url.replace('{{pk}}', String(pk));
    data = params || {};
    config = Object.assign({}, defaultConfig, config);
  } else {
    data = pk || {};
    config = Object.assign({}, defaultConfig, params || {});
  }

  let req = null;
  if (methodsWithoutData.includes(method)  && !config.hasBody) {
    const query = json2Query(data, '');
    if (query) {
      newUrl += `?${query}`;
    }
    req = axios[method](newUrl, config);
  } else {
    req = axios[method](newUrl, Object.keys(data).length ? data : null, config);
  }
  return req.then((res: any) => {
    if (config.checkData && !res.data) {
      return Promise.reject(res);
    }
    if (config.needRes) {
      return Promise.resolve(res);
    }
    return Promise.resolve(res.data);
  }).catch((err: Error) => {
    console.log('request error', err);
    return Promise.reject(err);
  });
};

export default request;
