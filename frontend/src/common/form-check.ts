import { isEmpty } from './util';
import {
  regIp,
  regIPv6,
  regUrl,
  regUrlMixinIp,
  regNormalText,
  regNaturalNumber,
  regInteger,
  regFnSysPath,
} from '@/common/regexp';

const i18nMap: Dictionary = {
  linux: 'Linux路径格式错误',
  windows: 'windows路径格式错误',
};

/**
 * regu: regexp rules
 */
export const reguRequired = {
  required: true,
  message: window.i18n.t('必填项'),
  trigger: 'blur',
};
export const reguIp = {
  regex: regIp,
  validator: (val: string) => regIp.test(val),
  message: window.i18n.t('IP格式不正确'),
  trigger: 'blur',
};
export const reguIPv6 = {
  regex: regIPv6,
  validator: (val: string) => regIPv6.test(val),
  message: window.i18n.t('IP格式不正确'),
  trigger: 'blur',
};
export const reguIPMixins = {
  validator: val => regIp.test(val) || regIPv6.test(val),
  message: window.i18n.t('IP格式不正确'),
  trigger: 'blur',
};
export const reguIpBatch = {
  trigger: 'blur',
  validator: (val: string) => {
    if (!val) return true;
    const splitCode = splitCodeArr.find(split => val.indexOf(split) > 0);
    const valSplit = val.split(splitCode).filter(text => !!text)
      .map(text => text.trim());
    // IP校验
    return valSplit.every(item => regIp.test(item) || regIPv6.test(item));
  },
  message: window.i18n.t('IP格式不正确'),
};
export const reguUrl = {
  regex: regUrl,
  validator: (val: string) => regUrl.test(val),
  message: window.i18n.t('URL格式不正确'),
  trigger: 'blur',
};
export const reguUrlMixinIp = {
  regex: regUrlMixinIp,
  message: window.i18n.t('URL格式不正确'),
  trigger: 'blur',
  validator: (val: string) => regUrlMixinIp.test(val),
};
export const reguPort = {
  validator: (val: string) => regNaturalNumber.test(val) && parseInt(val, 10) <= 65535,
  message: window.i18n.t('端口范围', { range: '0-65535' }),
  trigger: 'blur',
};
export const reguNaturalNumber = {
  regex: regNaturalNumber,
  validator: (val: string) => regNaturalNumber.test(val),
  message: window.i18n.t('不小于零的整数'),
  trigger: 'blur',
};
export function reguFnName(params?: { max: number } = {}) {
  const { max = 32 } = params;
  return {
    validator: (val: string) => regNormalText.test(val) && regrLengthCheck(val, max),
    message: window.i18n.t('正常输入内容校验', [max]),
    trigger: 'blur',
  };
}
export function reguFnStrLength(max = 40) {
  return {
    validator: (val: string) => regrLengthCheck(val, max),
    message: window.i18n.t('字符串长度校验', [Math.floor(max / 2), max]),
    trigger: 'blur',
  };
}
export function reguFnSysPath(params?: { [key: string]: number | string } = {}) { // 操作系统路径校验
  const { minText = 1, maxText = 16, minLevel = 1, type = 'linux' } = params;
  const reg = regFnSysPath({ minText, maxText, minLevel, type });
  return {
    type,
    message: window.i18n.t(i18nMap[type], { minLevel, maxText }),
    trigger: 'blur',
    validator: (val: string)  => reg.test(val),
  };
}
export function reguFnMinInteger(min = 0) {
  return {
    message: window.i18n.t('整数最小值校验提示', { min }),
    validator: (val: string)  => isEmpty(val) || (regInteger.test(val) && parseInt(val, 10) >= min),
    trigger: 'blur',
  };
}
export function reguFnRangeInteger(min: number, max: number) {
  return {
    validator: (val: string) => regInteger.test(val) && Number(val) <= max && Number(val) >= min,
    message: window.i18n.t('整数范围校验提示', { max, min }),
    trigger: 'blur',
  };
}
// 一行内不能重复
export const reguIpInLineRepeat = {
  trigger: 'blur',
  message: window.i18n.t('冲突校验', { prop: 'IP' }),
  validator(val: string) {
    if (!val) return true;
    const splitCode = splitCodeArr.find(split => val.indexOf(split) > 0);
    const valSplit = val.split(splitCode).filter(text => !!text)
      .map(text => text.trim());
    return new Set(valSplit).size === valSplit.length;
  },
};

/**
 * regr: regexp result
 */
export function regrLengthCheck(val, max = 32, min = 0) {
  const len = val.replace(/[\u0391-\uFFE5]/g, 'aa').length;
  return len >= min && len <= max;
}
