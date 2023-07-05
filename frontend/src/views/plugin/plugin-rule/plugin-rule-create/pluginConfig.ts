import { IStep } from '@/types/plugin/plugin-type';

// export const pluginOperateList = [
//   { id: 'MAIN_INSTALL_PLUGIN', name: window.i18n.t('安装或更新') },
//   { id: 'MAIN_START_PLUGIN', name: window.i18n.t('启动') },
//   { id: 'MAIN_STOP_PLUGIN', name: window.i18n.t('停止') },
//   { id: 'MAIN_RESTART_PLUGIN', name: window.i18n.t('重启') },
//   { id: 'MAIN_RELOAD_PLUGIN', name: window.i18n.t('重载') },
//   { id: 'MAIN_DELEGATE_PLUGIN', name: window.i18n.t('托管') },
//   { id: 'MAIN_UNDELEGATE_PLUGIN', name: window.i18n.t('取消托管') }
// ]
export const stepMap: { [key: string]: IStep[] } = {
  // 普通策略操作流程
  // upgrade: [
  //   { title: window.i18n.t('升级版本'), icon: 1, com: 'upgradeVersion' },
  //   { title: window.i18n.t('参数配置'), icon: 2, com: 'paramsConfig' },
  //   { title: window.i18n.t('执行预览'), icon: 3, com: 'performPreview' }
  // ],
  create: [
    { title: window.i18n.t('部署目标'), icon: 1, com: 'deployTarget' },
    { title: window.i18n.t('部署版本'), icon: 2, com: 'deployVersion' },
    { title: window.i18n.t('参数配置'), icon: 3, com: 'paramsConfig' },
    { title: window.i18n.t('执行预览'), icon: 4, com: 'performPreview' },
  ],
  edit: [
    { title: window.i18n.t('部署目标'), icon: 1, com: 'deployTarget' },
    { title: window.i18n.t('部署版本'), icon: 2, com: 'deployVersion' },
    { title: window.i18n.t('参数配置'), icon: 3, com: 'paramsConfig' },
    { title: window.i18n.t('执行预览'), icon: 4, com: 'performPreview' },
  ],
  // target: [
  //   { title: window.i18n.t('调整目标'), icon: 1, com: 'adjustTarget' },
  //   { title: window.i18n.t('执行预览'), icon: 2, com: 'performPreview' }
  // ],
  start: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  stop: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  stop_and_delete: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  RETRY_ABNORMAL: [ // 失败重试
    { title: '', icon: 1, com: 'performPreview' },
  ],

  // 灰度策略操作流程
  createGray: [
    { title: window.i18n.t('灰度目标'), icon: 1, com: 'deployTarget' },
    { title: window.i18n.t('灰度版本'), icon: 2, com: 'deployVersion' },
    { title: window.i18n.t('灰度参数'), icon: 3, com: 'paramsConfig' },
    { title: window.i18n.t('执行预览'), icon: 4, com: 'performPreview' },
  ],
  editGray: [
    { title: window.i18n.t('灰度目标'), icon: 1, com: 'deployTarget' },
    { title: window.i18n.t('灰度版本'), icon: 2, com: 'deployVersion' },
    { title: window.i18n.t('灰度参数'), icon: 3, com: 'paramsConfig' },
    { title: window.i18n.t('执行预览'), icon: 4, com: 'performPreview' },
  ],
  deleteGray: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  releaseGray: [
    { title: '', icon: 1, com: 'performPreview' },
  ],

  // 手动操作插件流程
  MAIN_INSTALL_PLUGIN: [
    { title: window.i18n.t('选择版本'), icon: 1, com: 'deployVersion' },
    { title: window.i18n.t('参数配置'), icon: 2, com: 'paramsConfig' },
    { title: window.i18n.t('执行预览'), icon: 3, com: 'performPreview' },
  ],
  MAIN_START_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  MAIN_STOP_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  MAIN_RESTART_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  MAIN_RELOAD_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  MAIN_DELEGATE_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
  MAIN_UNDELEGATE_PLUGIN: [
    { title: '', icon: 1, com: 'performPreview' },
  ],
};

export const titleMap: Dictionary = {
  // 策略相关
  create: window.i18n.t('nav_新建策略'),
  // target: window.i18n.t('nav_调整目标'),
  // upgrade: window.i18n.t('nav_升级部署'),
  edit: window.i18n.t('nav_编辑策略'),
  start: window.i18n.t('nav_启用预览'),
  stop: window.i18n.t('nav_停用预览'),
  stop_and_delete: window.i18n.t('nav_卸载并删除预览'),
  RETRY_ABNORMAL: window.i18n.t('nav_失败重试预览'),
  // 灰度
  createGray: window.i18n.t('nav_新建灰度策略'),
  editGray: window.i18n.t('nav_编辑灰度策略'),
  releaseGray: window.i18n.t('nav_发布灰度策略'),
  deleteGray: window.i18n.t('nav_删除灰度策略'),
  // 插件相关
  MAIN_INSTALL_PLUGIN: window.i18n.t('nav_安装或更新插件'),
  MAIN_START_PLUGIN: window.i18n.t('nav_启动插件预览'),
  MAIN_STOP_PLUGIN: window.i18n.t('nav_停止插件预览'),
  MAIN_RESTART_PLUGIN: window.i18n.t('nav_重启插件预览'),
  MAIN_RELOAD_PLUGIN: window.i18n.t('nav_重载插件预览'),
  MAIN_DELEGATE_PLUGIN: window.i18n.t('nav_托管插件预览'),
  MAIN_UNDELEGATE_PLUGIN: window.i18n.t('nav_取消托管插件预览'),
};
