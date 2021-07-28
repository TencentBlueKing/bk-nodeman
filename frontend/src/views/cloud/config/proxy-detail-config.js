export const detailConfig = [
  {
    prop: 'bk_cloud_id',
    label: window.i18n.t('云区域ID'),
    readonly: true,
  },
  {
    prop: 'bk_biz_name',
    label: window.i18n.t('归属业务'),
    readonly: true,
  },
  {
    prop: 'inner_ip',
    label: window.i18n.t('内网IP'),
    type: 'text',
    readonly: true,
    validation: {
      regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
      content: window.i18n.t('IP不符合规范'),
    },
  },
  {
    prop: 'account',
    label: window.i18n.t('登录账号'),
    type: 'text',
    readonly: true,
  },
  {
    prop: 'outer_ip',
    label: window.i18n.t('数据传输IP'),
    tip: window.i18n.t('数据传输IP提示'),
    type: 'text',
    readonly: true,
    validation: {
      regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
      content: window.i18n.t('IP不符合规范'),
    },
  },
  {
    prop: 'port',
    label: window.i18n.t('登录端口'),
    type: 'text',
    readonly: true,
    validation: {
      content: window.i18n.t('端口范围', { range: '0-65535' }),
      validator(value) {
        if (!value) return true;
        let portValidate =  /^[0-9]*$/.test(value);
        if (portValidate) {
          portValidate = parseInt(value, 10) <= 65535;
        }
        return portValidate;
      },
    },
  },
  {
    prop: 'login_ip',
    label: window.i18n.t('登录IP'),
    type: 'text',
    readonly: true,
    validation: {
      regx: '^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$',
      content: window.i18n.t('IP不符合规范'),
    },
  },
  {
    prop: 'auth_type',
    label: window.i18n.t('认证方式'),
    type: 'auth',
    readonly: true,
  },
  {
    prop: 'peer_exchange_switch_for_agent',
    label: window.i18n.t('BT节点探测'),
    tips: window.i18n.t('BT节点探测提示'),
    type: 'tag-switch',
    readonly: true,
  },
  {
    prop: 'bt_speed_limit',
    label: window.i18n.t('传输限速'),
    type: 'text',
    unit: 'MB/s',
    readonly: true,
  },
];

export default detailConfig;
