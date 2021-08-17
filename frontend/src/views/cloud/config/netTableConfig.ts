import { authentication } from '@/config/config';
import { ISetupHead, ISetupRow } from '@/types';

export const setupInfo: ISetupHead[] = [
  {
    label: '内网IP',
    prop: 'inner_ip',
    tips: window.i18n.t('内网IP提示'),
    required: true,
    type: 'text',
    unique: true,
    errTag: true,
    iconOffset: 10,
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
            prop: 'inner_ip',
            splitCode: ['，', ' ', '、', ','],
          });
        },
      },
    ],
  },
  {
    label: '数据传输IP',
    prop: 'outer_ip',
    tips: window.i18n.t('数据传输IP提示'),
    type: 'text',
    unique: true,
    errTag: true,
    required: true,
    iconOffset: 10,
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
            prop: 'outer_ip',
            splitCode: ['，', ' ', '、', ','],
          });
        },
      },
    ],
  },
  {
    label: '登录IP',
    prop: 'login_ip',
    tips: window.i18n.t('登录IP提示'),
    type: 'text',
    required: true,
    unique: true,
    errTag: true,
    iconOffset: 10,
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
            splitCode: ['，', ' ', '、', ','],
          });
        },
      },
    ],
  },
  {
    label: '认证方式',
    prop: 'auth_type',
    type: 'select',
    required: true,
    default: 'PASSWORD',
    iconOffset: 10,
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
    subTitle: window.i18n.t('仅对密码认证生效'),
    iconOffset: 10,
    getReadonly(row: ISetupRow) {
      return row.auth_type && row.auth_type === 'TJJ_PASSWORD';
    },
    getCurrentType(row: ISetupRow) {
      const auth = authentication.find(auth => auth.id === row.auth_type);
      return auth?.type || 'text';
    },
  },
  {
    label: '临时文件目录',
    prop: 'data_path',
    tips: window.i18n.t('供proxy文件分发临时使用后台定期进行清理建议预留至少磁盘空间'),
    type: 'text',
    required: true,
    show: true,
    iconOffset: 10,
    width: 160,
    rules: [
      {
        regx: '^(/[A-Za-z0-9_]{1,16}){1,}$',
        content: window.i18n.t('Linux路径格式不正确'),
      },
    ],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: true,
    required: false,
    show: true,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    required: false,
    show: true,
    // appendSlot: 'MB/s',
    iconOffset: 45,
    width: 120,
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

export const setupManualInfo: ISetupHead[] = [
  {
    label: '内网IP',
    prop: 'inner_ip',
    tips: window.i18n.t('内网IP提示'),
    required: true,
    type: 'text',
    unique: true,
    errTag: true,
    iconOffset: 10,
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
            prop: 'inner_ip',
            splitCode: ['，', ' ', '、', ','],
          });
        },
      },
    ],
  },
  {
    label: '数据传输IP',
    prop: 'outer_ip',
    tips: window.i18n.t('数据传输IP提示'),
    type: 'text',
    unique: true,
    errTag: true,
    required: true,
    iconOffset: 10,
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
            prop: 'outer_ip',
            splitCode: ['，', ' ', '、', ','],
          });
        },
      },
    ],
  },
  {
    label: '临时文件目录',
    prop: 'data_path',
    tips: window.i18n.t('供proxy文件分发临时使用后台定期进行清理建议预留至少磁盘空间'),
    type: 'text',
    required: true,
    show: true,
    iconOffset: 10,
    width: 240,
    rules: [
      {
        regx: '^(/[A-Za-z0-9_]{1,16}){1,}$',
        content: window.i18n.t('Linux路径格式不正确'),
      },
    ],
  },
  {
    label: 'BT节点探测',
    prop: 'peer_exchange_switch_for_agent',
    tips: window.i18n.t('BT节点探测提示'),
    type: 'switcher',
    default: true,
    required: false,
    show: true,
    width: 115,
  },
  {
    label: '传输限速Unit',
    prop: 'bt_speed_limit',
    type: 'text',
    required: false,
    show: true,
    // appendSlot: 'MB/s',
    iconOffset: 45,
    width: 160,
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
    local: true,
  },
];
