import { Module, VuexModule, Mutation, Action } from 'vuex-module-decorators';
import { IPlatformConfig } from '@/types/config/config';
import { getPlatformConfig } from '@blueking/platform-config';
import logoSrc from '@/images/logoIcon.png';

// eslint-disable-next-line new-cap
@Module({ name: 'platformConfig', namespaced: true })
export default class PlatformConfigStore extends VuexModule {
  public defaults: IPlatformConfig =  {
    bkAppCode: '', // appcode
    name: '', // 站点的名称，通常显示在页面左上角，也会出现在网页title中
    nameEn: '', // 站点的名称-英文
    appLogo: '', // 站点logo
    favicon: '/static/images/favicon.png', // 站点favicon
    helperText: '',
    helperTextEn: '',
    helperLink: '',
    brandImg: '',
    brandImgEn: '',
    brandName: '', // 品牌名，会用于拼接在站点名称后面显示在网页title中
    favIcon: '',
    brandNameEn: '', // 品牌名-英文
    footerInfo: '', // 页脚的内容，仅支持 a 的 markdown 内容格式
    footerInfoEn: '', // 页脚的内容-英文
    footerCopyright: '', // 版本信息，包含 version 变量，展示在页脚内容下方

    footerInfoHTML: '',
    footerInfoHTMLEn: '',
    footerCopyrightContent: '',
    version: '',

    // 需要国际化的字段，根据当前语言cookie自动匹配，页面中应该优先使用这里的字段
    i18n: {
      name: '',
      helperText: '...',
      brandImg: '...',
      brandName: '...',
      footerInfoHTML: '...',
    },
  };
  /**
  * 获取远程配置
  * @param {*} param0
  */
  
  @Mutation
  public updatePlatformConfig(value: IPlatformConfig) {
    Object.assign(this.defaults, value);
  }

  @Action
  public async getConfig() {
    const config = await getPlatformConfig(window.PROJECT_CONFIG?.BKPAAS_SHARED_RES_URL, {
      name: '蓝鲸节点管理',
      nameEn: 'NodeMan',
      appLogo: logoSrc,
      brandName: '腾讯蓝鲸智云',
      brandNameEn: 'BlueKing',
      favicon: '/static/images/favicon.png',
      helperLink: window.PROJECT_CONFIG.BKAPP_NAV_HELPER_URL,
      helperText: window.i18n.t('联系BK助手'),
      version: window.PROJECT_CONFIG.VERSION,
    });
    console.log("🚀 ~ PlatformConfigStore ~ getConfig ~ config:", config)

    this.context.commit('updatePlatformConfig', config);
  }
}
