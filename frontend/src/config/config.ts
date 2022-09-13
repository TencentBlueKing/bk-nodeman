import { MainStore } from '@/store';

export interface IAuth {
  id: string
  name: string
  disabled?: boolean
  type: string
  readonly?: boolean
  default?: string
}

const getAuthentication = () => {
  const auths: IAuth[] = [
    {
      id: 'PASSWORD',
      name: window.i18n.t('密码'),
      disabled: false,
      type: 'password',
    },
    {
      id: 'KEY',
      name: window.i18n.t('密钥'),
      disabled: false,
      type: 'file',
    },
  ];
  // 内部版才有铁将军
  if (window.PROJECT_CONFIG.USE_TJJ === 'True') {
    auths.push({
      id: 'TJJ_PASSWORD',
      name: window.i18n.t('铁将军IEG'),
      readonly: true,
      default: window.i18n.t('自动拉取'),
      type: 'text',
    });
  }
  return auths;
};
export const enableDHCP = window.PROJECT_CONFIG.BKAPP_ENABLE_DHCP === 'True';
export const addressingMode = [
  { id: '0', name: window.i18n.t('静态') },
  { id: '1', name: window.i18n.t('动态') },
];

export const authentication = getAuthentication();
export const defaultPort = window.PROJECT_CONFIG.DEFAULT_SSH_PORT ? Number(window.PROJECT_CONFIG.DEFAULT_SSH_PORT) : 22;
export const sysOptions = MainStore.osList;
export const defaultOsType = 'LINUX';
export const getDefaultConfig = (type: string, key: string, value?: any) => {
  const osConfig: Dictionary = MainStore.installDefaultValues[type];
  return osConfig && Object.prototype.hasOwnProperty.call(osConfig, key) ? osConfig[key] : value;
};
export const getConfigRemark = (key: string, os?: string) => {
  if (os) {
    const osConfig: Dictionary = MainStore.installDefaultValues[os];
    return osConfig[key] || MainStore.installDefaultValues[key] || '';
  }
  return MainStore.installDefaultValues[key] || '';
};
export const passwordFill = '********';

export default authentication;
