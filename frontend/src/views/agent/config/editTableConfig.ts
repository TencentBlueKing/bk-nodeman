import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions, defaultOsType, getDefaultConfig, addressingMode } from '@/config/config';
import { ICloudSource } from '@/types/cloud/cloud';
import { reguFnMinInteger, reguPort, reguIPMixins, reguIp } from '@/common/form-check';

export const editConfig: ISetupHead[] = [
  {
    label: 'IP地址',
    prop: 'inner_ip',
    type: 'text',
    required: true,
    noRequiredMark: false,
    rules: [reguIPMixins],
    readonly: true,
  },
  {
    label: '业务',
    prop: 'bk_biz_id',
    type: 'biz',
    required: true,
    multiple: false,
    noRequiredMark: false,
    readonly: true,
    placeholder: window.i18n.t('选择业务'),
  },
  {
    label: '云区域',
    prop: 'bk_cloud_id',
    type: 'select',
    required: true,
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions() {
      return this.cloudList.map((item: ICloudSource) => ({
        name: item.bk_cloud_name,
        id: item.bk_cloud_id,
      }));
    },
    getProxyStatus(row: ISetupRow) {
      return row.proxyStatus;
    },
    readonly: true,
  },
  {
    label: '安装通道',
    prop: 'install_channel_id',
    type: 'select',
    required: true,
    batch: true,
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions(row) {
      return row.bk_cloud_id || row.bk_cloud_id === 0
        ? this.channelList.filter(item => item.bk_cloud_id === row.bk_cloud_id || item.id === 'default')
        : this.channelList;
    },
  },
  {
    label: '接入点',
    prop: 'ap_id',
    type: 'select',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'ap_id', -1),
    options: [],
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions() {
      return this.apList;
    },
  },
  {
    label: '操作系统',
    prop: 'os_type',
    type: 'select',
    required: true,
    batch: true,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    options: sysOptions,
    getReadonly(row: ISetupRow) {
      return row.is_manual || /RELOAD_AGENT/ig.test(this.localMark);
    },
    handleValueChange(row: ISetupRow) {
      const osType = row.os_type || defaultOsType;
      row.port = getDefaultConfig(osType, 'port', osType === 'WINDOWS' ? 445 : defaultPort);
      row.account = getDefaultConfig(osType, 'account', osType === 'WINDOWS' ? 'Administrator' : 'root');
    },
  },
  {
    label: '登录端口',
    prop: 'port',
    type: 'text',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'port', defaultPort),
    rules: [reguPort],
    // getReadonly(row: ISetupRow) {
    //   return row && row.os_type === 'WINDOWS' && row.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD;
    // },
  },
  {
    label: '登录账号',
    prop: 'account',
    type: 'text',
    required: true,
    batch: true,
    placeholder: window.i18n.t('请输入'),
  },
  {
    label: '认证方式',
    prop: 'auth_type',
    type: 'select',
    required: true,
    batch: true,
    subTitle: window.i18n.t('密钥方式仅对Linux/AIX系统生效'),
    default: getDefaultConfig(defaultOsType, 'auth_type', 'PASSWORD'),
    getOptions(row: ISetupRow) {
      return row.os_type === 'WINDOWS' ? authentication.filter(auth => auth.id !== 'KEY') : authentication;
    },
    handleValueChange(row: ISetupRow) {
      const auth = authentication.find(auth => auth.id === row.auth_type);
      row.prove = auth?.default || '';
    },
  },
  {
    label: '密码密钥',
    prop: 'prove',
    type: 'password',
    required: false,
    show: true, // 常显项
    batch: true,
    noRequiredMark: false,
    subTitle: window.i18n.t('仅对密码认证生效'),
    placeholder: window.i18n.t('请输入'),
    rules: [
      {
        message: window.i18n.t('认证信息过期'),
        validator(v: string, id: number) {
          const row = this.table.data.find((row: ISetupRow) => row.id === id);
          const isValueEmpty = typeof v === 'undefined' || v === null || v === '';
          return !(isValueEmpty && row && (!row.is_manual && row.re_certification)); // 手动安装不需要校验密码过期
        },
      },
    ],
    getReadonly(row: ISetupRow) {
      return row.auth_type && row.auth_type === 'TJJ_PASSWORD';
    },
    getCurrentType(row: ISetupRow) {
      const auth = authentication.find(auth => auth.id === row.auth_type);
      return auth?.type || 'text';
    },
    getDefaultValue(row: ISetupRow) {
      if (row.auth_type === 'TJJ_PASSWORD') {
        return window.i18n.t('自动选择');
      }
      return '';
    },
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    noRequiredMark: false,
    placeholder: window.i18n.t('请输入'),
    rules: [reguIp],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', true),
    batch: true,
    required: false,
    noRequiredMark: false,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    batch: true,
    required: false,
    noRequiredMark: false,
    // appendSlot: 'MB/s',
    // iconOffset: 40,
    placeholder: window.i18n.t('请输入'),
    rules: [reguFnMinInteger(1)],
  },
  {
    label: '寻址方式',
    prop: 'bk_addressing',
    type: 'select',
    default: '0',
    batch: true,
    required: false,
    noRequiredMark: false,
    getOptions() {
      return addressingMode;
    },
    width: 115,
  },
  {
    label: '',
    prop: '',
    type: 'operate',
    width: 42,
  },
];

export const editManualConfig = [
  {
    label: 'IP地址',
    prop: 'inner_ip',
    type: 'text',
    required: true,
    noRequiredMark: false,
    rules: [reguIPMixins],
    readonly: true,
  },
  {
    label: '业务',
    prop: 'bk_biz_id',
    type: 'biz',
    required: true,
    multiple: false,
    noRequiredMark: false,
    readonly: true,
  },
  {
    label: '云区域',
    prop: 'bk_cloud_id',
    type: 'select',
    required: true,
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions() {
      return this.cloudList.map((item: ICloudSource) => ({
        name: item.bk_cloud_name,
        id: item.bk_cloud_id,
      }));
    },
    getProxyStatus(row: ISetupRow) {
      return row.proxyStatus;
    },
    readonly: true,
  },
  {
    label: '安装通道',
    prop: 'install_channel_id',
    type: 'select',
    required: true,
    batch: true,
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions(row) {
      return row.bk_cloud_id || row.bk_cloud_id === 0
        ? this.channelList.filter(item => item.bk_cloud_id === row.bk_cloud_id || item.id === 'default')
        : this.channelList;
    },
  },
  {
    label: '接入点',
    prop: 'ap_id',
    type: 'select',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'ap_id', -1),
    options: [],
    popoverMinWidth: 160,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    getOptions() {
      return this.apList;
    },
  },
  {
    label: '操作系统',
    prop: 'os_type',
    type: 'select',
    required: true,
    batch: true,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    options: sysOptions,
    handleValueChange(row: ISetupRow) {
      const osType = row.os_type || defaultOsType;
      row.port = getDefaultConfig(osType, 'port', osType === 'WINDOWS' ? 445 : defaultPort);
      row.account = getDefaultConfig(osType, 'account', osType === 'WINDOWS' ? 'Administrator' : 'root');
    },
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    noRequiredMark: false,
    placeholder: window.i18n.t('请输入'),
    rules: [reguIp],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', true),
    batch: true,
    required: false,
    noRequiredMark: false,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    batch: true,
    required: false,
    noRequiredMark: false,
    // appendSlot: 'MB/s',
    // iconOffset: 40,
    placeholder: window.i18n.t('请输入'),
    rules: [reguFnMinInteger(1)],
  },
  {
    label: '寻址方式',
    prop: 'bk_addressing',
    type: 'select',
    default: '0',
    batch: true,
    required: false,
    noRequiredMark: false,
    getOptions() {
      return addressingMode;
    },
    width: 115,
  },
  {
    label: '',
    prop: '',
    type: 'operate',
    width: 42,
  },
];
