import { regIPv6 } from '@/common/regexp';

export function setIpProp(key: string, obj: Dictionary): { [key: string]: string } {
  return regIPv6.test(obj[key])
    ? { [`${key}v6`]: obj[key] }
    : { [key]: obj[key] };
}

// 双模式下优先使用 ipv4
export function initIpProp(obj, keys: string[]): void {
  keys.forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(obj, `${key}v6`)) {
      obj[key] =  obj[key] || obj[`${key}v6`] || '';
    }
  });
}
