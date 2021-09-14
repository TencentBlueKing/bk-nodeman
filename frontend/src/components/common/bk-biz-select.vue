<template>
  <bk-select
    class="select"
    :value="selectValue"
    :show-select-all="showSelectAll"
    :placeholder="innerPlaceholder"
    :search-placeholder="$t('请输入业务名称或业务ID')"
    :loading="loading"
    :ext-cls="extCls"
    searchable
    :multiple="multiple"
    :style="{ 'min-width': minWidth }"
    :popover-options="{ 'boundary': 'window' }"
    :clearable="clearable"
    :popover-min-width="160"
    :readonly="readonly"
    :disabled="disabled"
    :remote-method="remoteMethod"
    ref="select"
    v-test.common="'biz'"
    @selected="handleSelected"
    @toggle="handleToggle"
    @change="handleChange"
    @clear="handleClear">
    <bk-option
      v-for="option in filterBkBizList"
      :key="option.bk_biz_id"
      :id="option.bk_biz_id"
      :name="option.bk_biz_name"
      :disabled="option.disabled">
      <auth-component
        v-if="option.action && !option.has_permission"
        class="bk-option-content-default select-item"
        tag="div"
        :title="option.bk_biz_name"
        :auto-emit="true"
        :authorized="false"
        :apply-info="[{
          action: option.action,
          instance_id: option.bk_biz_id,
          instance_name: option.bk_biz_name
        }]"
        @click="close">
      </auth-component>
      <div class="select-item">
        <span class="select-item-name">
          {{ `[${option.bk_biz_id}] ${option.bk_biz_name}` }}
        </span>
        <!-- <span class="select-item-id" v-show="searchValue">{{ `(#${option.bk_biz_id})` }}</span> -->
        <i
          class="select-item-icon bk-option-icon bk-icon icon-check-1"
          v-if="multiple && !option.disabled && selectValue.includes(option.bk_biz_id)">
        </i>
      </div>
    </bk-option>
  </bk-select>
</template>
<script lang="ts">
import { MainStore } from '@/store/index';
import { Component, Vue, Prop, Ref, Emit, Watch, Model } from 'vue-property-decorator';
import { STORAGE_KEY_BIZ } from '@/config/storage-key';
import { IBizValue, IBkBiz } from '@/types';

@Component({ name: 'bk-biz-select' })

export default class BkBizSelect extends Vue {
  @Model('update', { default: '', type: Array }) private readonly value!: IBizValue;

  @Prop({ type: Boolean, default: true }) private readonly showSelectAll!: boolean;  // 是否显示全选
  @Prop({ type: String, default: '' }) private readonly extCls!: string;  // 外部样式
  @Prop({ type: String, default: '' }) private readonly placeholder!: string;
  @Prop({ type: Boolean, default: true }) private readonly defaultChecked!: boolean;  // 是否默认选中storage中勾选的业务
  @Prop({ type: Boolean, default: true }) private readonly multiple!: boolean;
  @Prop({ type: Boolean, default: true }) private readonly autoUpdateStorage!: boolean;  // 是否自动更新storage
  @Prop({ type: String, default: '240px' }) private readonly minWidth!: string;
  @Prop({ type: Boolean, default: true }) private readonly clearable!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly readonly!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly disabled!: boolean;
  @Prop({ type: Boolean, default: true }) private readonly autoRequest!: boolean;
  @Prop({ type: String, default: 'agent_view' }) private readonly action!: string;
  @Ref('select') private readonly select!: any;

  private loading = false; // select框加载
  private selectValue: IBizValue = this.value; // select框加载
  private storageKey = STORAGE_KEY_BIZ; // bizId存储Key
  private searchValue = '';
  private innerPlaceholder = this.placeholder || this.$t('选择业务');
  private remoteMethod: Function = this.handleRemoteMethod;

  private get bkBizList() {
    return MainStore.bkBizList;
  }
  private get bizAction() {
    return MainStore.bizAction || this.action || 'agent_view';
  }
  private get selectedItems() {
    if (this.selectValue instanceof Array) {
      return this.bkBizList.filter(item => (this.selectValue as number[]).includes(item.bk_biz_id));
    }
    return this.bkBizList.filter(item => this.selectValue === item.bk_biz_id);
  }
  private get filterBkBizList() {
    return this.bkBizList.reduce((pre: IBkBiz[], item: IBkBiz) => {
      const filterId = item.bk_biz_id.toString().indexOf(this.searchValue) > -1;
      const filterName = item.bk_biz_name.toString().toLocaleLowerCase()
        .indexOf(this.searchValue.toLocaleLowerCase()) > -1;
      if (filterId || filterName || !this.searchValue) {
        pre.push(item);
      }
      return pre;
    }, []);
  }

  @Watch('value')
  public handleValueChange(v: IBizValue) {
    this.selectValue = v;
  }
  private created() {
    this.handleInit();
  }

  @Emit('update')
  private async handleInit() {
    if (!this.bkBizList.length && this.autoRequest) {
      this.loading = true;
      await MainStore.getBkBizList({ action: this.bizAction });
      !this.bkBizList.length && MainStore.updatePagePermission(false);
      this.loading = false;
    }
    this.selectValue = JSON.parse(JSON.stringify(this.value));
    return this.selectValue;
  }
  @Emit('selected')
  private handleSelected(value: IBizValue, options: IBkBiz) {
    return { value, options, selected: this.selectedItems };
  }
  @Emit('toggle')
  private handleToggle(toggle: boolean) {
    return toggle;
  }
  @Emit('change')
  private handleChange(newValue: IBizValue) { // , oldValue: IBizValue) {
    this.selectValue = newValue;
    if (this.autoUpdateStorage) {
      this.handleSetStorage();
    }
    this.emitUpdate(newValue);
    // this.$emit('change', newValue, oldValue, this.selectedItems)
    return newValue;
  }
  @Emit('update')
  private emitUpdate(newValue: IBizValue) {
    return newValue;
  }
  @Emit('clear')
  private handleClear(oldValue: IBizValue) {
    return { oldValue, selected: this.selectedItems };
  }
  /**
     * 设置存储当前选择的业务ID
     */
  private handleSetStorage() {
    if (window.localStorage) {
      window.localStorage.setItem(this.storageKey, JSON.stringify(this.selectValue));
    }
    MainStore.setSelectedBiz(this.selectValue as number[]);
  }
  private handleRemoteMethod(v: string) {
    this.searchValue = v;
  }
  private async handleApplyBiz() {
    this.loading = true;
    const res = await MainStore.getApplyPermission({ apply_info: [{ action: this.bizAction }] });
    if (res.url) {
      if (self === top) {
        window.open(res.url, '__blank');
      } else {
        try {
          window.top.BLUEKING.api.open_app_by_other('bk_iam', res.url);
        } catch (_) {
          window.open(res.url, '__blank');
        }
      }
    }
    this.loading = false;
  }
  private show() {
    this.select && this.select.show();
  }
  private close() {
    this.select && this.select.close();
  }
}
</script>
<style lang="postcss" scoped>
>>> .bk-select-loading {
  top: 6px;
}
.select {
  &-item {
    display: flex;
    &-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-right: 4px;
    }
    &-id {
      color: #c4c6cc;
      margin-right: 20px;
    }
    >>> .bk-icon {
      top: 3px;
      right: 0;
    }
  }
}
</style>
