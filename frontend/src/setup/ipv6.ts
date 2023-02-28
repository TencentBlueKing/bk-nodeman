import { regIPv6 } from '@/common/regexp';

export function setIpProp(key: string, obj: Dictionary): { [key: string]: string } {
  return $DHCP && regIPv6.test(obj[key])
    ? { [`${key}v6`]: obj[key] }
    : { [key]: obj[key] };
}

// 双模式下优先使用 IPv4
export function initIpProp(obj, keys: string[]): void {
  if ($DHCP) {
    keys.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(obj, `${key}v6`)) {
        obj[key] =  obj[key] || obj[`${key}v6`] || '';
      }
    });
  }
}
