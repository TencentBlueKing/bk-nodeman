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
  },
  {
    prop: 'port',
    label: window.i18n.t('登录端口'),
    type: 'text',
    readonly: true,
  },
  {
    prop: 'login_ip',
    label: window.i18n.t('登录IP'),
    type: 'text',
    readonly: true,
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
