<template>
  <div class="selector-content">
    <keep-alive :include="include">
      <component
        class="layout"
        :is="currentComponent"
        v-bind="$attrs"
        v-on="$listeners"
        ref="layout">
      </component>
    </keep-alive>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { ILayoutComponents, IPanel } from '../types/selector-type';

const abstractProp = ['getSearchTableData', 'getDefaultData', 'getDefaultSelections'];
const layout = require.context('../layout', true, /\.(vue|ts)$/);
const optionsSet = new Set();
const components = layout.keys().reduce<ILayoutComponents>((pre, next) => {
  const com = layout(next);
  const { name, props } = com.default.options;
  process.env.NODE_ENV === 'development' && props && Object.keys(props).forEach((key) => {
    if (optionsSet.has(key)) {
      !abstractProp.includes(key) && console.log(`${name}组件${key}属性和其余layout组件重复，确保数据源一致`);
    } else {
      optionsSet.add(key);
    }
  });
  name && (pre[name] = com.default);
  return pre;
}, {});

// 内容区域
@Component({ name: 'selector-content' })
export default class SelectorContent extends Vue {
  @Prop({ default: '', type: String }) private readonly active!: string; // 当前激活组件
  @Prop({ default: () => [], type: Array }) private readonly panels!: IPanel[];

  private get currentComponent() {
    const panel = this.panels.find(item => item.name === this.active);
    return panel?.component ? panel.component : components[this.active];
  }

  private get include() {
    return this.panels.reduce<string[]>((pre, next) => {
      if (next.keepAlive) {
        pre.push(next.name);
      }
      return pre;
    }, []);
  }

  public handleGetDefaultSelections() {
    try {
      (this.$refs.layout as any).handleGetDefaultSelections();
    } catch (err) {
      console.log(err);
    }
  }
}
</script>
<style lang="scss" scoped>
.selector-content {
  padding: 24px 24px 0 24px;
  overflow: hidden;
  height: 100%;
  background: #fff;
  .layout {
    height: 100%;
  }
}
</style>
