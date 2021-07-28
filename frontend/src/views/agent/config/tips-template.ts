export default ({ apUrl, net = false }: { apUrl: string, net: boolean }) => {
  const getFontHtml = (color: string, param: any) => `<font color="${color}">${param}</font>`;
  const key = net ? '开通Nginx策略提示内网' : '开通Nginx策略提示外网';
  return [
    `1、${window.i18n.t('支持的操作系统')}`,
    `2、${window.i18n.t(key, { url: getFontHtml('#313238', apUrl) })}`,
    `3、${window.i18n.t('开通Linux策略提示', { ip: getFontHtml('#313238', window.PROJECT_CONFIG.APPO_IP) })}`,
    `4、${window.i18n.t('开通Windows策略提示', {
      ip: getFontHtml('#313238', window.PROJECT_CONFIG.APPO_IP),
      port: getFontHtml('#313238', '139、445') })}`,
    `5、${window.i18n.t('登录要求提示')}`,
    `6、${window.i18n.t('Linux脚本执行权限提示')}`,
  ];
};
