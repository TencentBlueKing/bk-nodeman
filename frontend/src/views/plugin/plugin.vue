<template>
  <article class="plugin-node">
    <PluginListOperate :filter-data="filterData"></PluginListOperate>
    <PluginListTable
      class="plugin-node-table"
      :filter-data="filterData">
    </PluginListTable>
  </article>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import PluginListOperate from './plugin-list/plugin-list-operate.vue';
import PluginListTable from './plugin-list/plugin-list-table.vue';
import { ISearchItem } from '@/types';

@Component({
  name: 'plugin',
  components: {
    PluginListOperate,
    PluginListTable,
  },
})
export default class Plugin extends Vue {
  private filterData: ISearchItem[] = [];

  private mounted() {
    this.getFilterData();
  }
  public async getFilterData() {
    this.filterData = await PluginStore.getFilterList();
  }
}

</script>

<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";
  @import "@/css/transition.css";

  .plugin-node {
    margin-bottom: 20px;
    .plugin-node-table {
      margin-top: 14px;
    }
  }
</style>
