import { ISetupHead, ISetupRow } from '@/types';
import { authentication, defaultPort, sysOptions } from '@/config/config';

const useTjj = window.PROJECT_CONFIG.USE_TJJ === 'True';
const splitCodeArr = ['\n', '，', ' ', '、', ','];

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
      {
        content: window.i18n.t('IP不符合规范'),
        validator(value: string) {
          if (!value) return true;
          const regx = new RegExp('^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$');
          const splitCode = splitCodeArr.find(split => value.indexOf(split) > 0);
          const valueSplit = value.split(splitCode).filter(text => !!text)
            .map(text => text.trim());
          // IP校验
          const ipValidate = valueSplit.some(item => !regx.test(item));
          return !ipValidate;
        },
      },
      {
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
        validator(value: string) {
          // 一个输入框内不能重复
          if (!value) return true;
          const splitCode = splitCodeArr.find(split => value.indexOf(split) > 0);
          const valueSplit = value.split(splitCode).filter(text => !!text)
            .map(text => text.trim());
          return new Set(valueSplit).size === valueSplit.length;
        },
      },
      {
        trigger: 'blur',
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
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
        content: '',
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
    default: 'LINUX',
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
    default: 'root',
  },
  {
    label: '认证方式',
    prop: 'auth_type',
    type: 'select',
    required: true,
    batch: true,
    default: 'PASSWORD',
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
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
      {
        trigger: 'blur',
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
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
    default: true,
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
    iconOffset: 40,
    width: 180,
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
      {
        content: window.i18n.t('IP不符合规范'),
        validator(value: string) {
          if (!value) return true;
          const regx = new RegExp('^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$');
          const splitCode = splitCodeArr.find(split => value.indexOf(split) > 0);
          const valueSplit = value.trim().split(splitCode)
            .filter(text => !!text);
          // IP校验
          const ipValidate = valueSplit.some(item => !regx.test(item));
          return !ipValidate;
        },
      },
      {
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
        validator(value: string) {
          // 一个输入框内不能重复
          if (!value) return true;
          const splitCode = splitCodeArr.find(split => value.indexOf(split) > 0);
          const valueSplit = value.trim().split(splitCode)
            .filter(text => !!text);
          return new Set(valueSplit).size === valueSplit.length;
        },
      },
      {
        trigger: 'blur',
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
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
        content: '',
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
    default: 'LINUX',
    width: 'auto',
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
    unique: true,
    noRequiredMark: true,
    placeholder: window.i18n.t('请输入'),
    width: 'auto',
    errTag: true,
    rules: [
      {
        regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
        content: window.i18n.t('IP不符合规范'),
      },
      {
        trigger: 'blur',
        content: window.i18n.t('冲突校验', { prop: 'IP' }),
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
    default: true,
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
    iconOffset: 40,
    width: 180,
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
    width: 70,
  },
];
