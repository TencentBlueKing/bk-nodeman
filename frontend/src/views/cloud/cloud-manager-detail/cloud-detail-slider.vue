<template>
  <bk-sideslider transfer :is-show.sync="show" :width="width" quick-close @hidden="handleToggle(false)">
    <template #header>{{ title }}</template>
    <template #content>
      <SidesliderContentEdit
        v-if="edit"
        :basic="basicInfo"
        @close="handleToggle(false)"
        @change="handleSave">
      </SidesliderContentEdit>
      <SidesliderContent :basic="basicInfo" v-else></SidesliderContent>
    </template>
  </bk-sideslider>
</template>
<script lang="ts">
import { Component, Prop, Vue, ModelSync, Emit, Watch } from 'vue-property-decorator';
import SidesliderContent from '../components/sideslider-content.vue';
import SidesliderContentEdit from '../components/sideslider-content-edit.vue';

@Component({
  name: 'CloudDetailSlider',
  components: {
    SidesliderContent,
    SidesliderContentEdit,
  },
})

export default class CloudDetailSlider extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly row!: Dictionary;
  @Prop({ type: Boolean, default: false }) private readonly edit!: boolean;
  @ModelSync('value', 'change', { default: false, type: Boolean }) private show!: boolean;

  private basicInfo: Dictionary = {};

  private get title() {
    return this.edit ? this.$t('修改登录信息') : this.row.inner_ip;
  }
  private get width() {
    return this.edit ? 600 : 780;
  }

  @Watch('show')
  public handleShowChange(show: boolean) {
    this.$set(this, 'basicInfo', show ? this.row : {});
  }

  @Emit('change')
  public handleToggle(show: boolean) {
    return show;
  }
  @Emit('save')
  public handleSave(show: boolean) {
    return show;
  }
}
</script>
