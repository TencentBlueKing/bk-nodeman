<template>
  <transition name="tips">
    <div class="selection-tips" v-show="value">
      <i18n path="已选条数" tag="div">
        <span class="tips-num">{{ selectionCount }}</span>
      </i18n>
      <bk-button ext-cls="tips-btn" text v-if="!selectAllData && (selectionCount !== total)" @click="handleSelectAll">
        <span v-if="selectAllText">{{ $t('选择所有数据') }}</span>
        <i18n v-else path="选择所有条数">
          <span class="tips-num">{{ total }}</span>
        </i18n>
      </bk-button>
      <bk-button
        ext-cls="tips-btn"
        text
        v-else
        @click="handleClearSelected">
        {{ $t('清除所有数据') }}
      </bk-button>
    </div>
  </transition>
</template>
<script lang="ts">
import { Vue, Prop, Component, Model, Emit } from 'vue-property-decorator';

@Component({ name: 'selection-tips' })
export default class SelectionTips extends Vue {
  @Model('change', { default: false, type: Boolean }) private readonly value!: boolean;
  @Prop({ default: 0, type: Number }) private readonly selectionCount!: number;
  @Prop({ default: 0, type: Number }) private readonly total!: number;
  @Prop({ default: false, type: Boolean }) private readonly selectAllData!: boolean;
  @Prop({ default: false, type: Boolean }) private readonly selectAllText!: boolean;

  @Emit('select-all')
  public handleSelectAll() {}

  @Emit('clear')
  public handleClearSelected() {}
}
</script>
<style lang="postcss" scoped>
.selection-tips {
  height: 30px;
  background: #ebecf0;
  display: flex;
  align-items: center;
  justify-content: center;
  .tips-num {
    font-weight: bold;
    padding: 0 2px;
  }
  .tips-btn {
    font-size: 12px;
    margin-left: 5px;
  }
}
</style>
