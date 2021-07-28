/**
 * 判断属性props是否存在obj中
 * @param obj
 * @param props
 */
export const hasOwnProperty = (obj: any, props: string | string[]) => {
  if (Array.isArray(props)) {
    return props.every(str => Object.prototype.hasOwnProperty.call(obj, str));
  }
  return Object.prototype.hasOwnProperty.call(obj, props);
};
/**
 * 防抖装饰器
 * @param delay
 */
export const Debounce = (delay = 200) => (target: any, key: string, descriptor: PropertyDescriptor) => {
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
 * 关键字搜索
 * @param data
 * @param keyword
 */
export const defaultSearch = (data: any[], keyword: string) => {
  if (!Array.isArray(data) || keyword.trim() === '') return data;
  return data.filter(item => Object.keys(item).some((key) => {
    if (typeof item[key] === 'string') {
      return item[key].indexOf(keyword.trim()) > -1;
    }
    return false;
  }));
};

export default {
  hasOwnProperty,
  Debounce,
  defaultSearch,
};
