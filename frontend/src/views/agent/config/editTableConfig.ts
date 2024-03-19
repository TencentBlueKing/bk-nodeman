import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions, defaultOsType, getDefaultConfig, addressingMode, DHCP_FILTER_KEYS } from '@/config/config';
import { ICloudSource } from '@/types/cloud/cloud';
import { reguFnMinInteger, reguPort, reguIPMixins, reguIp, reguIPv6 } from '@/common/form-check';

export const config: ISetupHead[] = [
  {
    label: '业务',
    prop: 'bk_biz_id',
    type: 'biz',
    required: true,
    multiple: false,
    noRequiredMark: false,
    parentProp: 'biz_attr',
    readonly: true,
    placeholder: window.i18n.t('选择业务'),
    manualProp: true,
  },
  {
    label: '管控区域',
    prop: 'bk_cloud_id',
    type: 'select',
    required: true,
    popoverMinWidth: 160,
    noRequiredMark: false,
    parentProp: 'cloud_attr',
    placeholder: window.i18n.t('请选择'),
    manualProp: true,
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
    parentProp: 'cloud_attr',
    placeholder: window.i18n.t('请选择'),
    manualProp: true,
    handleValueChange(row) {
      if (row.install_channel_id !== 'default' && row.bk_cloud_id === window.PROJECT_CONFIG.DEFAULT_CLOUD) {
        row.ap_id = this.apList.find(item => item.id !== -1)?.id || '';
      }
    },
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
    // batch: true,
    default: getDefaultConfig(defaultOsType, 'ap_id', -1),
    options: [],
    popoverMinWidth: 160,
    noRequiredMark: false,
    parentProp: 'cloud_attr',
    placeholder: window.i18n.t('请选择'),
    manualProp: true,
    getBatch() {
      return !window.PROJECT_CONFIG?.ENABLE_AP_VERSION_MUTEX
        || window.PROJECT_CONFIG?.ENABLE_AP_VERSION_MUTEX !== 'True'
        || this.table?.data?.every(row => row.gse_version === 'V1');
    },
    getOptions(oldRow) {
      let row = oldRow;
      if (window.PROJECT_CONFIG?.ENABLE_AP_VERSION_MUTEX === 'True') {
        // getBatch 能确认是表格数据是否展示（同一类数据）, 如果展示, 则取第一个做操作
        if (!row.id) {
          row = this.table?.data?.[0] || {};
        }
        if (!row.id) {
          return [];
        }
        const gseVersion = row.gse_version;
        const list = this.apList.map((item) => {
          const disabled = gseVersion !== item.gse_version
            || (item.id === -1
              && (row.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD
                || row.install_channel_id !== 'default'));
          return {
            ...item,
            tip: disabled
              ? window.i18n.t('接入点互斥', gseVersion === 'V1' ? ['1.0', '2.0'] : ['2.0', '1.0'])
              : '',
            disabled,
          };
        });
        list.sort(p => (p.disabled ? 1 : -1));
        return list;
      }
      return this.apList.map(item => ({
        ...item,
        disabled: item.id === -1
          && (row.bk_cloud_id !== window.PROJECT_CONFIG.DEFAULT_CLOUD || row.install_channel_id !== 'default'),
      }));
    },
  },
  {
    label: '内网IPv4',
    prop: 'inner_ip',
    type: 'text',
    required: true,
    requiredPick: ['inner_ipv6'],
    noRequiredMark: true,
    rules: [reguIp],
    parentProp: 'host_ip',
    sync: 'login_ip',
    readonly: true,
    manualProp: true,
    placeholder: '--',
  },
  {
    label: '内网IPv6',
    prop: 'inner_ipv6',
    type: 'text',
    requiredPick: ['inner_ip'],
    required: true,
    noRequiredMark: true,
    rules: [reguIPv6],
    parentProp: 'host_ip',
    readonly: true,
    manualProp: true,
    placeholder: '--',
  },
  {
    label: '操作系统',
    prop: 'os_type',
    type: 'select',
    required: true,
    batch: true,
    noRequiredMark: false,
    parentProp: 'host_attr',
    placeholder: window.i18n.t('请选择'),
    options: sysOptions,
    manualProp: true,
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
    label: '寻址方式',
    prop: 'bk_addressing',
    type: 'select',
    default: 'static',
    batch: true,
    required: false,
    noRequiredMark: false,
    parentProp: 'host_attr',
    manualProp: true,
    getOptions() {
      return addressingMode;
    },
    getReadonly() {
      return /REINSTALL_AGENT/ig.test(this.localMark);
    },
    getBatch() {
      return !/REINSTALL_AGENT/ig.test(this.localMark);
    },
    width: 90,
  },
  {
    label: '登录端口',
    prop: 'port',
    type: 'text',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'port', defaultPort),
    tips: 'agentSetupPort',
    parentProp: 'login_info',
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
    tips: 'agentSetupLoginAccount',
    parentProp: 'login_info',
    placeholder: window.i18n.t('请输入'),
  },
  {
    label: '认证方式',
    prop: 'auth_type',
    type: 'select',
    required: true,
    batch: true,
    subTitle: window.i18n.t('密钥方式仅对Linux/AIX系统生效'),
    parentProp: 'login_info',
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
    label: '密码/密钥',
    prop: 'prove',
    type: 'password',
    required: false,
    show: true, // 常显项
    batch: true,
    noRequiredMark: false,
    tips: 'agentSetupKey',
    parentProp: 'login_info',
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
      return row.prove || '';
    },
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    noRequiredMark: false,
    tips: 'agentSetupLoginIp',
    parentProp: 'login_info',
    placeholder: window.i18n.t('请输入'),
    manualProp: true,
    rules: [reguIPMixins],
  },
  {
    label: 'Agent 包版本',
    prop: 'version',
    type: 'choose',
    required: true,
    readonly: false,
    noRequiredMark: false,
    placeholder: window.i18n.t('请选择'),
    batch: false,
    default: '',
    width: 100,
    parentProp: 'install_info',
    getReadonly() {
      return this.type === 'UNINSTALL_AGENT';
    },
    // rules: [reguPort],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: 'BT节点探测提示',
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', false),
    batch: true,
    required: false,
    noRequiredMark: false,
    width: 90,
    parentProp: 'trans_info',
    manualProp: true,
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
    parentProp: 'trans_info',
    manualProp: true,
  },
  {
    label: '数据压缩',
    prop: 'enable_compression',
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'enable_compression', false),
    tips: '数据压缩tip',
    batch: true,
    required: false,
    noRequiredMark: false,
    width: 90,
    parentProp: 'trans_info',
    manualProp: true,
  },
  {
    label: '',
    prop: '',
    type: 'operate',
    width: 42,
    manualProp: true,
  },
];

export const editConfig = $DHCP
  ? config
  : config.filter(item => !DHCP_FILTER_KEYS.includes(item.prop));
