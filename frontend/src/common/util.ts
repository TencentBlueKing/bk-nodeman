/**
 * 函数柯里化
 *
 * @example
 *     function add (a, b) {return a + b}
 *     curry(add)(1)(2)
 *
 * @param {Function} fn 要柯里化的函数
 *
 * @return {Function} 柯里化后的函数
 */
export function curry(fn: Function) {
  const judge = (...args: any) => (args.length === fn.length
    ? fn(...args)
    : (arg: any) => judge(...args, arg));
  return judge;
}

/**
 * 判断是否是对象
 *
 * @param {Object} obj 待判断的
 *
 * @return {boolean} 判断结果
 */
export function isObject(obj: any) {
  return obj !== null && typeof obj === 'object';
}

/**
 * 判断是否为空
 * @param {Object} obj
 */
export function isEmpty(obj: any) {
  return typeof obj === 'undefined' || obj === null || obj === '';
}

/**
 * 规范化参数
 *
 * @param {Object|string} type vuex type
 * @param {Object} payload vuex payload
 * @param {Object} options vuex options
 *
 * @return {Object} 规范化后的参数
 */
export function unifyObjectStyle(type: any, payload: any, options: any) {
  if (isObject(type) && type.type) {
    options = payload;
    payload = type;
    type = type.type;
  }

  if (NODE_ENV !== 'production') {
    if (typeof type !== 'string') {
      console.warn(`expects string as the type, but found ${typeof type}.`);
    }
  }

  return { type, payload, options };
}

/**
 * 以 baseColor 为基础生成随机颜色
 *
 * @param {string} baseColor 基础颜色
 * @param {number} count 随机颜色个数
 *
 * @return {Array} 颜色数组
 */
export function randomColor(baseColor: string, count: number) {
  const segments = baseColor.match(/[\da-z]{2}/g);
  if (!segments) return [];
  // 转换成 rgb 数字
  const segm = segments.map(item => parseInt(item, 16));
  const ret = [];
  // 生成 count 组颜色，色差 20 * Math.random
  for (let i = 0; i < count; i++) {
    ret[i] = `#${
      Math.floor(segm[0] + ((Math.random() < 0.5 ? -1 : 1) * Math.random() * 20)).toString(16)
    }${Math.floor(segm[1] + ((Math.random() < 0.5 ? -1 : 1) * Math.random() * 20)).toString(16)
    }${Math.floor(segm[2] + ((Math.random() < 0.5 ? -1 : 1) * Math.random() * 20)).toString(16)}`;
  }
  return ret;
}

/**
 * min max 之间的随机整数
 *
 * @param {number} min 最小值
 * @param {number} max 最大值
 *
 * @return {number} 随机数
 */
export function randomInt(min: number, max: number) {
  return Math.floor((Math.random() * ((max - min) + 1)) + min);
}

/**
 * 异常处理
 *
 * @param {Object} err 错误对象
 * @param {Object} ctx 上下文对象，这里主要指当前的 Vue 组件
 */
export function catchErrorHandler(err: any, ctx: any) {
  const { data } = err;
  if (data) {
    if (!data.code || data.code === 404) {
      ctx.exceptionCode = {
        code: '404',
        msg: '当前访问的页面不存在',
      };
    } else if (data.code === 403) {
      ctx.exceptionCode = {
        code: '403',
        msg: 'Sorry，您的权限不足!',
      };
    } else {
      console.error(err);
      ctx.bkMessageInstance = ctx.$bkMessage({
        theme: 'error',
        message: err.message || err.data.msg || err.statusText,
      });
    }
  } else {
    console.error(err);
    ctx.bkMessageInstance = ctx.$bkMessage({
      theme: 'error',
      message: err.message || err.data.msg || err.statusText,
    });
  }
}

/**
 * 获取字符串长度，中文算两个，英文算一个
 *
 * @param {string} str 字符串
 *
 * @return {number} 结果
 */
export function getStringLen(str: string) {
  let len = 0;
  for (let i = 0; i < str.length; i++) {
    if (str.charCodeAt(i) > 127 || str.charCodeAt(i) === 94) {
      len += 2;
    } else {
      len = len + 1;
    }
  }
  return len;
}

/**
 * 转义特殊字符
 *
 * @param {string} str 待转义字符串
 *
 * @return {string} 结果
 */
export const escape = (str: string) => String(str).replace(/([.*+?^=!:${}()|[\]/\\])/g, '\\$1');

/**
 * 对象转为 url query 字符串
 *
 * @param {*} param 要转的参数
 * @param {string} key key
 *
 * @return {string} url query 字符串
 */
export function json2Query(param: any, key: string) {
  const mappingOperator = '=';
  const separator = '&';
  let paramStr = '';

  if (param instanceof String || typeof param === 'string'
            || param instanceof Number || typeof param === 'number'
            || param instanceof Boolean || typeof param === 'boolean'
  ) {
    paramStr += separator + key + mappingOperator + encodeURIComponent(param as (string | number | boolean));
  } else {
    Object.keys(param).forEach((p) => {
      const value = param[p];
      const k = (key === null || key === '' || key === undefined)
        ? p
        : key + (param instanceof Array ? `[${p}]` : `.${p}`);
      paramStr += separator + json2Query(value, k);
    });
  }
  return paramStr.substr(1);
}

/**
 * 字符串转换为驼峰写法
 *
 * @param {string} str 待转换字符串
 *
 * @return {string} 转换后字符串
 */
export function camelize(str: string) {
  return str.replace(/-(\w)/g, (strMatch, p1) => p1.toUpperCase());
}

/**
 * 获取元素的样式
 *
 * @param {Object} elem dom 元素
 * @param {string} prop 样式属性
 *
 * @return {string} 样式值
 */
export function getStyle(elem: HTMLElement, prop: string) {
  if (!elem || !prop) {
    return false;
  }

  // 先获取是否有内联样式
  let value: string | boolean = camelize(prop) in elem.style;

  if (!value) {
    // 获取的所有计算样式
    let css = null;
    if (document.defaultView && document.defaultView.getComputedStyle) {
      css = document.defaultView.getComputedStyle(elem, null);
      value = css ? css.getPropertyValue(prop) : '';
    }
  }

  return String(value);
}

/**
 *  获取元素相对于页面的高度
 *
 *  @param {Object} node 指定的 DOM 元素
 */
export function getActualTop(node: HTMLElement) {
  let actualTop = node.offsetTop;
  let current = node.offsetParent;

  while (current !== null) {
    actualTop += (current as HTMLElement).offsetTop;
    current = (current as HTMLElement).offsetParent;
  }

  return actualTop;
}

/**
 *  获取元素相对于页面左侧的宽度
 *
 *  @param {Object} node 指定的 DOM 元素
 */
export function getActualLeft(node: HTMLElement) {
  let actualLeft = node.offsetLeft;
  let current = node.offsetParent;

  while (current !== null) {
    actualLeft += (current as HTMLElement).offsetLeft;
    current = (current as HTMLElement).offsetParent;
  }

  return actualLeft;
}

/**
 * document 总高度
 *
 * @return {number} 总高度
 */
export function getScrollHeight() {
  let scrollHeight = 0;
  let bodyScrollHeight = 0;
  let documentScrollHeight = 0;

  if (document.body) {
    bodyScrollHeight = document.body.scrollHeight;
  }

  if (document.documentElement) {
    documentScrollHeight = document.documentElement.scrollHeight;
  }

  scrollHeight = (bodyScrollHeight - documentScrollHeight > 0) ? bodyScrollHeight : documentScrollHeight;

  return scrollHeight;
}

/**
 * 滚动条在 y 轴上的滚动距离
 *
 * @return {number} y 轴上的滚动距离
 */
export function getScrollTop() {
  let scrollTop = 0;
  let bodyScrollTop = 0;
  let documentScrollTop = 0;

  if (document.body) {
    bodyScrollTop = document.body.scrollTop;
  }

  if (document.documentElement) {
    documentScrollTop = document.documentElement.scrollTop;
  }

  scrollTop = (bodyScrollTop - documentScrollTop > 0) ? bodyScrollTop : documentScrollTop;

  return scrollTop;
}

/**
 * 浏览器视口的高度
 *
 * @return {number} 浏览器视口的高度
 */
export function getWindowHeight() {
  const windowHeight = document.compatMode === 'CSS1Compat'
    ? document.documentElement.clientHeight
    : document.body.clientHeight;

  return windowHeight;
}

/**
 * 简单的 loadScript
 *
 * @param {string} url js 地址
 * @param {Function} callback 回调函数
 */
export function loadScript(url: string, callback: Function) {
  const script = document.createElement('script');
  script.async = true;
  script.src = url;

  script.onerror = () => {
    callback(new Error(`Failed to load: ${url}`));
  };

  script.onload = () => {
    callback();
  };

  document.getElementsByTagName('head')[0].appendChild(script);
}

/**
 * 函数防抖
 * @param {*} fn 执行的函数
 * @param {*} delay 延时时间
 * @param {*} immediate 是否立即执行
 */
export function debounce(delay = 300, fn: Function, immediate = false) {
  let timeout: any;
  let result: any;
  const debounced = function () {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    const ctx = this;// 当前上下文
    // eslint-disable-next-line prefer-rest-params
    const args = arguments;// fn的参数

    // 取消之前的延时调用
    if (timeout) clearTimeout(timeout);
    if (immediate) {
      const applyImmediate = !timeout; // 是否执行过
      timeout = setTimeout(() => {
        timeout = null;// 标志是否执行过，与clearTimeout有区别，clearTimeout之后timeout不为null而是一个系统分配的队列ID
      }, delay);
      if (applyImmediate) result = fn.apply(ctx, args); // 立即调用
    } else {
      timeout = setTimeout(() => {
        fn.apply(ctx, args);
      }, delay);
    }
    return result;
  };
  debounced.cancel = function () {
    clearTimeout(timeout);
    timeout = null;
  };

  return debounced;
}
/**
 * 函数节流简单版
 * @param {*} fn
 * @param {*} delay
 */
export function throttle(fn: Function, delay: number) {
  let flag = false;// 标志是否执行完成
  return function (e: any) {
    // 未执行完成，退出
    if (flag) return false;
    // 开始执行，但未完成
    flag = true;
    setTimeout(() => {
      fn(e);
      // 执行完成
      flag = false;
    }, delay);
  };
}
// 下划线转换驼峰
export const toHump = (name: string) => name.replace(/_(\w)/g, (all, letter) => letter.toUpperCase());
// 驼峰转换下划线
export const toLine = (name: string) => name.replace(/([A-Z])/g, '_$1').toLowerCase();
// 下划线与Camel命名互转，默认转驼峰
export const transformDataKey = (data: Dictionary = {}, mode = 'camel'): Dictionary => {
  if (!['[object Array]', '[object Object]'].includes(Object.prototype.toString.call(data))) return data;
  const result: Dictionary = {};
  if (Array.isArray(data)) {
    return data.map(item => transformDataKey(item, mode));
  }
  Object.keys(data).forEach((key) => {
    const matchList = mode === 'camel' ? key.match(/(_[a-zA-Z])/g) : key.match(/([A-Z])/g);
    let newKey = key;
    const item = data[key];
    if (matchList) {
      if (mode === 'camel') {
        matchList.forEach((set) => {
          newKey = newKey.replace(set, set.replace('_', '').toLocaleUpperCase());
        });
      } else {
        matchList.forEach((set) => {
          newKey = newKey.replace(set, toLine(set));
        });
      }
    }
    if (item && typeof item === 'object' && Object.keys(item).length) {
      result[newKey] = transformDataKey(item, mode);
    } else {
      result[newKey] = item;
    }
  });

  return result;
};
/**
 * 复制文本
 * @param {String} text
 */
export const copyText = (text: string, successFn?: Function) => {
  window.copyContentText = text || '';
  let result = 'failed';
  if (!window.copyContentText) {
    window.bus.$bkMessage({
      theme: 'error',
      message: window.i18n.t('复制出错，再重新复制一遍吧'),
    });
    return result;
  }
  result = copyListener();
  if (result === 'success' && successFn) {
    successFn(result);
  }
  if (result === 'failed') {
    window.copyFailedMsg = window.bus.$bkMessage({
      theme: 'error',
      message: getCopyBtn(successFn),
    });
  }
  return result;
};

function copyListener() {
  let result = '';
  try {
    document.addEventListener('copy', copyHandler);
    const copyRes = document.execCommand('copy');
    document.removeEventListener('copy', copyHandler);
    result = copyRes ? 'success' : 'failed';
  } catch (_) {
    result = 'error';
    window.bus.$bkMessage({
      theme: 'error',
      message: '浏览器不支持此功能，请使用谷歌浏览器。',
    });
  }
  return result;
}

export const copyHandler = (e: any) => {
  e.preventDefault();
  e.clipboardData.setData('text/html', window.copyContentText);
  e.clipboardData.setData('text/plain', window.copyContentText);
};

export const getCopyBtn = (successFn?: Function) => {
  const h = window.mainComponent.$createElement;
  const copyBtn = h('p', [
    window.i18n.t('复制出错，再重新复制一遍吧'),
    h('span', {
      style: { color: '#3A84FF', cursor: 'pointer' },
      on: {
        click: () => {
          const res = copyListener();
          if (window.copyFailedMsg) {
            window.copyFailedMsg.close();
          }
          if (successFn && res === 'success') {
            successFn(res);
          }
          if (res === 'failed') {
            window.bus.$bkMessage({ theme: 'error', message: '复制失败' });
          }
          window.copyContentText = '';
        },
      },
    }, window.i18n.t('点击复制')),
  ]);
  return copyBtn;
};

/**
 * 下载
 */
export const download = (filename: string, href: string) => {
  const element = document.createElement('a');
  element.setAttribute('href', href);
  element.setAttribute('download', filename);
  element.style.display = 'none';
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
};
/**
 * 导出日志
 */
export const downloadLog = (filename: string, text: string) => {
  const element = document.createElement('a');
  element.setAttribute('href', `data:text/plain;charset=utf-8,${encodeURIComponent(text)}`);
  element.setAttribute('download', filename);
  element.style.display = 'none';
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
};

/**
 * 排序数组对象
 * 排序规则：1. 数字 => 2. 字母 => 3. 中文
 * @param {*} arr
 * @param {*} key
 */
export const sort = (arr: any[], key: string) => {
  if (!Array.isArray(arr)) return;
  const reg = /^[0-9a-zA-Z]/;
  return arr.sort((pre, next) => {
    if (isObject(pre) && isObject(next) && key) {
      if (reg.test(pre[key]) && !reg.test(next[key])) {
        return -1;
      } if (!reg.test(pre[key]) && reg.test(next[key])) {
        return 1;
      }
      return pre[key].localeCompare(next[key]);
    }
    return (`${pre}`).toString().localeCompare((`${pre}`));
  });
};
/**
 * 对象深拷贝
 * @param {*} obj
 */
export function deepClone(obj: any) {
  if (obj === null || typeof obj !== 'object') return obj;
  const cpObj: any = obj instanceof Array ? [] : {};
  // eslint-disable-next-line no-restricted-syntax
  for (const key in obj) cpObj[key] = deepClone(obj[key]);
  return cpObj;
}

/**
 *  @param {number}  timezone -12 - 12
 */
export function formatTimeByTimezone(date: string, timezone?: number, fmt = 'YYYY-mm-dd HH:MM:SS') {
  let formatTime = '--';
  if (date) {
    try {
      const currentTimezone = new Date().getTimezoneOffset() / -60;
      const offsetTimezone = timezone || timezone === 0 ? currentTimezone - timezone : 0;
      const timeString = new Date(date).getTime();
      formatTime = filterTimeFormat(new Date(timeString - (offsetTimezone * 60 * 60 * 1000)), fmt);
    } catch (err) {}
  }
  return formatTime;
}
// 格式化时间戳 dateFormat(date, "YYYY-mm-dd HH:MM:SS")
export function filterTimeFormat(date: Date, fmt? = 'YYYY-mm-dd HH:MM:SS') {
  const fmtArr = ['Y+', 'm+', 'd+', 'H+', 'M+', 'S+'];
  const opt = {
    'Y+': date.getFullYear().toString(),        // 年
    'm+': (date.getMonth() + 1).toString(),     // 月
    'd+': date.getDate().toString(),            // 日
    'H+': date.getHours().toString(),           // 时
    'M+': date.getMinutes().toString(),         // 分
    'S+': date.getSeconds().toString(),          // 秒
  };
  let res;
  let time = fmt;
  fmtArr.forEach((key) => {
    res = new RegExp(`(${key})`).exec(fmt);
    if (res) {
      time = time.replace(res[1], (res[1].length === 1) ? (opt[key]) : (opt[key].padStart(res[1].length, '0')));
    }
  });
  return time;
}
/**
 * 格式化时间 - 最大单位 天
 */
export function takesTimeFormat(seconds: number | string) {
  const sortList = [
    { unit: 'd', calculate: 24 * 60 * 60 },
    { unit: 'h', calculate: 60 * 60 },
    { unit: 'm', calculate: 60 },
    { unit: 's', calculate: 1 },
  ];
  let nonZero = false; // 非零开头
  let remainders = parseInt(seconds, 10);
  const arr = sortList.reduce<string[]>((arr, item) => {
    const num = Math.floor(remainders / item.calculate);
    remainders = remainders % item.calculate;
    if (num || nonZero) {
      arr.push(`${num}${item.unit}`);
      nonZero = true;
    }
    return arr;
  }, []);
  return arr.join(' ') || 0;
}
/**
* 防抖装饰器
* @param [delay: number] 延时ms
* @returns descriptor
*/
export const debounceDecorate = (delay = 200) => (target: any, key: string, descriptor: PropertyDescriptor) => {
  const originFunction = descriptor.value;
  const getNewFunction = () => {
    let timer: any;
    const newFunction = function (...args: any[]) {
      if (timer) window.clearTimeout(timer);
      timer = setTimeout(() => {
        originFunction.call(this, ...args);
      }, delay);
    };
    return newFunction;
  };
  descriptor.value = getNewFunction();
  return descriptor;
};

/**
 * searchSelect 组件输入的 name|id 转换成child
 */
export const getFilterChildBySelected = (key: string, text: string, filterData: any[]) => {
  const category = filterData.find(item => item.id === key || item.name === key);
  const childIds: Dictionary[] = [];
  if (category && Array.isArray(category.children)) {
    const textArr = text.replace(/\s/g, '').split('|');
    textArr.forEach((name) => {
      const child = category.children.find(item => item.name === name);
      if (child) {
        childIds.push({ ...child });
      }
    });
  }
  return childIds.length ? childIds : [{ id: text }];
};
