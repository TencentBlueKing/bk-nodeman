import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions, defaultOsType, getDefaultConfig, addressingMode } from '@/config/config';
import { reguFnMinInteger, reguPort, reguIp, reguIpBatch, reguIpInLineRepeat, splitCodeArr } from '@/common/form-check';

const useTjj = window.PROJECT_CONFIG.USE_TJJ === 'True';

export const setupTableConfig: ISetupHead[] = [
  {
    label: 'IP地址',
    prop: 'inner_ip',
    type: 'textarea',
    required: true,
    splitCode: splitCodeArr,
    unique: true,
    noRequiredMark: false,
    placeholder: window.i18n.t('多ip输入提示'),
    width: '20%',
    errTag: true,
    rules: [
      reguIpBatch,
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
    getReadonly(row: ISetupRow, isDefaultCloud: Boolean) {
      return row && row.os_type === 'WINDOWS' && !isDefaultCloud;
    },
  },
  {
    label: '登录账号',
    prop: 'account',
    type: 'text',
    required: true,
    batch: true,
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
    getReadonly(row: ISetupRow) {
      return row.auth_type && row.auth_type === 'TJJ_PASSWORD';
    },
    getCurrentType(row: ISetupRow) {
      const auth = authentication.find(auth => auth.id === row.auth_type);
      return auth?.type || 'text';
    },
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    type: 'text',
    required: false,
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('请输入'),
    width: '15%',
    errTag: true,
    rules: [reguIp,
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
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', true),
    batch: true,
    required: false,
    show: true,
    noRequiredMark: false,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    batch: true,
    required: false,
    show: true,
    noRequiredMark: false,
    // appendSlot: 'MB/s',
    // iconOffset: 40,
    width: 180,
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
    width: 70,
  },
];

export const setupTableManualConfig = [
  {
    label: 'IP地址',
    prop: 'inner_ip',
    type: 'textarea',
    required: true,
    splitCode: splitCodeArr,
    unique: true,
    noRequiredMark: false,
    placeholder: window.i18n.t('多ip输入提示'),
    width: 'auto',
    errTag: true,
    rules: [
      reguIpBatch,
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
          const valueSplit = v.trim().split(splitCode)
            .filter(text => !!text);
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
    ],
  },
  {
    label: '操作系统',
    prop: 'os_type',
    type: 'select',
    batch: true,
    required: true,
    default: defaultOsType,
    width: 'auto',
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
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('请输入'),
    width: 'auto',
    errTag: true,
    rules: [reguIp,
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
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: getDefaultConfig(defaultOsType, 'peer_exchange_switch_for_agent', true),
    batch: true,
    required: false,
    show: true,
    noRequiredMark: false,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    batch: true,
    required: false,
    show: true,
    noRequiredMark: false,
    // appendSlot: 'MB/s',
    // iconOffset: 40,
    width: 180,
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
    width: 70,
  },
];
