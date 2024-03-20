<template>
  <bk-sideslider
    transfer
    :is-show.sync="show"
    :width="width"
    quick-close
    :before-close="sliderBeforeClose"
    @hidden="handleToggle(false)">
    <template #header>{{ title }}</template>
    <template #content>
      <SidesliderContentEdit
        v-if="edit"
        :basic="basicInfo"
        :edit-type="editType"
        @update-edited="(isEdited) => edited = !!isEdited"
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
  @Prop({ type: String, default: '' }) private readonly editType!: string;
  @ModelSync('value', 'change', { default: false, type: Boolean }) private show!: boolean;

  private basicInfo: Dictionary = {};
  private edited = false;

  private get title() {
    // return this.edit ? this.$t('修改登录信息') : this.row.inner_ip;
    return this.edit ?  this.text : this.row.inner_ip;
  }
  private get text() {
    const messages: Dictionary = {
      reinstall: '重装',
      reload: '重载',
    };
    return messages[this.editType] || '修改登录信息';
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
    if (!show) {
      this.edited = false;
    }
    return show;
  }
  @Emit('save')
  public handleSave(show: boolean) {
    return show;
  }

  public sliderBeforeClose() {
    if (!this.edited) return Promise.resolve(true);
    return new Promise((resolve) => {
      this.$bkInfo({
        title: window.i18n.t('确定离开当前页'),
        subTitle: window.i18n.t('离开将会导致未保存的信息丢失'),
        confirmFn: () => {
          resolve(true);
        },
        cancelFn: () => resolve(false),
      });
    });
  }
}
</script>
