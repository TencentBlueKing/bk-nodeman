<template>
  <section class="content">
    <bk-input :placeholder="$t('搜索拓扑节点')" class="mb20"></bk-input>
    <DynamicTopo></DynamicTopo>
  </section>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import DynamicTopo from './dynamic-topo.vue';

@Component({
  name: 'dynamic-content',
  components: {
    DynamicTopo,
  },
})
export default class DynamicContent extends Vue {}
</script>
<style lang="postcss" scoped>
.content {
  padding: 0 24px 16px 24px;
}
</style>
