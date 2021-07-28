export default (apUrl, proxy, sshPort, gesServerIps) => {
  const getFontHtml = (color, param) => `<font color="${color}">${param}</font>`;
  return [
    `1、${window.i18n.t('开通Nginx策略提示外网', { url: getFontHtml('#313238', apUrl) })}`,
    `2、${window.i18n.t('APPO外网到Proxy使用端口', {
      appoIp: getFontHtml('#313238', window.PROJECT_CONFIG.APPO_IP),
      proxyIp: getFontHtml('#3A84FF', proxy),
      port: getFontHtml('#3A84FF', sshPort) })}`,
    `3、${window.i18n.t('Proxy到GSE使用端口', {
      proxyIp: getFontHtml('#3A84FF', proxy),
      gseIp: getFontHtml('#313238', gesServerIps),
      port: getFontHtml(
        '#313238',
        window.PROJECT_CONFIG.GSE_LISTEN_PORT,
      ) })}`,
    `4、${window.i18n.t('Gse到Proxy使用端口', {
      gseIp: getFontHtml('#313238', gesServerIps),
      proxyIp: getFontHtml('#3A84FF', proxy),
      port: getFontHtml(
        '#313238',
        window.PROJECT_CONFIG.PROXY_LISTEN_PORT,
      ) })}`,
    `5、${window.i18n.t('Linux脚本执行权限提示')}`,
  ];
};
