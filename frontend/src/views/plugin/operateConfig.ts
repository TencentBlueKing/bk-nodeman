export interface IRuleRouterParams {
  id?: number // 策略id 暂不与灰度id区分
  policyName?: string // 策略名称
  pluginId?: number
  pluginName?: string
  type: string // 操作类型
  ruleType?: 'policy' | 'gray' | 'plugin' // 规则对象类型
}

// 主策略更新类型
export const policyUpdateType = ['create', 'edit'];
// 主策略操作类型
export const policyOperateType = ['start', 'stop', 'delete', 'stop_and_delete', 'RETRY_ABNORMAL'];
// 主策略
export const policyRuleType = [...policyUpdateType, ...policyOperateType];

// 灰度策略
export const grayRuleType: string[] = ['createGray', 'editGray', 'deleteGray', 'releaseGray'];

// 插件操作类型
export const pluginOperate = [
  'MAIN_INSTALL_PLUGIN',
  'MAIN_START_PLUGIN',
  'MAIN_STOP_PLUGIN',
  'MAIN_RESTART_PLUGIN',
  'MAIN_RELOAD_PLUGIN',
  'MAIN_DELEGATE_PLUGIN',
  'MAIN_UNDELEGATE_PLUGIN',
];
// 全部类型
export const allProcessType = [...policyRuleType, ...grayRuleType, ...policyOperateType];

// 手动操作插件 且 不需要传steps参数的类型
export const manualNotSteps = [
  'MAIN_START_PLUGIN',
  'MAIN_STOP_PLUGIN',
  'MAIN_RESTART_PLUGIN',
  'MAIN_RELOAD_PLUGIN',
  'MAIN_DELEGATE_PLUGIN',
  'MAIN_UNDELEGATE_PLUGIN',
];
// 带步骤流程的操作类型
export const stepOperate = ['create', 'edit', 'createGray', 'editGray', 'MAIN_INSTALL_PLUGIN'];
// 只有预览流程的操作类型
export const previewOperate = [
  'start', 'stop', 'stop_and_delete', 'RETRY_ABNORMAL',
  'deleteGray', 'releaseGray', ...manualNotSteps,
];
// 不需要前置计算的类型
export const notCalculate = ['stop', 'stop_and_delete', 'RETRY_ABNORMAL'];
