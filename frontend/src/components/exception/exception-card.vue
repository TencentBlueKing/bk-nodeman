<template>
  <div :class="['bk-exception-card', { 'has-border': hasBorder }]" v-show="show">
    <div class="exception-content">
      <img class="exception-img" :src="image">
      <template v-if="$slots.message">
        <slot name="message"></slot>
      </template>
      <template v-else>
        <p class="exception-text">{{ message }}</p>
        <p v-if="type === 'notPower'" class="exception-text text-link" @click="handleClick">{{ $t('去申请') }}</p>
      </template>
      <slot name="content"></slot>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Emit } from 'vue-property-decorator';
import imgNotData from '@/images/not-data.png';
import imgNotPower from '@/images/not-power.png';
import imgNotResult from '@/images/not-result.png';
import imgDataAbnormal from '@/images/data-abnormal.png';

@Component({ name: 'app-exception-card' })

export default class AppExceptionCard extends Vue {
  @Prop({ type: String, default: 'notData' }) private readonly type!: string;
  @Prop({ type: Number, default: 0 }) private readonly delay!: number;
  @Prop({ type: String, default: '' }) private readonly text!: string;
  @Prop({ type: Boolean, default: true }) private readonly hasBorder!: boolean;

  private show = false;
  private image = '';
  private message = '';

  private created() {
    let message = '';
    let image = '';
    switch (this.type) {
      case 'notData':
        image = imgNotData;
        message = window.i18n.t('没有数据');
        break;
      case 'notPower':
        image = imgNotPower;
        message = window.i18n.t('没有权限');
        break;
      case 'notResult':
        image = imgNotResult;
        message = window.i18n.t('搜索为空');
        break;
      case 'dataAbnormal':
        image = imgDataAbnormal;
        message = window.i18n.t('数据异常');
        break;
    }
    if (this.text) {
      message = this.text;
    }
    setTimeout(() => {
      this.show = true;
    }, this.delay);
    this.message = message;
    this.image = image;
  }

  @Emit('click')
  private handleClick() {
    return this.type;
  }
}
</script>

<style lang="postcss" scoped>
.bk-exception-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 260px;
  background: #fff;
  &.has-border {
    border: 1px solid #dcdee5;
    border-radius: 2px;
  }
  .exception-content {
    margin-top: -10px;
    text-align: center;
  }
  .exception-img {
    width: 120px;
    margin-bottom: 10px;
  }
  .exception-text {
    margin: 0;
    line-height: 19px;
    font-size: 14px;
    font-weight: normal;
    color: #63656e;
    &.text-link {
      margin-top: 10px;
      line-height: 16px;
      font-size: 12px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
}
</style>
