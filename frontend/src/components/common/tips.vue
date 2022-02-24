<template>
  <article :class="['tips', theme]" v-show="showTips">
    <!--提示icon-->
    <section class="tips-icon">
      <template v-if="$slots.tipsIcon">
        <slot name="tipsIcon"></slot>
      </template>
      <i v-else class="nodeman-icon nc-tips"></i>
    </section>
    <!--提示内容-->
    <section class="tips-content">
      <slot v-bind="{ list }">
        <ul v-if="Array.isArray(list)">
          <li v-for="(item, index) in list" :key="index" class="tips-content-item">{{ item }}</li>
        </ul>
        <span class="tips-content-item" v-else>
          {{ list }}
        </span>
      </slot>
      <span class="tips-content-close" text @click="handleHide" v-if="showClose">{{ $t('不再提示') }}</span>
    </section>
  </article>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';

@Component({ name: 'tips' })

export default class Tips extends Vue {
  @Prop({ type: String, default: 'primary' }) private readonly theme!: string;
  @Prop({ type: [Array, String], default: '' }) private readonly list!: string | string[];
  @Prop({ type: Boolean, default: false }) private readonly showClose!: boolean; // 是否显示关闭提示按钮
  @Prop({ type: Number, default: 3600000 * 24 * 30 }) private readonly expire!: number; // tips隐藏过期时间
  @Prop({ type: String, default: '__nodeman_tips__' }) private readonly storageKey!: string; // 存储key

  private showTips = true;

  private created() {
    this.handleInit();
  }

  @Emit('change')
  public handleInit() {
    if (window.localStorage && this.showClose) {
      const expireTime = window.localStorage.getItem(this.storageKey) || '0';
      this.showTips = new Date().getTime() > parseInt(expireTime, 10);
    }
    return this.showTips;
  }
  // 隐藏tips
  @Emit('change')
  public handleHide() {
    if (window.localStorage) {
      const dateTime = new Date().getTime() + this.expire;
      window.localStorage.setItem(this.storageKey, `${dateTime}`);
      this.showTips = false;
    }
    return this.showTips;
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/variable.css";

  $tipsBackground: #f0f8ff;
  $tipsBorder: #c5daff;
  $tipsDangerBackground: #ffeded;
  $tipsDangerBorder: #ffd2d2;
  $tipsWarningBackground: #fff4e2;
  $tipsWarningBorder: #ffdfac;
  $tipsDefaultBackground: #f5f6fa;
  $tipsDefaultBorder: #f5f6fa;
  $tipsDefault: #878A99;

  .tips {
    padding: 7px 15px 7px 10px;
    min-height: 32px;
    border: 1px solid $tipsBorder;
    border-radius: 2px;
    background: $tipsBackground;

    @mixin layout-flex row;
    .tips-icon {
      font-size: 16px;
      color: $primaryFontColor;

      @mixin layout-flex row;
    }
    .tips-content {
      flex: 1;
      margin-left: 8px;

      @mixin layout-flex row, flex-start, space-between;
      &-item {
        line-height: 16px;
        &:not(:first-child) {
          margin-top: 6px;
        }
      }
      &-close {
        line-height: 16px;
        font-size: 12px;
        color: #699df4;
        cursor: pointer;
      }
    }
    &.danger {
      border: 1px solid $tipsDangerBorder;
      background: $tipsDangerBackground;
      .tips-icon {
        color: $bgFailed;
      }
    }
    &.warning {
      border: 1px solid $tipsWarningBorder;
      background: $tipsWarningBackground;
      .tips-icon {
        color: $bgWarning;
      }
    }
    &.default {
      border: 1px solid $tipsDefaultBackground;
      background: $tipsDefaultBackground;
      .tips-icon {
        color: $tipsDefault;
      }
    }
  }
</style>
