<template>
  <bk-select
    ref="permissionSelect"
    :value="selectValue"
    :placeholder="placeholder"
    :loading="loading"
    :ext-cls="extCls"
    :searchable="searchable"
    :multiple="multiple"
    :clearable="clearable"
    :readonly="readonly"
    :disabled="disabled"
    :popover-options="{ 'boundary': 'window' }"
    :popover-min-width="popoverMinWidth"
    @selected="handleSelected"
    @toggle="handleToggle"
    @change="handleChange"
    @clear="handleClear">
    <template v-for="item in optionList">
      <bk-option
        :key="item[optionId]"
        :id="item[optionId]"
        :name="item[optionName]"
        :class="{ 'is-auth-disabled': openPermission && !(item.permission || item[permissionKey]) }"
        :disabled="item.disabled"
        @mouseenter.native="(e) => optionMouseenter(e, item)"
        @mouseleave.native="(e) => optionMouseleave(e, item)">
        <div class="bk-option-content-default" :title="item[optionName]">
          <span class="bk-option-name">
            {{ item[optionName] }}
          </span>
          <i
            v-if="multiple && selectValue.includes(item[optionId])"
            class="select-item-icon bk-option-icon bk-icon icon-check-1">
          </i>
          <auth-component
            v-if="openPermission && !(item.permission || item[permissionKey])"
            class="bk-option-content-default"
            tag="div"
            :auto-emit="true"
            :title="item[optionName]"
            :authorized="!permissionKey || item[permissionKey]"
            :apply-info="[{
              action: item.permissionType || permissionType,
              instance_id: item[instanceId],
              instance_name: item[instanceName]
            }]"
            @click="handleSelectClose">
          </auth-component>
        </div>
      </bk-option>
    </template>
    <div v-if="extension" slot="extension" style="cursor: pointer;" @click="handleExtension">
      <i class="bk-icon icon-plus-circle mr5"></i>{{ $t('新增') }}
    </div>
  </bk-select>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Watch, Ref, Model } from 'vue-property-decorator';
import { MainStore } from '@/store/index';
import { IBizValue } from '@/types';

interface IItem {
  [key: string]: any
}

@Component({ name: 'permission-select' })
export default class PermissionSelect extends Vue {
  @Model('update', { type: [String, Array, Number] }) private value!: IBizValue;

  @Prop({ type: Array, default: () => ([]) }) private optionList!: IItem[];
  @Prop({ type: String, default: '' }) private extCls!: string; // 外部样式
  @Prop({ type: String, default: '' }) private placeholder!: string;
  @Prop({ type: Boolean, default: false }) private loading!: boolean;
  @Prop({ type: Boolean, default: false }) private multiple!: boolean;
  @Prop({ type: Boolean, default: false }) private searchable!: boolean;
  @Prop({ type: Boolean, default: false }) private clearable!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly!: boolean;
  @Prop({ type: Boolean, default: false }) private disabled!: boolean;
  @Prop({ type: String, default: 'id' }) private optionId!: string;
  @Prop({ type: String, default: 'name' }) private optionName!: string;
  @Prop({ type: Boolean, default: false }) private extension!: boolean; // extension slot
  @Prop({ type: [String, Boolean, Number], default: true }) private permission!: boolean | string | number; // 权限控制
  @Prop({ type: String, default: '' }) private permissionKey!: string; // 权限字段
  @Prop({ type: String, default: '' }) private permissionType!: string; // 权限类型
  @Prop({ type: String, default: '' }) private permissionId!: string; // 自定义权限实例的id 和name
  @Prop({ type: String, default: '' }) private permissionName!: string;
  @Prop({ type: Number, default: 0 }) private popoverMinWidth!: number;

  @Ref('permissionSelect') private readonly permissionSelect: any;

  private selectValue: IBizValue = this.value;
  private optPop: any = null;

  private get openPermission(): boolean {
    return MainStore.permissionSwitch && !!this.permission;
  }
  private get selectedItems(): IItem {
    if (this.selectValue instanceof Array) {
      // @ts-ignore: Unreachable code error
      return this.optionList.filter(item => this.selectValue.includes(item[this.optionId])
        && (this.openPermission ? item.permission || item[this.permissionKey] : true));
    }
    return this.optionList.filter(item => this.selectValue === item[this.optionId]
      && (this.openPermission ? item.permission || item[this.permissionKey] : true));
  }
  // 实例id
  private get instanceId(): string {
    return this.openPermission ? this.permissionId || this.optionId : this.optionId;
  }
  // 实例名称
  private get instanceName(): string {
    return this.openPermission ? this.permissionName || this.optionName : this.optionName;
  }

  @Watch('value')
  public handleWatchValue(v: IBizValue) {
    this.selectValue = v;
  }

  private created() {
    this.handleInit();
  }

  private async handleInit() {
    if (this.openPermission) {
      const copyValue = JSON.stringify(this.selectValue);
      if (Array.isArray(this.selectValue)) {
        // @ts-ignore: Unreachable code error
        this.selectValue = this.optionList.filter(item => this.selectValue.includes(item[this.optionId])
          && (item.permission || item[this.permissionKey]));
      } else {
        const option = this.optionList.find(item => this.selectValue === item[this.optionId]
          && (item.permission || item[this.permissionKey]));
        this.selectValue = option ? option[this.optionId] : '';
      }
      this.handleUpdate(this.selectValue);
      if (JSON.stringify(this.selectValue) !== copyValue) {
        this.handleChange(this.selectValue);
        // this.$emit('change', this.selectValue, copyValue, this.selectedItems)
      }
    }
  }
  @Emit('update')
  private handleUpdate(value: IBizValue) {
    return value;
  }
  @Emit('selected')
  private handleSelected(value: IBizValue) { // , options: IItem
    return value;
    // return { value, options, item: this.selectedItems }
  }
  @Emit('toggle')
  private handleToggle(toggle: boolean) {
    return toggle;
    // return { toggle, item: this.selectedItems }
  }
  @Emit('change')
  private handleChange(newValue: IBizValue) { // , oldValue: IBizValue
    this.selectValue = newValue;
    this.handleUpdate(newValue);
    return newValue;
    // return { newValue, oldValue, item: this.selectedItems }
  }
  @Emit('clear')
  private handleClear(oldValue: IBizValue) {
    return oldValue;
    // return { oldValue, item: this.selectedItems }
  }
  @Emit('extension')
  private handleExtension() {
    return false;
  }
  private optionMouseenter(e: MouseEvent, option: IItem) {
    if (option.tip && !this.optPop) {
      this.optPop = this.$bkPopover(e.target!, {
        content: option.tip,
        trigger: 'manual',
        theme: 'dark',
        interactive: true,
        arrow: true,
        placement: 'right',
        maxWidth: 300,
        delay: 100,
        distance: 12,
        followCursor: false,
        flip: true,
        boundary: 'window',
        zIndex: 2000,
      });
    }
    this.optPop && this.optPop.show();
  }
  private optionMouseleave() {
    this.optPop?.hide();
    this.optPop?.destroy();
    this.optPop = null;
  }
  private handleSelectClose() {
    this.permissionSelect.close();
  }
  private show() {
    this.permissionSelect && this.permissionSelect.show();
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
      }
    }
  }
</style>
