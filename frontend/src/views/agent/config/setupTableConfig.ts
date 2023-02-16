import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions, defaultOsType, getDefaultConfig, addressingMode, enableDHCP, DHCP_FILTER_KEYS } from '@/config/config';
import { reguFnMinInteger, reguPort, reguIPv4Batch, reguIPv6Batch, reguIpMixinsBatch, reguIpInLineRepeat } from '@/common/form-check';
import { splitCodeArr } from '@/common/regexp';

const useTjj = window.PROJECT_CONFIG.USE_TJJ === 'True';

export const parentHead = [
  { label: '主机IPTip', prop: 'host_ip', type: 'text', colspan: 0, required: true, tips: 'agentSetupHostIp' },
  { label: '主机属性', prop: 'host_attr', type: 'text', colspan: 0 },
  { label: '登录信息', prop: 'login_info', type: 'text', tips: 'agentSetupLoginInfo', colspan: 0 },
  { label: '传输信息', prop: 'trans_info', type: 'text', colspan: 0 },
  { label: '', prop: '', type: 'operate' },
];

const config: ISetupHead[] = [
  {
    label: '内网IPv4',
    prop: 'inner_ip',
    reprop: 'inner_ipv6',
    requiredPick: ['inner_ipv6'],
    type: 'textarea',
    required: true,
    splitCode: splitCodeArr,
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('多ip输入提示'),
    width: '20%',
    errTag: true,
    // tips: 'agentSetupInnerIp',
    parentProp: 'host_ip',
    sync: 'login_ip',
    manualProp: true,
    rules: [
      reguIPv4Batch,
      reguIpInLineRepeat,
      {
        trigger: 'blur',
        message: window.i18n.t('冲突校验', { prop: 'IP' }),
        validator(v: string, id: number) {
          // 与其他输入框的值不能重复
          if (!v) return true;
          const row = this.table.data.find((item: ISetupRow) => item.id === id);
          if (!row) return;
          return this.handleValidateUnique(row, {
            prop: 'inner_ip',
            splitCode: splitCodeArr,
          });
        },
      },
      {
        trigger: 'blur',
        message: '',
        async validator(v: string, id: number) {
          if (!useTjj) return true;
          // 铁将军校验
          const splitCode = splitCodeArr.find(split => v.indexOf(split) > 0);
          const valueSplit = v.split(splitCode).filter(text => !!text)
            .map(text => text.trim());
          const data = await this.fetchPwd({
            hosts: valueSplit,
          });
          if (data && data.success_ips.length === valueSplit.length) {
            const row = this.table.data.find((item: ISetupRow) => item.id === id);
            if (!row) return true;
            if (row.os_type === 'LINUX') {
              row.port = 36000;
            }
            row.auth_type = 'TJJ_PASSWORD';
          }
          return true;
        },
      },
      {
        trigger: 'blur',
        message: window.i18n.t('IP数量不一致'),
        validator(v: string, id: number) {
          if (!v) return true;
          const row = this.table.data.find((item: ISetupRow) => item.id === id);
          if (!row) return;
          return this.handleValidateEqual(row, {
            prop: 'inner_ip',
            reprop: 'inner_ipv6',
            splitCode: splitCodeArr,
          });
        },
      },
    ],
  },
  {
    label: '内网IPv6',
    prop: 'inner_ipv6',
    reprop: 'inner_ip',
    requiredPick: ['inner_ip'],
    type: 'textarea',
    required: true,
    splitCode: splitCodeArr,
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('多ip输入提示'),
    width: '20%',
    errTag: true,
    // tips: 'agentSetupInnerIPv6',
    parentProp: 'host_ip',
    // sync: 'login_ip',
    manualProp: true,
    rules: [
      reguIPv6Batch,
      reguIpInLineRepeat,
      {
        trigger: 'blur',
        message: window.i18n.t('冲突校验', { prop: 'IP' }),
        validator(v: string, id: number) {
          // 与其他输入框的值不能重复
          if (!v) return true;
          const row = this.table.data.find((item: ISetupRow) => item.id === id);
          if (!row) return;
          return this.handleValidateUnique(row, {
            prop: 'inner_ipv6',
            splitCode: splitCodeArr,
          });
        },
      },
      {
        trigger: 'blur',
        message: window.i18n.t('IP数量不一致'),
        validator(v: string, id: number) {
          if (!v) return true;
          const row = this.table.data.find((item: ISetupRow) => item.id === id);
          if (!row) return;
          return this.handleValidateEqual(row, {
            prop: 'inner_ipv6',
            reprop: 'inner_ip',
            splitCode: splitCodeArr,
          });
        },
      },
    ],
  },
  {
    label: '操作系统',
    prop: 'os_type',
    type: 'select',
    batch: true,
    required: true,
    default: defaultOsType,
    options: sysOptions,
    parentProp: 'host_attr',
    manualProp: true,
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
    getOptions() {
      return addressingMode;
    },
    width: 115,
    manualProp: true,
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    splitCode: splitCodeArr,
    default: '',
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('请输入'),
    width: '15%',
    errTag: true,
    tips: 'agentSetupLoginIp',
    parentProp: 'login_info',
    manualProp: true,
    rules: [
      reguIpMixinsBatch,
      {
        trigger: 'blur',
        message: window.i18n.t('冲突校验', { prop: 'IP' }),
        validator(v: string, id: number) {
          // 与其他输入框的值不能重复
          if (!v) return true;
          const row = this.table.data.find((item: ISetupRow) => item.id === id);
          return this.handleValidateUnique(row, {
            prop: 'login_ip',
          });
        },
      },
    ],
  },
  {
    label: '登录端口',
    prop: 'port',
    type: 'text',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'port', defaultPort),
    rules: [reguPort],
    tips: 'agentSetupPort',
    parentProp: 'login_info',
    // getReadonly(row: ISetupRow, isDefaultCloud: Boolean) {
    //   return row && row.os_type === 'WINDOWS' && !isDefaultCloud;
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
    default: getDefaultConfig(defaultOsType, 'account', 'root'),
  },
  {
    label: '认证方式',
    prop: 'auth_type',
    type: 'select',
    required: true,
    batch: true,
    default: getDefaultConfig(defaultOsType, 'auth_type', 'PASSWORD'),
    subTitle: window.i18n.t('密钥方式仅对Linux/AIX系统生效'),
    parentProp: 'login_info',
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
    required: true,
    prop: 'prove',
    type: 'password',
    batch: true,
    subTitle: window.i18n.t('仅对密码认证生效'),
    parentProp: 'login_info',
    tips: 'agentSetupKey',
    getReadonly(row: ISetupRow) {
      return row.auth_type && row.auth_type === 'TJJ_PASSWORD';
    },
    getCurrentType(row: ISetupRow) {
      const auth = authentication.find(auth => auth.id === row.auth_type);
      return auth?.type || 'text';
    },
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: 'BT节点探测提示',
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', true),
    batch: true,
    required: false,
    // show: true,
    noRequiredMark: false,
    width: 115,
    parentProp: 'trans_info',
    manualProp: true,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    batch: true,
    required: false,
    // show: true,
    noRequiredMark: false,
    // appendSlot: 'MB/s',
    // iconOffset: 40,
    width: 180,
    parentProp: 'trans_info',
    rules: [reguFnMinInteger(1)],
    manualProp: true,
  },
  {
    label: '',
    prop: '',
    type: 'operate',
    width: 70,
    manualProp: true,
  },
];

export const setupTableConfig = enableDHCP
  ? config
  : config.filter(item => !DHCP_FILTER_KEYS.includes(item.prop));

export const setupDiffConfigs = {
  inner_ip: {
    width: 'auto%',
  },
  os_type: {
    width: 'auto',
  },
  login_ip: {
    width: 'auto',
  },
};
