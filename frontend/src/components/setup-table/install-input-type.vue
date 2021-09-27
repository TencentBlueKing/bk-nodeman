<template>
  <div :class="[`input-type input-${type}`, { 'is-focus': isFocus }]" :style="{ 'z-index': zIndex }" @click.stop>
    <div v-if="isFocus" class="input-type-border"></div>
    <!--input类型-->
    <bk-input
      :ref="type"
      v-if="isInput"
      :type="type"
      :value="inputValue"
      :placeholder="placeholder"
      :readonly="readonly"
      :disabled="disabled"
      @change="handleChange"
      @blur="handleBlur"
      @focus="handleFocus"
      @enter="handleEnter">
      <template v-if="appendSlot" slot="append">
        <div class="group-text">{{ appendSlot }}</div>
      </template>
    </bk-input>
    <div v-else-if="type === 'textarea'">
      <bk-input
        :ref="type"
        :type="type"
        :value="inputValue"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        :rows="currentRows"
        @change="handleChange"
        @blur="handleBlur"
        @focus="handleFocus"
        @enter="handleEnter">
      </bk-input>
      <span v-if="showEllipsis" class="input-text" @click="handleShowTextArea">{{ valueText }}</span>
    </div>
    <!-- 密码框 -->
    <bk-input
      :ref="type"
      v-else-if="type === 'password'"
      :type="passwordType"
      :value="inputValue"
      :placeholder="placeholder"
      :readonly="readonly"
      :disabled="disabled"
      :native-attributes="{
        autocomplete: 'off'
      }"
      @change="handleChange"
      @blur="handleBlur"
      @focus="handleFocus"
      @enter="handleEnter">
    </bk-input>
    <!--select类型-->
    <permission-select
      v-else-if="type === 'select'"
      ext-cls="input-select"
      permission-key="view"
      :permission="permission"
      :ref="type"
      :clearable="false"
      :value="inputValue"
      :popover-options="{ 'boundary': 'window' }"
      :placeholder="placeholder"
      :readonly="readonly"
      :disabled="disabled"
      :popover-min-width="popoverMinWidth"
      :option-list="options"
      :extension="prop === 'bk_cloud_id' && !options.length"
      @extension="handleCreate"
      @change="handleChange"
      @toggle="handleSelectChange">
    </permission-select>
    <!--file类型-->
    <div v-else-if="type === 'file'">
      <upload
        :value="inputValue"
        parse-text
        :max-size="10"
        unit="KB"
        :file-info="fileInfo"
        @change="handleUploadChange">
      </upload>
    </div>
    <!--业务选择器-->
    <div v-else-if="type === 'biz'">
      <bk-biz-select
        :value="inputValue"
        :show-select-all="false"
        :default-checked="false"
        :auto-update-storage="false"
        :multiple="multiple"
        :disabled="disabled"
        :readonly="readonly"
        :clearable="clearable"
        :auto-request="autoRequest"
        :ref="type"
        min-width="auto"
        @change="handleChange"
        @toggle="handleSelectChange">
      </bk-biz-select>
    </div>
    <!--权限类型-->
    <div v-else-if="type === 'auth'" class="input-auth">
      <bk-dropdown-menu
        :class="{ 'dropdown': authType === 'TJJ_PASSWORD' }"
        @show="handleDropdownShow()"
        @hide="handleDropdownHide()"
        ref="authType">
        <div slot="dropdown-trigger" class="auth-type">
          <span>{{ authName }}</span>
          <i :class="['arrow-icon nodeman-icon nc-arrow-down', { 'icon-flip': isDropdownShow }]"></i>
        </div>
        <ul class="bk-dropdown-list" slot="dropdown-content">
          <li v-for="auth in authentication"
              :key="auth.id"
              class="auth-options"
              @click.stop="handleAuthChange(auth)">
            <a>{{ auth.name }}</a>
          </li>
        </ul>
      </bk-dropdown-menu>
      <bk-input
        :value="$t('自动拉取')"
        class="auth-input"
        v-if="authType === 'TJJ_PASSWORD'"
        disabled>
      </bk-input>
      <bk-input
        :value="inputValue"
        :type="passwordType"
        class="auth-input"
        v-else-if="authType === 'PASSWORD'"
        :native-attributes="{
          autocomplete: 'off'
        }"
        @change="handleChange"
        @blur="handleBlur">
      </bk-input>
      <upload
        :value="inputValue"
        :disable-hover-cls="true"
        class="auth-input file"
        parse-text
        :max-size="10"
        unit="KB"
        v-else-if="authType === 'KEY'"
        @change="handleUploadChange">
      </upload>
    </div>
    <bk-switcher
      theme="primary"
      size="small"
      v-else-if="type === 'switcher'"
      :value="inputValue"
      @change="handleChange">
    </bk-switcher>
    <span v-else>--</span>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Emit, Model, Watch, Ref, Mixins } from 'vue-property-decorator';
import { IFileInfo } from '@/types';
import Upload from './upload.vue';
import PermissionSelect from '@/components/common/permission-select.vue';
import { authentication, IAuth } from '@/config/config';
import { isEmpty } from '@/common/util';
import emitter from '@/common/emitter';

// 支持的输入类型
const basicInputType = ['text', 'number', 'email', 'url', 'date'];
type IValue = string | number | boolean | Array<number | string>;

@Component({
  name: 'input-type',
  components: {
    Upload,
    PermissionSelect,
  },
})
export default class InputType extends Mixins(emitter) {
  @Model('update', { type: [String, Array, Number, Boolean], default: '' }) private inputValue!: IValue;

  @Prop({ type: String, default: '' }) private type!: string; // 输入框类型
  @Prop({ type: String, default: '' }) private prop!: string;
  @Prop({ type: Array, default: () => ([]) }) private splitCode!: string[]; // 值分隔方式
  @Prop({ type: Boolean, default: false }) private readonly autofocus!: boolean; // 是否自动聚焦
  @Prop({ type: Boolean, default: false }) private readonly readonly!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly disabled!: boolean;
  @Prop({ type: String, default: window.i18n.t('请输入') }) private placeholder!: string;
  @Prop({ type: Boolean, default: true }) private readonly multiple!: boolean; // biz select 框是否支持多选
  @Prop({ type: Array, default: () => ([]) }) private options!: Dictionary[]; // 下拉框数据源
  @Prop({ type: Number, default: 0 }) private popoverMinWidth!: number;
  @Prop({ type: Boolean, default: true }) private readonly autoRequest!: boolean;
  @Prop({ type: String, default: '' }) private subType!: string;
  @Prop({ type: String, default: '' }) private appendSlot!: string; // input类型插槽
  @Prop({ type: Boolean, default: false }) private readonly permission!: boolean; // select 权限控制
  @Prop({ type: Object, default: () => ({}) }) private readonly fileInfo!: IFileInfo;
  @Prop({ type: Boolean, default: false }) private readonly clearable!: boolean;

  @Ref('authType') private readonly authTypeRef: any;

  private inputRef: any;
  private authentication = authentication;
  private authType = this.subType;
  private isDropdownShow = false;
  private isFocus = false;
  private maxRows = 8;
  private rows = 1;

  private get authName(): string {
    const auth = this.authentication.find(auth => auth.id === this.authType) || { name: '' };
    return auth.name;
  }
  private get isInput(): boolean {
    return basicInputType.includes(this.type);
  }
  private get passwordType(): string {
    if (!isEmpty(this.inputValue)) {
      return 'password';
    }
    return 'text';
  }
  private get zIndex(): number {
    return this.isFocus ? 99 : 0;
  }
  private get currentRows(): number {
    return this.isFocus ? this.rows : 1;
  }
  private get valueText(): string {
    if (this.rows > 1 && this.inputValue) {
      // @ts-ignore: Unreachable code error
      const data = this.inputValue.split('\n').map((text: string) => text.trim())
        .filter((text: string) => text);
      return data.join(',');
    }
    // @ts-ignore: Unreachable code error
    return this.inputValue;
  }
  private get showEllipsis(): boolean {
    if (this.type === 'textarea') {
      return this.isFocus ? false : (this.rows > 1);
    }
    return false;
  }

  @Watch('inputValue')
  public handleValueChange() {
    this.$nextTick(this.setRows);
  }

  private created() {
    this.dispatch('step-verify-input', 'verify-registry', this);
  }
  private mounted() {
    // 是否自动聚焦
    this.inputRef = this.$refs[this.type];
    if (this.autofocus) {
      if (this.isInput || this.type === 'password') {
        // 输入框类型自动focus
        this.inputRef && this.inputRef.focus();
      } else if (['select', 'biz'].includes(this.type)) {
        // select框类型focus（展示下拉列表）
        this.inputRef && this.inputRef.show();
      }
    }
  }
  private beforeDestroy() {
    this.dispatch('step-verify-input', 'verify-remove');
  }

  @Emit('update')
  public handleEmitUpdate(value: IValue) {
    return value;
  }
  @Emit('change')
  public handleEmitChange(value: IValue) {
    return { value, instance: this };
  }
  @Emit('blur')
  public handleEmitBlur(value: IValue) {
    return { value, instance: this };
  }
  @Emit('upload-change')
  public handleEmitUpload(value: IFileInfo) {
    return value;
  }
  /**
   * input change时触发
   */
  public handleChange(value: IValue) {
    this.handleEmitUpdate(value);
    this.handleEmitChange(value);
  }
  /**
   * 失焦
   */
  public handleBlur(value: IValue) {
    this.isFocus = false;
    this.handleEmitBlur(value);
    this.dispatch('step-verify-input', 'verify-blur', this.inputValue);
  }
  /**
     * 文件变更时事件
     */
  public handleUploadChange({ value, fileInfo }: { value: string, fileInfo: IFileInfo }) {
    this.handleEmitUpdate(value);
    this.handleEmitUpload({ value, ...fileInfo });
  }
  /**
     * 业务选择器折叠和收起时触发事件
     */
  @Emit('toggle')
  public handleSelectChange(toggle: boolean) {
    this.isFocus = !!toggle;
    if (!toggle) {
      this.handleEmitBlur(this.inputValue);
      this.dispatch('step-verify-input', 'verify-blur', this.inputValue);
    } else {
      this.dispatch('step-verify-input', 'verify-focus', this.inputValue);
    }
    return toggle;
  }
  /**
     * 认证方式change
     * @param {Object} auth
     */
  public handleAuthChange(auth: IAuth) {
    this.authType = auth.id;
    this.inputValue = '';
    if (this.authType === 'TJJ_PASSWORD') {
      this.handleBlur(window.i18n.t('自动拉取'));
    }
    this.authTypeRef.hide();
  }
  public handleDropdownShow() {
    this.isDropdownShow = true;
  }
  public handleDropdownHide() {
    this.isDropdownShow = false;
  }
  @Emit('enter')
  public handleEnter(value: IValue) {
    return { value, instance: this };
  }
  @Emit('focus')
  public handleFocus(value: IValue) {
    this.isFocus = true;
    return { value, instance: this };
  }
  public setRows() {
    if (this.type !== 'textarea') return;
    // @ts-ignore: Unreachable code error
    const rows = this.inputValue.split('\n').length || 1;
    this.rows = Math.min(this.maxRows, rows);
  }
  public handleShowTextArea() {
    this.isFocus = true;
    this.inputRef && this.inputRef.focus();
  }
  // select 下拉新增事件 - 少量，不做派发
  public handleCreate() {
    if (this.prop === 'bk_cloud_id') {
      this.$router.push({ name: 'cloudManager' });
    }
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  .input-type {
    position: relative;
    width: 100%;
    &.is-focus {
      z-index: 5;
      .input-type-border {
        display: block;
      }
      >>> textarea {
        border: 1px solid #3a84ff;
        background: #fff;
      }
    }
    &.input-textarea {
      .input-type-border {
        display: none;
      }
    }
    >>> .bk-textarea-wrapper textarea {
      height: auto;
      min-height: 29px;
    }
    .input-select {
      width: 100%;
    }
    .input-auth {
      @mixin layout-flex row;
      .dropdown {
        z-index: 1;
      }
      .auth-type {
        padding: 0 6px;
        margin-right: -1px;
        border: 1px solid #c4c6cc;
        border-radius: 2px 0 0 2px;
        min-width: 80px;
        height: 32px;
        background: #fafbfd;

        @mixin layout-flex row, center, center;
        .arrow-icon {
          font-size: 20px;
          transition: all .2s ease;
          &.icon-flip {
            transform: rotate(180deg)
          }
        }
      }
      .auth-options {
        cursor: pointer;
      }
      .auth-input {
        &.file {
          width: 100%;
          >>> .upload-info {
            border: 1px solid #c4c6cc;
          }
        }
        >>> .bk-form-input {
          border-radius: 0 2px 2px 0;
        }
        >>> .upload-btn {
          border-radius: 0 2px 2px 0;
        }
      }
    }
    .input-text {
      position: absolute;
      top: 0;
      left: 0;
      padding: 5px 10px;
      height: 43px;
      width: 100%;
      color: #63656e;
      background-color: #fff;
      z-index: 1;
      cursor: text;
      line-height: 30px;
      border-radius: 2px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .group-text {
      padding: 0 4px;
    }
  }
</style>
