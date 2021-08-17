import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions } from '@/config/config';
import { ICloudSource } from '@/types/cloud/cloud';

export const editConfig: ISetupHead[] = [
  {
    label: 'IP地址',
    prop: 'inner_ip',
    type: 'text',
    required: true,
    noRequiredMark: false,
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
    ],
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
    default: -1,
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
      if (row.os_type === 'WINDOWS') {
        row.port = 445;
        row.account = 'Administrator';
      } else {
        row.port = defaultPort;
        row.account = 'root';
      }
    },
  },
  {
    label: '登录端口',
    prop: 'port',
    type: 'text',
    required: true,
    batch: true,
    default: defaultPort,
    rules: [
      {
        content: window.i18n.t('端口范围', { range: '0-65535' }),
        validator(value: string) {
          if (!value) return true;
          let portValidate =  /^[0-9]*$/.test(value);
          if (portValidate) {
            portValidate = parseInt(value, 10) <= 65535;
          }
          return portValidate;
        },
      },
    ],
    getReadonly(row: ISetupRow) {
      return row && row.os_type === 'WINDOWS';
    },
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
    default: 'PASSWORD',
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
        content: window.i18n.t('认证信息过期'),
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
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
    ],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: true,
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
    iconOffset: 40,
    placeholder: window.i18n.t('请输入'),
    rules: [
      {
        regx: '^[1-9]\\d*$',
        content: window.i18n.t('整数最小值校验提示', { min: 1 }),
      },
    ],
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
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
    ],
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
    default: -1,
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
      if (row.os_type === 'WINDOWS') {
        row.port = 445;
        row.account = 'Administrator';
      } else {
        row.port = defaultPort;
        row.account = 'root';
      }
    },
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    noRequiredMark: false,
    placeholder: window.i18n.t('请输入'),
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
    ],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: true,
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
    iconOffset: 40,
    placeholder: window.i18n.t('请输入'),
    rules: [
      {
        regx: '^[1-9]\\d*$',
        content: window.i18n.t('整数最小值校验提示', { min: 1 }),
      },
    ],
  },
  {
    label: '',
    prop: '',
    type: 'operate',
    width: 42,
  },
];
