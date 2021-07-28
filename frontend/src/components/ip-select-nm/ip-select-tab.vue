<template>
  <ul class="tab">
    <li v-for="item in list"
        :key="item.name"
        :class="['tab-item', { active: active === item.name }]"
        @click="handleTabClick(item)">
      {{ item.label }}
    </li>
  </ul>
</template>
<script lang="ts">
import { Vue, Component, Prop, Model, Watch, Emit } from 'vue-property-decorator';

interface ITabPanel {
  name: string
  label: string
  visible?: boolean
  disabled?: boolean
}

@Component({ name: 'tab' })
export default class Tab extends Vue {
  @Prop({ default: () => [] }) private readonly list!: ITabPanel[];
  @Model('change', { default: '' }) private readonly value!: string;

  private active = this.value;

  @Watch('active')
  private handleOnActiveChange() {
    this.handleTabChange();
  }

  public handleTabClick(item: ITabPanel) {
    return this.active = item.name;
  }

  @Emit('change')
  public handleTabChange() {
    return this.active;
  }
}
</script>
<style lang="postcss" scoped>
.tab {
  display: flex;
  &-item {
    display: flex;
    justify-content: center;
    align-items: center;
    flex: 1;
    height: 42px;
    color: #63656e;
    font-size: 14px;
    border-bottom: 1px solid #dcdee5;
    cursor: pointer;
    background: #fafbfd;
    &:not(:last-child) {
      border-right: 1px solid #dcdee5;
    }
    &.active {
      background: #fff;
      border-bottom: 0;
    }
  }
}
</style>
