<template>
  <div class="loading" :style="verticalAlign">
    <section class="loading-origin">
      <div class="loading-ball" v-for="index in 8" :key="index" :style="bgColor"></div>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({ name: 'loading-icon' })
export default class LoadingIcon extends Vue {
  @Prop({ default: '#3A84FF', type: String }) private readonly color!: string;
  @Prop({ default: 'middle', type: String }) private readonly vertical!: string;

  private get verticalAlign() {
    return { verticalAlign: this.vertical };
  }

  private get bgColor() {
    return { background: this.color };
  }
}
</script>
<style lang="scss" scoped>
.loading {
  position: relative;
  display: inline-block;
  width: 16px;
  height: 16px;
  vertical-align: middle;
  .loading-origin {
    position: absolute;
    top: 6px;
    left: 7px;
    width: 2px;
    height: 3px;
    animation: loading 1s linear infinite;
  }
  .loading-ball {
    position: absolute;
    top: 0;
    left: 0;
    width: 2px;
    height: 3px;
    border-radius: 2px;
    &:nth-child(1) {
      top: -6px;
    }
    &:nth-child(2) {
      top: -4px;
      left: 4px;
      transform: rotateZ(45deg);
      opacity: .9;
    }
    &:nth-child(3) {
      left: 6px;
      transform: rotateZ(90deg);
      opacity: .8;
    }
    &:nth-child(4) {
      top: 4px;
      left: 4px;
      transform: rotateZ(-45deg);
      opacity: .7;
    }
    &:nth-child(5) {
      top: 6px;
      opacity: .6;
    }
    &:nth-child(6) {
      top: 4px;
      left: -4px;
      transform: rotateZ(45deg);
      opacity: .5;
    }
    &:nth-child(7) {
      left: -6px;
      transform: rotateZ(90deg);
      opacity: .4;
    }
    &:nth-child(8) {
      top: -4px;
      left: -4px;
      transform: rotateZ(-45deg);
      opacity: .3;
    }
  }
}
</style>
