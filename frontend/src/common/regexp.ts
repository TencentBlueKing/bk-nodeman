// 不包含i18n

export const splitCodeArr = ['\n', '，', ' ', '、', ','];
export const IpStr = '((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)';
export const IPv6Str = '(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]).){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(,(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])))*';


export const protocolStr = '(?:http(s)?://)?'; // 协议
export const domainStr = '[\\w-]+(\\.[\\w-]+){1,}'; // 普通domain
export const hostnameStr = `((${domainStr})|${IpStr}|\\[(${IPv6Str})\\])`; // 整合了IP校验的domain
export const portStr = '(:(\\d){1,5})?'; // 端口校验不严谨
export const pathnameStr = '(?:/\\S*)?'; // 按需调整

/**
 * reg: regexp instance
 */
export const regIp = new RegExp(`^${IpStr}$`);
export const regFilterIp = new RegExp(`^(?:\\d+:)?(${IpStr})$`);
export const regExclusiveFilterIp = new RegExp(`^\\d+:${IpStr}$`);
export const regIPv6 = new RegExp(`^${IPv6Str}$`);
export const regIpMixin = window.$DHCP ? new RegExp(`^${IpStr}$|^${IPv6Str}$`) : regIp; // 区分环境可用的IP类型
export const regFilterIpMixin = window.$DHCP ? new RegExp(`^(?:\\d+:)?(${IpStr}|${IPv6Str})$`) : regFilterIp;
export const regExclusiveFilterIpMixin = window.$DHCP ? new RegExp(`^\\d+:(${IpStr}|${IPv6Str})$`) : regExclusiveFilterIp; // 用于区分IP还是按管控区域筛选ip
export const regUrl = /^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w.-]+)+[\w\-._~:/?#[\]@!$&'*+,;=.]+$/;
export const regUrlMixinIp = new RegExp(`^${protocolStr}${hostnameStr}${portStr}${pathnameStr}$`);
export const regNormalText = /^[\u4e00-\u9fa5A-Za-z0-9-_]+$/;
export const regNaturalNumber = /^(0|[1-9][0-9]*)$/; // 自然数 | 非负整数
export const regInteger = /^-?\d+$/; // 整数
export function regFnFileType(type: string) { // 文件类型
  return new RegExp(`^.+(.${type})$`);
}
export function regFnSysPath(params?: { [key: string]: number | string } = {}) {
  const { minText = 1, maxText = 16, minLevel = 1, type = 'linux' } = params;
  const regText = type === 'linux'
    ? `^(/[A-Za-z0-9_]{${minText},${maxText}}){${minLevel},}$`
    : `^([c-zC-Z]:)(\\\\[A-Za-z0-9_]{${minText},${maxText}}){${minLevel},}$`;
  return new RegExp(regText);
}
