<template>
  <section class="sideslider-content">
    <div class="sideslider-content-basic">
      <!--基础信息-->
      <div class="basic-title">{{ $t('基础信息') }}</div>
      <div class="basic-form">
        <div
          v-for="(item, index) in basicInfo"
          :key="index"
          class="basic-form-item"
          :class="index % 2 === 0 ? 'basic-form-even' : 'basic-form-odd'">
          <div class="item-label" :style="{ flexBasis: `${labelMaxWidth}px` }">
            <span :class="{ 'has-tip': item.tip }" v-bk-tooltips="{
              width: 200,
              delay: [300, 0],
              theme: 'light',
              content: item.tip,
              disabled: !item.tip
            }">{{ item.label }}</span>：
          </div>
          <div class="item-content">
            <!--普通类型-->
            <div v-if="item.prop !== 'auth_type'" class="item-content-form">
              <span class="form-input" v-if="item.type === 'tag-switch'">
                <span :class="['tag-switch', { 'tag-enable': item.value }]">
                  {{ item.value ? item.onText || $t('启用') : item.offText || $t('停用') }}
                </span>
              </span>
              <span class="form-input" v-else>
                {{ getFormValue(item) }}
              </span>
            </div>
            <!--认证类型-->
            <div class="item-content-form auth" v-else>
              <span class="auth-type">
                {{ getAuthName(item.authType) }}
              </span>
              <span class="key-icon nodeman-icon nc-key" v-show="item.authType === 'KEY'"></span>
              <span class="form-input"
                    :class="{ 'password': item.authType === 'PASSWORD' }"
                    :title="getAuthValue(item)">
                {{ getAuthValue(item) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';
import { MainStore, CloudStore } from '@/store/index';
import { detailConfig } from '../config/proxy-detail-config';
import { authentication, passwordFillText } from '@/config/config';
import { IProxyDetail } from '@/types/cloud/cloud';
import { IAuth, IProxyIpKeys } from '@/types';

interface IItem {
  label: string
  prop: string
  readonly: boolean
  value: string
  authType?: string
  type?: string
  unit?: string
}

@Component({ name: 'sideslider-content' })

export default class SidesliderCcontent extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly basic!: IProxyDetail;

  private loading = false;
  // 基础信息和服务信息数据
  private basicInfo: any[] = [];
  // 认证方式
  private authentication = authentication;
  private labelMaxWidth = 100;

  private get apList() {
    return CloudStore.apList;
  }
  private get apUrl() {
    return CloudStore.apUrl;
  }
  private get apId() {
    return this.basic.ap_id;
  }

  @Watch('basic', { immediate: true })
  public async handlebasicChange(data: Dictionary) {
    const ipKeys: IProxyIpKeys[] = ['inner_ip', 'outer_ip', 'login_ip'];
    // 设置判断当前接入点为v2版本的布尔值
    const isApV2 = this.apList?.find(item => item.id === data.ap_id)?.gse_version === 'V2'
    let basicInfo = detailConfig.map((config: Dictionary) => {
      if (config.prop === 'auth_type') {
        config.authType = data.auth_type || 'PASSWORD';
        config.value = config.authType === 'TJJ_PASSWORD' ? this.$t('自动拉取') : '';
      } else if (ipKeys.includes(config.prop)) {
        config.value = data[`${config.prop}v6`] || data[config.prop] || '';
      } else {
        config.value = data[config.prop] || '';
      }
      return JSON.parse(JSON.stringify(config));
    });
    // 接入点不为v2时，不显示版本信息
    if (!isApV2) {
      basicInfo = basicInfo.filter(item => item.prop !== 'version');
    };
    this.basicInfo.splice(0, this.basicInfo.length, ...basicInfo);
  }

  private created() {
    this.handleInit();
  }
  private mounted() {
    this.labelMaxWidth = this.getLabelMaxWidth();
  }

  private async handleInit() {
    if (!this.apList.length) {
      await CloudStore.getApList();
    }
    CloudStore.setApUrl({ id: this.apId });
  }
  /**
   * 获取认证方式对应的name
   */
  private getAuthName(id: string) {
    const auth: IAuth | Dictionary = this.authentication.find(auth => auth.id === id) || {};
    return auth.name || '';
  }
  /**
   * 认证方式表单值
   */
  private getAuthValue(item: IItem) {
    if (item.authType === 'PASSWORD') {
      return passwordFillText;
    } if (item.authType === 'KEY') {
      return 'key';
    }
    return item.value;
  }
  /**
   * 回显表单值
   */
  private getFormValue(item: IItem) {
    if (item.prop === 'bk_biz_scope') {
      return MainStore.bkBizList.filter((biz: Dictionary) => item.value.includes(biz.bk_biz_id))
        .map((biz: Dictionary) => biz.bk_biz_name)
        .join(', ');
    }
    if (item.unit) {
      return item.value ? `${item.value} ${item.unit}` : '--';
    }
    return item.value || '--';
  }
  private getLabelMaxWidth(): number {
    const el = this.$el;
    const $labelWidthList: NodeListOf<Element> = el.querySelectorAll('.item-label');
    let max = 100;
    $labelWidthList.forEach((item: Element) => {
      const { width } = (item.querySelector('span') as Element).getBoundingClientRect();
      max = Math.max(max, width);
    });
    return Math.ceil(max);
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

@define-mixin title {
  font-size: 14px;
  color: #313238;
  margin-bottom: 14px;
  font-weight: bold;
}
@define-mixin form {
  @mixin layout-flex row, center, flex-start, wrap;
  &-item {
    margin-bottom: 8px;
    font-size: 14px;

    @mixin layout-flex row, center;
    .item-label {
      flex-basis: 100px;
      text-align: right;
      color: #979ba5;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .item-content {
      width: 0;
      flex: 1;
      padding: 0 8px;
      height: 32px;

      @mixin layout-flex row, center, space-between;
    }
  }
}
@define-mixin name-overflow {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@define-mixin font-size-color $color, $size {
  font-size: $size;
  color: $color;
}

.sideslider-content {
  height: calc(100vh - 60px);
  padding: 24px 30px 0 30px;
  &-basic {
    .basic-title {
      @mixin title;
    }
    .basic-form {
      @mixin form;
      &-odd {
        flex: 0 0 60%;
      },
      &-even {
        flex: 0 0 40%;
      }
      .has-tip {
        border-bottom: 1px dashed #979ba5;
      }
      .item-content {
        &-form {
          width: 0;
          flex: 1;

          @mixin layout-flex row, center;
          @mixin name-overflow;
          .key-icon {
            margin-right: 4px;

            @mixin font-size-color #C4C6CC, 18px;
          }
          .auth-type {
            min-width: 55px;
            border-right: 1px solid #dcdee5;
            margin-right: 12px;

            @mixin layout-flex row, center, space-between;

          },
          .form-input {
            width: 0;
            flex: 1;

            @mixin name-overflow;
            &.password {
              margin-top: 4px;
            }
          }
        }
      }
    }
  }
}
</style>
