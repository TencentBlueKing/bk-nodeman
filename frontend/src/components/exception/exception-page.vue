<template>
  <div :class="['bk-exception-page', { 'has-border': hasBorder }]" v-show="show">
    <div class="exception-content">
      <img class="exception-img" :src="image">
      <template v-if="$slots.message">
        <slot name="message"></slot>
      </template>
      <template v-else>
        <p class="exception-title">{{ message }}</p>
        <p v-if="subTitle" class="exception-sub-title">{{ subTitle }}</p>
        <bk-button
          v-if="type === 'notPower'"
          class="power-apply-btn"
          theme="primary"
          @click="handleClick">
          {{ btnText || $t('去申请') }}
        </bk-button>
      </template>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import imgNotPower from '@/images/not-power_large.svg';

@Component({ name: 'app-exception-page' })

export default class AppExceptionPage extends Vue {
  @Prop({ type: String, default: 'notPower' }) private readonly type!: string;
  @Prop({ type: Number, default: 0 }) private readonly delay!: number;
  @Prop({ type: String, default: '' }) private readonly title!: string;
  @Prop({ type: String, default: () => window.i18n.t('页面auth') }) private readonly subTitle!: string;
  @Prop({ type: Boolean, default: true }) private readonly hasBorder!: boolean;
  @Prop({ type: String, default: '' }) private readonly btnText!: string;

  private show = false;
  private image = '';
  private message = '';

  private created() {
    let message = '';
    let image = '';

    switch (this.type) {
      case 'notPower':
        image = imgNotPower;
        message = window.i18n.t('没有权限');
        break;
    }
    if (this.title) {
      message = this.title;
    }
    this.message = message;
    this.image = image;
    setTimeout(() => {
      this.show = true;
    }, this.delay);
  }

  @Emit('click')
  private handleClick() {
    return this.type;
  }
}
</script>

<style lang="postcss" scoped>

.bk-exception-page {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  min-height: 423px;
  background: #fff;
  &.has-border {
    border: 1px solid #dcdee5;
    border-radius: 2px;
  }
  .exception-content {
    position: absolute;
    top: 40%;
    left: 50%;
    text-align: center;
    transform: translate3d(-50%, -50%, 0)
  }
  .exception-img {
    width: 480px;
  }
  .exception-title {
    margin: 0;
    line-height: 31px;
    font-size: 24px;
    color: #63656e;
  }
  .exception-sub-title {
    margin: 15px 0 0 0;
    line-height: 19px;
    font-size: 14px;
    color: #979ba5;
  }
  .power-apply-btn {
    margin-top: 24px;
  }
}

</style>
