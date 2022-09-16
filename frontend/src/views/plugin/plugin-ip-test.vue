<template>
  <div class="p30">
    <IpSelector />
  </div>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import IpSelector from '@/components/common/nm-ip-selectors.ts';
// import IpChooserTopo as * from '@'

@Component({
  name: 'plugin-ip-test',
  components: {
    IpSelector,
  },
})
export default class PluginRule extends Vue {
  private data: any[] = [];
}
</script>

<style lang="postcss" scoped>
</style>
