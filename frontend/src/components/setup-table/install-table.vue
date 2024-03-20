<template>
  <div :class="`install-table-wrapper table-${virtualScroll && hasScroll ? 'has' : 'not'}-scroll`">
    <!-- 表头 -->
    <section :class="['install-table-header', { 'table-setting': localMark }]">
      <div class="table-header">
        <table class="form-table">
          <colgroup>
            <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
          </colgroup>
          <thead>
            <tr v-if="tableParentHead.length">
              <th v-for="config in tableParentHead" :key="config.prop" :colspan="config.colspan">
                <TableHeader
                  :ref="`header_${config.prop}`"
                  v-bind="{
                    tips: config.tips,
                    label: config.label,
                    colspan: config.colspan,
                    required: config.required,
                  }">
                </TableHeader>
              </th>
            </tr>
            <tr>
              <th v-for="(config, index) in tableHead" :key="config.prop">
                <div class="cell">
                  <ColumnSetting
                    v-if="colSetting && index === tableHead.length - 1"
                    class="column-setting"
                    filter-head
                    :local-mark="localMark"
                    :font-setting="false"
                    :value="filter"
                    @update="handleColumnUpdate">
                  </ColumnSetting>
                  <TableHeader
                    :ref="`header_${config.prop}`"
                    v-else
                    v-bind="{
                      prop: config.prop,
                      tips: config.tips,
                      label: config.label,
                      required: !config.noRequiredMark && config.required,
                      batch: config.getBatch ? config.getBatch.call(_self) : config.batch,
                      isBatchIconShow: !!table.data.length
                        && (config.getBatch ? config.getBatch.call(_self) : config.batch),
                      type: config.type,
                      subTitle: config.subTitle,
                      options: getCellInputOptions({}, config),
                      multiple: !!config.multiple,
                      searchable: !!config.searchable,
                      placeholder: config.placeholder,
                      appendSlot: config.appendSlot,
                      parentProp: config.parentProp,
                      parentTip: config.parentTip,
                      focusRow: focusRow
                    }"
                    @confirm="handleBatchConfirm(arguments, config)">
                  </TableHeader>
                </div>
              </th>
            </tr>
          </thead>
        </table>
      </div>
    </section>
    <!-- 表体 -->
    <section
      v-if="table.data.length"
      class="install-table-body"
      ref="tableBody"
      :style="{ 'height': height }"
      @scroll="rootScroll">
      <div ref="scrollPlace" class="virtual-scroll-wrapper" :style="ghostStyle" v-if="virtualScroll"></div>
      <div class="body-content" :class="{ 'virtual-scroll-content': virtualScroll }" ref="content">
        <table class="form-table" v-test.common="'installTable'">
          <colgroup>
            <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
          </colgroup>
          <tbody class="table-body">
            <tr v-for="(row, rowIndex) in renderData" :key="row.id">
              <td v-for="(config, colIndex) in tableHead" :key="colIndex">
                <div class="cell-operate" v-if="config.type === 'operate'">
                  <i class="cell-operate-plus nodeman-icon nc-plus" @click="handleAddItem(row.id)" v-if="needPlus"></i>
                  <i
                    class="cell-operate-delete nodeman-icon nc-minus"
                    :disabled="disableDelete"
                    @click="handleDeleteItem(row.id)"></i>
                </div>
                <!-- 验证输入 -->
                <VerifyInput
                  position="right"
                  error-mode="mask"
                  :id="row.id"
                  :prop="config.prop"
                  :required="config.required"
                  :required-handle="() => requiredHandle(row, config)"
                  :rules="config.rules"
                  :icon-offset="config.iconOffset"
                  :default-validator="getDefaultValidator(row, config)"
                  :proxy-status="getCurrentProxyStatus(row, config)"
                  :ref="`verify_${rowIndex}_${config.prop}`"
                  v-else
                  @jump-proxy="handleGotoProxy(row)"
                  @validator-change="setValidator(row, config.prop, ...arguments)">
                  <!-- 查看态（不要嵌入组件，防止虚拟滚动的时候渲染卡顿） -->
                  <div :class="['ghost-wrapper', {
                         'is-disabled': getCellDisabled(row, config)
                       }]"
                       v-if="virtualScroll && !editStatus(row, config) && getDisabledType(row, config)"
                       @click="handleShowEdit(row, config)">
                    <!-- 下拉框 -->
                    <span class="ghost-input bk-form-input select"
                          v-if="['select','biz'].includes(getCellInputType(row, config))"
                          :data-placeholder="getDisplayName(row, config) ? '' : config.placeholder">
                      <span class="name" v-bk-overflow-tips>{{ getDisplayName(row, config) }}</span>
                      <i class="bk-icon icon-angle-down"></i>
                    </span>
                    <!-- 密码框 -->
                    <span class="ghost-input bk-form-input password"
                          :data-placeholder="row[config.prop] || getPwdFillEnable(row, config)
                            ? ''
                            : config.placeholder"
                          v-else-if="getCellInputType(row, config) === 'password'">
                      <span class="name">{{ hidePassword(row, config) }}</span>
                    </span>
                    <!-- 限速输入 -->
                    <span class="ghost-input speed"
                          :data-placeholder="row[config.prop] ? '' : config.placeholder"
                          v-else-if="config.appendSlot">
                      <span class="name">{{ row[config.prop] }}</span>
                      <span class="speed-unit">MB/s</span>
                    </span>
                    <span class="ghost-input bk-form-input"
                          :data-placeholder="row[config.prop] ? '' : config.placeholder"
                          v-else>
                      <span class="name" v-bk-overflow-tips>{{ row[config.prop] }}</span>
                    </span>
                  </div>
                  <!-- 编辑态 -->
                  <InstallInputType
                    v-else
                    v-model.trim="row[config.prop]"
                    :class="{ 'fixed-form-el': getCellInputType(row, config) === 'switcher' }"
                    v-bind="{
                      clearable: false,
                      prop: config.prop,
                      type: getCellInputType(row, config),
                      disabled: getCellDisabled(row, config),
                      options: getCellInputOptions(row, config),
                      placeholder: config.placeholder,
                      multiple: !!config.multiple,
                      splitCode: config.splitCode,
                      popoverMinWidth: config.popoverMinWidth,
                      autoRequest: !!config.autoRequest,
                      appendSlot: config.appendSlot,
                      permission: config.permission,
                      autofocus: virtualScroll,
                      wrapperBorder: true,
                      pwdFill: getPwdFillEnable(row, config),
                      fileInfo: getCellFileInfo(row, config)
                    }"
                    @focus="handleCellFocus(arguments, { row, config, rowIndex, colIndex })"
                    @blur="handleCellBlur(arguments, { row, config, rowIndex, colIndex })"
                    @input="handleCellValueInput(arguments, row, config)"
                    @choose="handleCellChoose(arguments, { row, config, rowIndex, colIndex })"
                    @change="handleCellValueChange(row, config)"
                    @upload-change="handleCellUploadChange($event, row)">
                  </InstallInputType>
                </VerifyInput>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <!--空数据内容区-->
    <section class="table-empty" v-if="!table.data.length">
      <slot name="empty">
        <i class="table-empty-icon bk-icon icon-empty"></i>
        <span class="table-empty-text">{{ $t('暂无数据') }}</span>
      </slot>
    </section>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop, Ref, Emit, Watch } from 'vue-property-decorator';
import { MainStore, AgentStore } from '@/store/index';
import { bus } from '@/common/bus';
import ColumnSetting from '@/components/common/column-setting.vue';
import VerifyInput from '@/components/common/verify-input.vue';
import InstallInputType from './install-input-type.vue';
import { throttle, isEmpty } from '@/common/util';
import TableHeader from './table-header.vue';
import { STORAGE_KEY_COL } from '@/config/storage-key';
import { Context } from 'vm';
import { IFileInfo, IKeysMatch, ISetupHead, ISetupRow, ITabelFliter, ISetupParent } from '@/types';
import { getDefaultConfig, passwordFillText } from '@/config/config';
import { splitCodeArr } from '@/common/regexp';
import { IAp } from '@/types/config/config';
import { ICloudSource } from '@/types/cloud/cloud';

interface IFilterRow {
  [key: string]: ITabelFliter
}

@Component({
  name: 'InstallTable',
  components: {
    ColumnSetting,
    VerifyInput,
    InstallInputType,
    TableHeader,
  },
})

export default class SetupTable extends Vue {
  // 安装信息
  @Prop({
    type: Object,
    default: () => ({ header: [], data: [] }),
    validator(v) {
      return v && Array.isArray(v.header);
    },
  }) private readonly setupInfo!: { header: ISetupHead[], data: ISetupRow[], parentHead?: ISetupParent[] };

  // 是否启用校验错误时自动排序
  @Prop({ type: Boolean, default: false }) private readonly autoSort!: boolean;
  // 安装信息最小数量
  @Prop({ type: Number, default: 1 }) private readonly minItems!: number;
  // body 内容区域高度
  @Prop({ type: String, default: 'auto' }) private readonly height!: string;
  // 是否支持虚拟滚动（需要设置高度）
  @Prop({ type: Boolean, default: false }) private readonly virtualScroll!: boolean;
  // 是否支持添加操作
  @Prop({ type: Boolean, default: true }) private readonly needPlus!: boolean;
  // 额外参数
  @Prop({ type: Array, default: () => [] }) private readonly extraParams!: string[];
  // 是否为手动安装，校验和管控区域变更时需要此变量
  @Prop({ type: Boolean, default: false }) private readonly isManual!: boolean;
  // 是否开启表头设置
  @Prop({ type: Boolean, default: true }) private readonly colSetting!: boolean;
  @Prop({ type: String, default: '' }) private readonly localMark!: string;
  @Prop({ type: Function }) private readonly beforeDelete!: Function;
  @Prop({ type: Number }) private readonly bkCloudId!: number;
  @Prop({ type: Array }) private readonly aps!: IAp[];
  @Prop({ type: Array }) private readonly clouds!: ICloudSource[];
  @Prop() private readonly arbitrary!: any; // 可以是任意值, 用来在config文件里做为必要的一些参数
  @Prop({ type: String, default: '' }) private readonly type!: string;

  @Ref('tableBody') private readonly tableBody!: any;
  @Ref('scrollPlace') private readonly scrollPlace!: any;
  @Ref('content') private readonly content!: any;

  //  表格信息
  private table: { data: ISetupRow[], config: ISetupHead[] } = {
    data: [],
    config: [],
  };
  private tableParentHead: ISetupParent[] = [];
  private tableHead: ISetupHead[] = [];
  private filter: IFilterRow = {};
  private startIndex = 0;
  private endIndex = 0;
  private itemHeight = 44;
  private id = 0;
  private popoverEl: any = null;
  // 滚动节流
  private handleScroll!: Function;
  // 处于编辑态的数据
  public editData: {  id: number, prop: string }[] = [];
  private hasScroll= false;
  private listenResize!: Function;
  private focusRow: any = {};

  private get fetchPwd() {
    return AgentStore.fetchPwd;
  }
  private get cloudList() {
    return this.clouds || AgentStore.cloudList;
  }
  private get apList() {
    return this.aps || AgentStore.apList;
  }
  private get channelList() {
    return AgentStore.channelList;
  }
  private get ghostStyle() {
    const allDataLength = this.table.data ? this.table.data.length : 0;
    return {
      height: `${allDataLength * this.itemHeight}px`,
    };
  }
  private get renderData() {
    if (this.table.data && this.virtualScroll) {
      // 滚动后重置编辑态
      this.editData = [];
      return this.table.data.slice(this.startIndex, this.endIndex);
    }
    return this.table.data || [];
  }
  private get disableDelete() {
    return this.table.data.length <= this.minItems;
  }

  @Watch('table.data.length')
  public handleTableLengthChange(len: number) {
    if (len) {
      this.$nextTick(this.handleResize);
    } else {
      this.hasScroll = false;
    }
  }

  private created() {
    this.handleInit();
  }
  private mounted() {
    this.handleScroll();
    window.addEventListener('resize', this.initTableHead);
  }
  private beforeDestroy() {
    window.removeEventListener('resize', this.initTableHead);
  }

  /**
   * 初始化
   */
  private handleInit() {
    this.handleScroll = throttle(this.rootScroll, 0);
    const table = {
      config: this.setupInfo.header,
      data: this.setupInfo.data || [],
    };
    // 初始化表格默认最小数据个数
    if (table.data.length < this.minItems) {
      const fillNum = this.minItems - table.data.length;
      table.data.push(...Array.from(new Array(fillNum)));
    }
    // 添加初始化的属性
    table.data = table.data.map((item) => {
      const row = item || {};
      this.id += 1;
      row.id = this.id;
      table.config.forEach((config) => {
        if (config.prop) {
          this.addPropToData(row, config);
        }
      });
      return Object.assign({}, row); // 切断引用- 密码框问题
    });
    this.$set(this, 'table', table);
    this.table.config.forEach((config) => {
      this.handleBindRules(config);
    });
    if (this.localMark) {
      this.initCustomColStatus();
    } else {
      this.tableHead = this.table.config;
    }
  }
  /**
   * 修改配置文件的this指向
   */
  private handleBindRules(config: { rules?: any[] }) {
    if (config.rules) {
      config.rules.forEach((rule) => {
        if (typeof rule.validator === 'function') {
          rule.validator.bind = function (context: Context) {
            // eslint-disable-next-line @typescript-eslint/no-this-alias
            const me = this;
            const fBind = function (...args: any[]) {
              return me.call(me.prototype.context, ...args);
            };
            if (!me.prototype.context) {
              fBind.prototype.context = context;
              me.prototype = fBind.prototype;
            } else {
              me.prototype.context = context;
              fBind.prototype = me.prototype;
            }
            return fBind;
          };
          rule.validator = rule.validator.bind(this);
        }
      });
    }
  }
  /**
   * 添加额外属性
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  private addPropToData(row: ISetupRow | any, config: ISetupHead) {
    const prop = config.prop as keyof ISetupRow;
    if (typeof config.getDefaultValue === 'function') {
      row[prop] = config.getDefaultValue.call(this, row);
    } else {
      row[prop] = isEmpty(row[prop]) && !isEmpty(config.default) ? config.default : row[prop];
    }
    row.validator = {};
  }
  /**
   * 获取select框的options数据
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  private getCellInputOptions(row: ISetupRow, config: ISetupHead): any[] {
    if (config.prop === 'bk_biz_id') {
      return MainStore.bkBizList.map(item => ({
        id: item.bk_biz_id,
        name: item.bk_biz_name,
      }));
    } if (config.type === 'select') {
      return config.getOptions ? config.getOptions.call(this, row) : config.options;
    }
    return [];
  }
  /**
   * 获取可直接编辑的输入类型
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  private getDisabledType(row: ISetupRow, config: ISetupHead) {
    let { type } = config;
    if (config.getCurrentType) {
      type = config.getCurrentType.call(this, row);
    }
    return !['switcher', 'file'].includes(type);
  }
  /**
   * 获取当前cell的输入类型
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  private getCellInputType(row: ISetupRow, config: ISetupHead) {
    if (config.getCurrentType) {
      return config.getCurrentType.call(this, row);
    }
    return config.type;
  }
  /**
   * 获取当前cell是否只读
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  private getCellDisabled(row: ISetupRow, config: ISetupHead) {
    if (config.getReadonly) {
      return !!config.getReadonly.call(this, row, this.bkCloudId === window.PROJECT_CONFIG.DEFAULT_CLOUD);
    }
    return !!config.readonly;
  }
  private getPwdFillEnable(row: ISetupRow, config: ISetupHead) {
    return row.bk_host_id && config.type === 'password' && !row.re_certification; // 忽略 proxy——id
  }
  private getCellFileInfo(row: ISetupRow, config: ISetupHead) {
    if (row.fileInfo && row[config.prop as keyof ISetupRow]) {
      return row.fileInfo;
    }
    return null;
  }
  // 把当前值回填到另一表单里
  private handleCellValueInput(arg: any[], row: ISetupRow, config: ISetupHead) {
    const [newValue] = arg;
    const prop = config.prop as IKeysMatch<ISetupRow, string>;
    const sync = config.sync as IKeysMatch<ISetupRow, string>;
    const syncSource = typeof row[prop] === 'undefined' ? '' : row[prop].trim();
    const syncTarget = typeof row[sync] === 'undefined' ? '' : row[sync].trim();
    if (sync && syncSource === syncTarget) {
      row[sync] = newValue;
    }
  }
  /**
   * 当前cell change事件
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  @Emit('change')
  private handleCellValueChange(row: ISetupRow, config: ISetupHead) {
    MainStore.updateEdited(true);
    const prop = config.prop as IKeysMatch<ISetupRow, string>;
    if (config.type !== 'textarea' && row[prop] && typeof row[prop] === 'string') {
      row[prop] = row[prop].trim();
    }
    if (config.handleValueChange) {
      config.handleValueChange.call(this, row);
    }
    return { row, config };
  }
  private handleCellUploadChange(fileInfo: IFileInfo, row: ISetupRow) {
    if (fileInfo) {
      MainStore.updateEdited(true);
      row.fileInfo = !isEmpty(fileInfo.value) ? fileInfo : undefined;
    }
  }
  private getCurrentProxyStatus(row: ISetupRow, config: ISetupHead) {
    if (config.getProxyStatus) {
      return config.getProxyStatus.call(this, row);
    }
    return '';
  }
  @Emit('choose')
  private handleCellChoose(arg: any[], bb: { row: ISetupRow }) {
    const [param] = arg;
    const { row } = bb;
    return { instance: param.instance, row };
  }
  private rootScroll() {
    if (!this.virtualScroll) return;

    if (this.table.data && this.table.data.length) {
      this.updateRenderData(this.tableBody.scrollTop);
    }
  }
  /**
   * 更新可视区域的数据列表
   * @param {Number} scrollTop 滚动条高度
   */
  private updateRenderData(scrollTop = 0) {
    // 可视区显示的条数 (数字 16 ： 上下边距)
    const count = Math.ceil((this.tableBody.clientHeight + 16) / this.itemHeight);
    // 滚动后可视区新的 startIndex
    const newStartIndex = Math.floor(scrollTop / this.itemHeight);
    // 滚动后可视区新的 endIndex
    const newEndIndex = newStartIndex + count;
    this.startIndex = newStartIndex;
    this.endIndex = newEndIndex;
    this.content.style.transform = `translate3d(0, ${newStartIndex * this.itemHeight}px, 0)`;
  }
  /**
   * 添加
   * @param {Number} id
   */
  @Emit('add')
  public handleAddItem(id: number) {
    const index = this.table.data.findIndex(item => item.id === id) || 0;
    this.id += 1;
    const row = {
      id: this.id,
    };
    this.table.config.forEach((config) => {
      if (config.prop) {
        this.addPropToData(row, config);
      }
    });
    this.table.data.splice(index + 1, 0, row as ISetupRow);
    return;
  }
  /**
   * 删除
   * @param {Number} id
   */
  private handleDeleteItem(id: number) {
    if (this.disableDelete) return;
    if (this.beforeDelete && typeof this.beforeDelete === 'function') {
      this.beforeDelete(id, this.table.data, () => {
        this.deleteItem(id);
      });
    } else {
      this.deleteItem(id);
    }
  }
  @Emit('delete')
  private deleteItem(id: number) {
    const index = this.table.data.findIndex(item => item.id === id);
    if (index !== -1) {
      this.table.data.splice(index, 1);
    }
    return index;
  }
  /**
   * 通用方法：配置文件内调用唯一性校验
   */
  private handleValidateUnique(row: ISetupRow | any, config: ISetupHead) {
    if (!row || !config) return;
    const rowId = row.id;
    const { prop, splitCode } = config;
    let value = row[config.prop] || '';
    // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
    if (splitCode && splitCode.length) {
      const split = this.getSplitCode(splitCode, value);
      value = this.handleTrimArray(value.split(split));
    }
    const ipRepeat = this.table.data.some((row: ISetupRow | any) => {
      if (row.id === rowId) return false;
      let targetValue = !isEmpty(row[prop]) ? row[prop].trim() : '';
      // 1. 处理多值的情况
      // eslint-disable-next-line @typescript-eslint/prefer-optional-chain
      if (splitCode && splitCode.length) {
        const targetSplit = this.getSplitCode(splitCode, targetValue);
        targetValue = this.handleTrimArray(targetValue.split(targetSplit));
      }
      // 2.校验和其他行的值不能重复
      return Array.isArray(value) && Array.isArray(targetValue)
        ? value.some(v => targetValue.includes(v))
        : value === targetValue;
    });
    return !ipRepeat;
  }
  /**
   * 通用方法：配置文件内调用 - 多IP对应性校验
   */
  private handleValidateEqual(row: ISetupRow | any, config: ISetupHead) {
    if (!row || !config) return true;
    const { prop, reprop, splitCode } = config;
    let value = row[prop] || '';
    let reValue = row[reprop as string] || '';
    if (!reValue) return true;
    if (splitCode?.length) {
      const split = this.getSplitCode(splitCode, value);
      const reSplit = this.getSplitCode(splitCode, reValue);
      value = this.handleTrimArray(value.split(split));
      reValue = this.handleTrimArray(reValue.split(reSplit));
    }
    return value.length === reValue.length;
  }
  private handleTrimArray(arr: string[]) {
    if (!arr || !arr.length) return;
    return arr.filter(text => !!text).map(text => text.trim());
  }
  private getSplitCode(splitCode: string[], value: string) {
    return splitCode.find(split => value.indexOf(split) > 0);
  }
  // 多选一必填的校验
  private requiredHandle(row: ISetupRow | any, config: ISetupHead) {
    let required = false;
    const value = row[config.prop];
    if (isEmpty(value) && config.required) {
      required = config.requiredPick?.length
        ? !config.requiredPick.some(prop => row[prop]?.trim())
        : true;
    }
    return required;
  }
  private handleValidateValue(row: ISetupRow | any, config: ISetupHead) {
    const validator = {
      show: false,
      message: '',
      type: '',
    };
    if (!row || !config) return validator;

    const value = row[config.prop];
    // 密码校验区分手动安装
    if (!config.required && config.prop === 'prove') {
      // 1. 密码过期校验
      if (!row.is_manual && isEmpty(value) && row.re_certification) {
        validator.show = true;
        validator.message = window.i18n.t('认证信息过期');
      }
      return validator;
    }
    // 为空就不需要继续校验
    if (isEmpty(value)) {
      // 2. 必填项校验
      if (config.required) {
        validator.message = window.i18n.t('必填项');
        // 多选一
        validator.show = config.requiredPick?.length
          ? !config.requiredPick.some(prop => row[prop]?.trim())
          : true;
      }
      return validator;
    }
    // 3. rules校验
    config.rules && config.rules.some((rule: any) => {
      if (rule.regex && !isEmpty(value)) {
        validator.show = !rule.regex.test(value);
        validator.message = rule.message;
      } else if (rule.validator && typeof rule.validator === 'function') {
        const isValidate = rule.validator(value, row.id);
        validator.show = !isValidate;
        validator.message = rule.message || '';
      }
      // 存在失败校验就终止
      return validator.show;
    });
    if (validator.show) return validator;

    // 4. 唯一性校验
    if (config.unique && !isEmpty(value)) {
      const unique = this.handleValidateUnique(row, config);
      validator.type = ['inner_ip', 'inner_ipv6'].includes(config.prop) && !unique ? 'unique' : '';
      validator.show = !unique;
      validator.message = window.i18n.t('冲突校验', { prop: 'IP' });
    }
    return validator;
  }
  /**
   * 外部调用的校验方法
   */
  private validate() {
    const union: { [key: string]: any } = {};
    const failedProp: string[] = [];
    const isValidate = this.table.data.map((row: ISetupRow | any, index: number) => {
      // 当前行是否校验通过：true通过，false不通过
      row.isRowValidate = this.table.config.map((config) => {
        if (!config.prop) return true;
        const value = row[config.prop];
        // 普通校验
        const validator = this.handleValidateValue(row, config);
        if (config.unique && config.prop === 'inner_ip') { // 只做innerip的合并
          row.errType = validator.type;
        }

        if (!validator.show && config.union && value && !isEmpty(row[config.union])) {
          // 联合校验
          union[config.prop] = union[config.prop] ? union[config.prop] : [];
          const unionValue = value + row[config.union];
          validator.show = union[config.prop].includes(unionValue);
          validator.message = window.i18n.t('冲突校验', { prop: config.label });
          union[config.prop].push(unionValue);
        }

        this.$set((this.table.data[index] as any).validator, config.prop, validator);
        if (validator.show) {
          failedProp.push(config.prop);
        }
        return !validator.show;
      }).every(val => !!val);

      return row.isRowValidate;
    }).every(isRowValidate => !!isRowValidate);

    this.autoSort && this.sortTableData();
    this.$nextTick().then(() => {
      Object.keys(this.$refs).forEach((refKey) => {
        if (refKey.includes('verify_')) {
          (this.$refs[refKey] as any[]).map(instance => instance.handleUpdateDefaultValidator?.());
        }
      });
      if (!isValidate) {
        this.showFailedRow(Array.from(new Set(failedProp)));
      }
    });
    return isValidate;
  }
  public showFailedRow(failedRows: string[]) {
    const copyFilter = JSON.parse(JSON.stringify(this.filter));
    failedRows.forEach((prop) => {
      if (copyFilter[prop]) {
        copyFilter[prop].checked = true;
        copyFilter[prop].mockChecked = true;
      }
    });
    this.handleColumnUpdate(copyFilter);
  }

  private sortTableData() {
    const copyData: ISetupRow[] = [];
    const uniqueData: ISetupRow[] = [];
    this.table.data.forEach((item) => {
      if (item.errType === 'unique') {
        uniqueData.push(item);
      } else {
        copyData.push(item);
      }
    });
    // 简略的拆分
    const infoList: { ipArr: string[], 'inner_ip': string, id: number }[] = uniqueData.map((item, index) => {
      const splitCode = splitCodeArr.find(splits => (item.inner_ip as string).indexOf(splits) > 0);
      return {
        ipArr: splitCode ? (item.inner_ip as string).split(splitCode) : [item.inner_ip],
        inner_ip: item.inner_ip,
        id: index,
      };
    });
    infoList.sort((a, b) => a.ipArr.length - b.ipArr.length); // 多ip靠后
    let copyUniqueData: ISetupRow[] = [];
    const usedIndex: number[] = [];
    if (infoList.length && infoList[0].ipArr.length < 2) {
      infoList.forEach((item, index) => {
        if (!index || !usedIndex.includes(item.id)) {
          copyUniqueData.push(uniqueData[item.id]);
          usedIndex.push(item.id);
          // 找到后续冲突的项
          infoList.slice(index, infoList.length).forEach((row) => {
            if (row.ipArr.find(ip => item.inner_ip.includes(ip)) && !usedIndex.includes(row.id)) {
              copyUniqueData.push(uniqueData[row.id]);
              usedIndex.push(row.id);
            }
          });
        }
      });
    } else {
      copyUniqueData = [...uniqueData];
    }
    copyData.sort((first, second) => {
      // 优先级：Proxy过期或未安装 > 数据校验逻辑
      if (first.proxyStatus || second.proxyStatus) {
        return Number(Boolean(second.proxyStatus)) - Number(Boolean(first.proxyStatus));
      }
      return Number(Boolean(first.isRowValidate)) - Number(Boolean(second.isRowValidate));
    });
    this.table.data.splice(0, this.table.data.length, ...copyUniqueData.concat(copyData));
    this.$nextTick().then(() => {
      this.tableBody && this.tableBody.scrollTo(0, 0);
      // if (this.virtualScroll) {
      //     this.$refs.verify.map(instance => instance.handleUpdateDefaultValidator())
      // }
    });
  }
  /**
   * 获取表格数据
   */
  private getTableData() {
    return this.table.data;
  }
  /**
   * 获取过滤后的数据
   */
  private getData() {
    const resultData: ISetupRow[] = [];
    const tableData = this.getTableData();
    tableData.forEach((row) => {
      const formatItem: { [key: string]: any } = {};
      let splittedDeep = 0;
      const splittedProps: string[] = []; // 拆分过的prop
      const splitValueMap: { [key: string]: string[] } = {};
      this.table.config.filter(col => col.prop && col.prop !== 'prove').forEach((col) => {
        const prop = col.prop as keyof ISetupRow;
        const { splitCode = [] } = col;
        // 多个拆分为数组 - 能走到此步骤证明校验通过，不一一对应的情况需从表单校验处修改处理
        if (splitCode.length && row[prop]) {
          splitValueMap[prop] = this.getSplitValues(row[prop] as string, splitCode);
          splittedDeep = splitValueMap[prop].length;
          splittedProps.push(prop);
        } else {
          // if (col.required || !isEmpty(data[col.prop])) { // 剔除非必填项 - 优化备用（未全面测试）
          //     item[col.prop] = data[col.prop]
          // }
          formatItem[prop] = row[prop]; // 有false的情况，不能默认设置为字符串
          if (prop === 'auth_type') {
            const proveProp = row[prop] as string;
            formatItem[proveProp.toLowerCase()] = row.prove;
          }
        }
        // 处理非表头字段的额外参数
        this.extraParams.forEach((param) => {
          if (!isEmpty(row[param as keyof ISetupRow])) {
            formatItem[param] = row[param as keyof ISetupRow];
          }
        });
      });
      let rows = [formatItem];
      if (splittedDeep && splittedProps.length) {
        rows = new Array(splittedDeep).fill('x')
          .map((p: string, index: number) => ({
            ...formatItem,
            ...splittedProps.reduce((obj: Dictionary, key) => {
              obj[key] = splitValueMap[key][index] || '';
              return obj;
            }, {}),
          }));
      }

      resultData.push(...rows as ISetupRow[]);
    });
    return resultData;
  }

  private getSplitValues(val: string, splitCodeArr: string[]) {
    if (splitCodeArr?.length && val) {
      const splitCode = splitCodeArr.find((splitCode: string) => val.indexOf(splitCode) > 0);
      return this.handleTrimArray(val.split(splitCode as string)) || [];
    }
    return [];
  }
  /**
   * 批量编辑确定事件
   */
  private handleBatchConfirm(arg: any[], config: ISetupHead) {
    if (!arg || !arg.length) return;
    const [{ value, fileInfo, focusRow = {} }] = arg;
    const { type, prop } = config;
    if (prop === 'port' && isEmpty(value)) {
      this.table.data.forEach((row, index) => {
        if (!focusRow.os_type || (focusRow.os_type && row.os_type === focusRow.os_type)) {
          this.$set(this.table.data[index], prop, getDefaultConfig(row.os_type as string, prop));
        }
      });
    } else {
      if ((isEmpty(value) && type !== 'switcher') && (isEmpty(fileInfo) || !fileInfo.value)) return;
      this.table.data.forEach((row, index) => {
        const isReadOnly = config.getReadonly?.call(this, row) || config.readonly;
        const isFileType = config.getCurrentType && config.getCurrentType(row) === 'file';
        const isWindowsKey = config.prop === 'auth_type'
                            && value === 'KEY'
                            && row.os_type === 'WINDOWS'; // Windows不支持密钥
        if (isReadOnly || isWindowsKey) return;

        if (fileInfo && isFileType) {
          this.$set(this.table.data[index], config.prop, fileInfo.value);
          this.$set(this.table.data[index], 'fileInfo', fileInfo);
        } else if (!isEmpty(value)) {
          if (type === 'select') {
            const option = this.getCellInputOptions(this.table.data[index], config);
            this.$set(this.table.data[index], config.prop, option.find(item => item.id === value) ? value : '');
          } else {
            this.$set(this.table.data[index], config.prop, value);
          }
        } else if (isEmpty(value) && type === 'switcher') {
          this.$set(this.table.data[index], config.prop, !!value);
        }
        if (typeof config.handleValueChange === 'function') {
          // 触发联动属性（如：Windows操作系统变更后，端口默认变更）
          config.handleValueChange.call(this, row);
        }
        // if (config.prop === 'os_type' && value === 'WINDOWS') {
        //     this.$set(this.table.data[index], 'port', 445)
        // }
      });
    }
    this.$forceUpdate(); // 强制重新渲染提前，防止 inputInstance 为null的情况出现
    this.$nextTick(() => {
      Object.keys(this.$refs).forEach((refKey) => {
        if (refKey.includes('verify_')) {
          (this.$refs[refKey] as any[]).forEach((instance) => {
            if (instance && instance.$attrs.prop === config.prop) {
              instance.handleValidate();
            }
          });
        }
      });
    });
  }
  private getDefaultValidator(row: ISetupRow | any, config: ISetupHead) {
    return {
      show: row.validator[config.prop] ? row.validator[config.prop].show : false,
      message: row.validator[config.prop] ? row.validator[config.prop].message : '',
      errTag: config.errTag,
    };
  }
  private setValidator(row: ISetupRow | any, prop: string, validator: Dictionary) {
    this.$set(row.validator, prop, validator);
  }
  private handleUpdateData(data: ISetupRow[]) {
    this.$set(this.table, 'data', data);
  }
  /**
   * 跳转Proxy
   */
  private handleGotoProxy(row: ISetupRow) {
    let routeData = null;
    switch (row.proxyStatus) {
      case 'no_proxy':
        routeData = this.$router.resolve({
          name: 'setupCloudManager',
          params: {
            type: 'create',
            title: window.i18n.t('nav_安装Proxy'),
            id: row.bk_cloud_id,
          },
        });
        window.open(routeData.href, '_blank');
        break;
      case 'overdue':
        routeData = this.$router.resolve({
          name: 'cloudManagerDetail',
          params: {
            id: row.bk_cloud_id,
          },
        });
        window.open(routeData.href, '_blank');
        break;
    }
  }
  /**
   * 初始化表头设置
   */
  private initCustomColStatus() {
    // 初始化filter
    const filter = this.table.config.reduce((obj: IFilterRow, item) => {
      if (item.type !== 'operate') {
        obj[item.prop] = {
          checked: item.required || item.show || false,
          disabled: item.required || item.show || false,
          mockChecked: item.required || item.show || false,
          name: this.$t(item.label) as string,
          id: item.prop,
        };
      }
      return obj;
    }, {});
    this.$set(this, 'filter', filter);
    const data: IFilterRow = this.handleGetStorage();
    if (data && Object.keys(data).length) {
      Object.keys(this.filter).forEach((key) => {
        // 防止安装方式切换影响
        if (Object.prototype.hasOwnProperty.call(data, key)) {
          this.filter[key].mockChecked = !!data[key];
          this.filter[key].checked = !!data[key];
        }
      });
    }
    this.initTableHead();
  }
  public initTableHead() {
    if (this.colSetting || this.localMark) {
      let tableHead = this.table.config.filter(item => item.type === 'operate' || this.filter[item.prop]?.mockChecked);
      if (this.setupInfo.header?.length) {
        const tableParentHead = this.setupInfo.parentHead?.map(item => ({
          ...item,
          colspan: tableHead.filter(head => head.parentProp === item.prop).length,
        })) || [];
        this.tableParentHead = tableParentHead.filter(item => !!item.colspan || !item.prop);
      }
      const { clientWidth } = this.$el || {};
      if (clientWidth) {
        const operateCol = tableHead.find(item => item.type === 'operate');
        const widthMap = {
          textarea: 0,
          operate: (operateCol?.width || operateCol?.minWidth || 70) as number, // 操作col定宽70px
        };
        // 两个IP输入框需要尽可能保证宽度
        const textareaLen = tableHead.filter(item => item.type === 'textarea').length;
        let minWidth: number|string = 'auto'; // 最小col 宽度
        if (textareaLen) {
          minWidth = 70;
          const otherLen = tableHead.length - textareaLen - 1;
          const lastWidth = clientWidth - otherLen * minWidth - widthMap.operate;
          if (clientWidth < tableHead.length * minWidth) { // 不能保证最小宽度时，需要缩小最小宽度
            minWidth = (clientWidth - widthMap.operate) / (tableHead.length - 1);
            widthMap.textarea = minWidth;
          } else if (lastWidth / textareaLen > clientWidth * 0.2) {
            widthMap.textarea = clientWidth * 0.2;
            minWidth = 0; // 使用默认宽度
          } else {
            widthMap.textarea = lastWidth / textareaLen;
          }
        }
        tableHead = tableHead.map(item => ({
          ...item,
          width: widthMap[item.type as 'textarea'|'operate'] || minWidth || item.minWidth || item.width || 'auto',
        }));
      }
      this.tableHead = tableHead.map(item => ({
        ...item,
        parentTip: this.tableParentHead.find(parent => item.parentProp === parent.prop)?.tips || '',
      }));
    }
  }
  /**
   * 字段显示列确认事件
   */
  private handleColumnUpdate(data: IFilterRow) {
    this.filter = data;
    this.initTableHead();
    this.$forceUpdate();
  }
  /**
   * 获取存储信息
   */
  private handleGetStorage() {
    let data = {};
    try {
      data = JSON.parse(window.localStorage.getItem(this.localMark + STORAGE_KEY_COL) || '');
    } catch (_) {
      data = {};
    }
    return data;
  }
  /**
   * 设置面板开关
   */
  private handleToggleSetting(isShow: boolean) {
    bus.$emit('toggleSetting', isShow);
  }
  // 是否显示编辑态
  private handleShowEdit(row: ISetupRow, config: ISetupHead) {
    if (this.getCellDisabled(row, config)) return;
    this.editData.push({
      id: row.id,
      prop: config.prop,
    });
  }
  // 判断当前是否是编辑态
  private editStatus(row: ISetupRow, config: ISetupHead) {
    return !!this.editData.find(item => item.id === row.id && item.prop === config.prop);
  }
  // 获取显示名称
  private getDisplayName(row: ISetupRow | any, config: ISetupHead) {
    const options = this.getCellInputOptions(row, config);
    const data = options.find(item => item.id === row[config.prop]);
    return data ? data.name : row[config.prop];
  }
  private hidePassword(row: ISetupRow | any, config: ISetupHead) {
    return this.getPwdFillEnable(row, config)
      ? passwordFillText
      : new Array(`${row[config.prop]}`.length).fill('*')
        .join('');
  }
  public handleCellFocus(arg: any[], cell: {
    row: ISetupRow
    config: ISetupHead
    rowIndex: number
    colIndex: number
  }) {
    const { row, config, rowIndex } = cell;
    this.$set(this, 'focusRow', row);
    const { prop, requiredPick = [], parentProp, tips } = config;
    requiredPick.forEach((propKey) => {
      (this.$refs[`verify_${rowIndex}_${propKey}`] as any[])?.forEach((instance) => {
        instance.clear?.();
      });
    });
    const parentHeadCell = this.tableParentHead?.find(item => item.prop === parentProp);
    if (tips || parentHeadCell?.tips) {
      const [refs] = this.$refs[`header_${tips ? prop : parentProp}`] as any[];
      if (refs?.tipsShow) {
        setTimeout(() => {
          this.popoverEl = refs;
          this.popoverEl.tipsShow();
        }, 200);
      }
    }
  }
  public handleCellBlur(arg: any[], cell: {
    row: ISetupRow
    config: ISetupHead
    rowIndex: number
    colIndex: number
  }) {
    const { row, config } = cell;
    if (config.handleBlur) {
      config.handleBlur(row, config);
    }
    this.$set(this, 'focusRow', {});
    this.popoverEl && this.popoverEl.tipsHide();
    this.popoverEl = null;
  }
  public handleResize() {
    const { tableBody, scrollPlace } = this;
    if (tableBody && scrollPlace) {
      this.hasScroll = tableBody.clientHeight + 2 < scrollPlace.clientHeight;
    } else {
      this.hasScroll = false;
    }
  }
  public updateRow(fn: Function) {
    this.table.data.forEach(row => fn(row));
  }
};
</script>
