import * as XLSX from 'xlsx';

interface IHead {
  name: string,
  prop: string
  optional?: boolean
  width?: number
}

export const headConfig: IHead[] = [
  { name: window.i18n.t('IP地址'), prop: 'inner_ip', width: 150 },
  { name: window.i18n.t('操作系统'), prop: 'os_type' },
  { name: window.i18n.t('安装通道'), prop: 'install_channel_id' },
  { name: window.i18n.t('登录端口'), prop: 'port' },
  { name: window.i18n.t('登录账号'), prop: 'account' },
  { name: window.i18n.t('认证方式'), prop: 'auth_type' },
  { name: window.i18n.t('密码密钥'), prop: 'prove' },
  { name: window.i18n.t('外网IP'), prop: 'outer_ip', optional: true, width: 150 },
  { name: window.i18n.t('登录IP'), prop: 'login_ip', optional: true, width: 150 },
  { name: window.i18n.t('业务'), prop: 'bk_biz_id', optional: true },
  { name: window.i18n.t('云区域'), prop: 'bk_cloud_id', optional: true },
  { name: window.i18n.t('接入点'), prop: 'ap_id', optional: true },
  { name: window.i18n.t('BT节点探测'), prop: 'peer_exchange_switch_for_agent', optional: true, width: 120 },
  { name: window.i18n.t('传输限速Unit'), prop: 'bt_speed_limit', optional: true, width: 140 },
  { name: window.i18n.t('寻址方式'), prop: 'bk_addressing', optional: true, width: 120 },
];

export const demoData = [
  {
    inner_ip: '1.1.1.1',
    os_type: 'LINUX',
    install_channel_id: 'default',
    port: '22',
    account: 'root',
    auth_type: window.i18n.t('密码'),
    prove: '123456',
    outer_ip: '1.1.1.1',
    login_ip: '',
    bk_biz_id: '蓝鲸',
    bk_cloud_id: '直连区域',
    ap_id: '自动选择',
    peer_exchange_switch_for_agent: 'TRUE',
    bt_speed_limit: '',
    bk_addressing: window.i18n.t('静态'),
  },
  {
    inner_ip: '1.1.1.2',
    os_type: 'WINDOWS',
    install_channel_id: 'default',
    port: '445',
    account: 'test',
    auth_type: '',
    prove: '66666',
    outer_ip: '',
    login_ip: '1.1.1.2',
    bk_biz_id: '蓝鲸',
    bk_cloud_id: '',
    ap_id: '',
    peer_exchange_switch_for_agent: '',
    bt_speed_limit: '3',
    bk_addressing: window.i18n.t('动态'),
  },
  {
    inner_ip: '1.1.1.3',
    os_type: 'LINUX',
    install_channel_id: 'default',
    port: '8080',
    account: 'root2',
    auth_type: window.i18n.t('密码'),
    prove: '8888888888',
    outer_ip: '',
    login_ip: '',
    bk_biz_id: '',
    bk_cloud_id: '直连区域',
    ap_id: '默认接入点',
    peer_exchange_switch_for_agent: 'FALSE',
    bt_speed_limit: '',
    bk_addressing: '',
  },
];

// 字符串转ArrayBuffer
export function s2ab(s) {
  const buf = new ArrayBuffer(s.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i !== s.length; ++i) view[i] = s.charCodeAt(i) & 0xFF;
  return buf;
}

// 参考 https://segmentfault.com/a/1190000021272653?sort=newest
export function createWorksheet(config: IHead[]) {
  try {
    const excelHead = config.map(th => (th.optional ? `${th.name}${window.i18n.t('可选')}` : th.name));

    const excelBody = demoData.map(demo => config.map(item => demo[item.prop] || null));
    const excelData = [excelHead, ...excelBody];
    const excelCols = config.map(item => ({
      wpx: item.width || 100,
    }));

    const worksheet = XLSX.utils.aoa_to_sheet(excelData);
    worksheet['!cols'] = excelCols; // 控制列样式
    return worksheet;
  } catch (err) {
    console.warn(err);
  }
}

export function createExcel(name: string, config: IHead[]) {
  const worksheet = createWorksheet(config);
  const workbook = {
    SheetNames: [name],
    Sheets: {
      [name]: worksheet,
    },
  };
  const workbookOption = {
    bookType: 'xlsx',
    bookSST: false, // 是否生成Shared String Table，官方解释是，如果开启生成速度会下降，但在低版本IOS设备上有更好的兼容性
    type: 'binary',
  };
  const excelBuffer = XLSX.write(workbook, workbookOption);
  const excelBlob = new Blob([s2ab(excelBuffer)], { type: 'application/octet-stream' });
  return {
    blob: excelBlob,
    url: URL.createObjectURL(excelBlob),
  };
}

export default {
  headConfig,
  createWorksheet,
  createExcel,
};
