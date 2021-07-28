<template>
  <div class="filter-tips">
    <i class="filter-tips-icon nodeman-icon nc-tips"></i>
    <span>{{ $t('全部过滤提示') }}</span>
    <bk-button ext-cls="filter-tips-btn" text @click="handleShowDetail">{{ $t('查看详情') }}</bk-button>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Emit } from 'vue-property-decorator';

@Component({ name: 'filter-ip-tips' })

export default class FilterIpTips extends Vue {
  @Emit('click')
  public handleShowDetail() {}
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .filter-tips {
    height: 16px;
    line-height: 16px;

    @mixin layout-flex row, center;
    &-icon {
      font-size: 16px;
      margin-right: 8px;
    }
    &-btn {
      font-size: 12px;
    }
  }
</style>
