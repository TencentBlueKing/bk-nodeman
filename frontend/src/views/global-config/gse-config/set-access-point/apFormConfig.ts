import { reguFnSysPath, reguNaturalNumber, reguRequired } from '@/common/form-check';

export const stepHost = [
  {
    label: window.i18n.t('接入点名称'),
    key: 'name',
    required: true,
    ruleName: 'name',
    placeholder: window.i18n.t('用户创建的接入点'),
  },
  {
    label: window.i18n.t('接入点说明'),
    key: 'description',
    type: 'textarea',
    rows: 4,
    maxLength: 100,
    placeholder: window.i18n.t('接入点说明placeholder'),
    inputExtCls: 'bg-white textarea-description',
  },
  {
    label: window.i18n.t('区域'),
    key: 'region_id',
    required: true,
    ruleName: 'required',
    placeholder: window.i18n.t('请输入'),
  },
  {
    label: window.i18n.t('城市'),
    key: 'city_id',
    required: true,
    ruleName: 'required',
    placeholder: window.i18n.t('请输入'),
  },
  {
    label: window.i18n.t('Zookeeper用户名'),
    key: 'zk_account',
    placeholder: window.i18n.t('请输入'),
    extCls: 'mt40',
  },
  {
    type: 'zkPassword',
  },
  // zk 相关
  {
    type: 'zk',
  },
  {
    type: 'url',
    items: [
      {
        label: window.i18n.t('回调地址'),
        prepend: window.i18n.t('内网URL'),
        key: 'callback_url',
        ruleName: 'callback',
        placeholder: window.i18n.t('请输入内网回调地址'),
        extCls: 'mt20',
      },
      {
        label: '',
        prepend: window.i18n.t('外网URL'),
        key: 'outer_callback_url',
        ruleName: 'callback',
        placeholder: window.i18n.t('请输入外网回调地址'),
        extCls: 'mt10',
      },
    ],
  },
  {
    type: 'url',
    items: [
      {
        label: window.i18n.t('Agent安装包地址'),
        prepend: window.i18n.t('内网URL'),
        required: true,
        key: 'package_inner_url',
        ruleName: 'url',
        placeholder: window.i18n.t('请输入内网下载URL'),
        extCls: 'mt20',
      },
      {
        label: '',
        prepend: window.i18n.t('外网URL'),
        required: true,
        key: 'package_outer_url',
        ruleName: 'url',
        placeholder: window.i18n.t('请输入外网下载URL'),
        extCls: 'mt10 hide-require',
      },
    ],
  },
  {
    label: window.i18n.t('Agent包服务器目录'),
    key: 'nginx_path',
    ruleName: 'nginxPath',
    placeholder: window.i18n.t('请输入服务器目录'),
    extCls: 'mt20',
  },
  // 可用性测试
  {
    type: 'usability',
  },
];

export const apAgentInfo = [
  {
    type: 'linux',
    title: window.i18n.t('Agent信息Linux'),
    children: [
      { label: window.i18n.t('hostid路径'), required: true, prop: 'linuxHostidPath', rules: 'linuxPath' },
      { label: 'dataipc', required: true, prop: 'linuxDataipc', rules: 'linuxDataipc' },
      { label: window.i18n.t('安装路径'), required: true, prop: 'linuxSetupPath', rules: 'linuxInstallPath' },
      { label: window.i18n.t('数据文件路径'), required: true, prop: 'linuxDataPath', rules: 'linuxPath' },
      { label: window.i18n.t('运行时路径'), required: true, prop: 'linuxRunPath', rules: 'linuxPath' },
      { label: window.i18n.t('日志文件路径'), required: true, prop: 'linuxLogPath', rules: 'linuxPath' },
      { label: window.i18n.t('临时文件路径'), required: true, prop: 'linuxTempPath', rules: 'linuxPath' },
    ],
  },
  {
    type: 'windows',
    title: window.i18n.t('Agent信息Windows'),
    children: [
      { label: window.i18n.t('hostid路径'), required: true, prop: 'windowsHostidPath', rules: 'winPath' },
      { label: 'dataipc', required: true, prop: 'windowsDataipc', rules: 'winDataipc', placeholder: window.i18n.t('请输入不小于零的整数') },
      { label: window.i18n.t('安装路径'), required: true, prop: 'windowsSetupPath', rules: 'winInstallPath' },
      { label: window.i18n.t('数据文件路径'), required: true, prop: 'windowsDataPath', rules: 'winPath' },
      { label: window.i18n.t('运行时路径'), required: true, prop: 'windowsRunPath', rules: 'winPath' },
      { label: window.i18n.t('日志文件路径'), required: true, prop: 'windowsLogPath', rules: 'winPath' },
      { label: window.i18n.t('临时文件路径'), required: true, prop: 'windowsTempPath', rules: 'winPath' },
    ],
  },
];

// 目录名可以包含但不相等，所以末尾加了 /, 校验的时候给值也需要加上 /
export const linuxNotInclude = [
  '/etc/', '/root/', '/boot/', '/dev/', '/sys/', '/tmp/', '/var/', '/usr/lib/',
  '/usr/lib64/', '/usr/include/', '/usr/local/etc/', '/usr/local/sa/', '/usr/local/lib/',
  '/usr/local/lib64/', '/usr/local/bin/', '/usr/local/libexec/', '/usr/local/sbin/',
];
export const linuxNotIncludeError = [
  '/etc', '/root', '/boot', '/dev', '/sys', '/tmp', '/var', '/usr/lib',
  '/usr/lib64', '/usr/include', '/usr/local/etc', '/usr/local/sa', '/usr/local/lib',
  '/usr/local/lib64', '/usr/local/bin', '/usr/local/libexec', '/usr/local/sbin',
];
// 转换为正则需要四个 \
const winNotInclude = [
  'C:\\\\Windows\\\\', 'C:\\\\Windows\\\\', 'C:\\\\config\\\\',
  'C:\\\\Users\\\\', 'C:\\\\Recovery\\\\',
];
const winNotIncludeError = ['C:\\Windows', 'C:\\Windows', 'C:\\config', 'C:\\Users', 'C:\\Recovery'];

export const apAgentInfoRules = {
  linuxDataipc: [reguRequired,
    {
      validator(val: string) {
        return /^(\/[A-Za-z0-9_.]{1,}){1,}$/.test(val);
      },
      message: window.i18n.t('LinuxIpc校验不正确'),
      trigger: 'blur',
    },
  ],
  winDataipc: [reguRequired, reguNaturalNumber],
  winPath: [reguRequired, reguFnSysPath({ type: 'windows' })],
  linuxPath: [reguRequired, reguFnSysPath()],
  linuxInstallPath: [reguRequired, reguFnSysPath({ minLevel: 2 }),
    {
      validator: (val: string) => {
        const path = `${val}/`;
        return !linuxNotInclude.find(item => path.search(item) > -1);
      },
      message: () => window.i18n.t('不能以如下内容开头', { path: linuxNotIncludeError.join(', ') }),
      trigger: 'blur',
    },
  ],
  winInstallPath: [reguRequired, reguFnSysPath({ type: 'windows' }),
    {
      validator: (val: string) => {
        const path = `${val}\\\\`;
        return !winNotInclude.find(item => path.search(new RegExp(item, 'i')) > -1);
      },
      message: () => window.i18n.t('不能以如下内容开头', { path: winNotIncludeError.join(', ') }),
      trigger: 'blur',
    },
  ],
  package: [reguRequired,
    {
      validator(val: string) {
        return /^[A-Za-z0-9_-]{1,}(.tgz)$/.test(val);
      },
      message: window.i18n.t('包名称格式不正确'),
      trigger: 'blur',
    },
  ],
};
