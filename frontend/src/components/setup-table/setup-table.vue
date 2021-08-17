<template>
  <div class="setup">
    <div :class="['setup-header-wrapper', { 'setup-setting': localMark }]">
      <table>
        <colgroup>
          <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
        </colgroup>
        <!-- 表头 -->
        <thead class="setup-header">
          <tr>
            <th v-for="(config, index) in tableHead" :key="index">
              <ColumnSetting
                v-if="localMark && index === tableHead.length - 1"
                class="column-setting"
                filter-head
                :local-mark="localMark"
                :font-setting="false"
                :value="filter"
                @update="handleColumnUpdate">
              </ColumnSetting>
              <table-header
                :ref="`header_${config.prop}`"
                v-else
                v-bind="{
                  tips: config.tips,
                  label: config.label,
                  required: !config.noRequiredMark && config.required,
                  batch: config.batch,
                  isBatchIconShow: !!table.data.length,
                  type: config.type,
                  subTitle: config.subTitle,
                  options: getCellInputOptions({}, config),
                  multiple: !!config.multiple,
                  placeholder: config.placeholder,
                  appendSlot: config.appendSlot
                }"
                @confirm="handleBatchConfirm(arguments, config)">
              </table-header>
            </th>
          </tr>
        </thead>
      </table>
    </div>
    <div
      v-if="table.data.length"
      class="setup-body-wrapper"
      ref="tableBody"
      :style="{ 'height': height }"
      @scroll="rootScroll">
      <div class="virtual-scroll-wrapper" :style="ghostStyle" v-if="virtualScroll"></div>
      <div class="body-content" :class="{ 'virtual-scroll-content': virtualScroll }" ref="content">
        <table>
          <colgroup>
            <col v-for="(item, index) in tableHead" :key="index" :width="item.width ? item.width : 'auto'">
          </colgroup>
          <!-- 表体 -->
          <tbody class="setup-body">
            <tr v-for="row in renderData" :key="row.id">
              <td v-for="(config, index) in tableHead" :key="index">
                <div class="cell-operate" v-if="config.type === 'operate'">
                  <i class="cell-operate-plus nodeman-icon nc-plus" @click="handleAddItem(row.id)" v-if="needPlus"></i>
                  <i
                    class="cell-operate-delete nodeman-icon nc-minus"
                    :disabled="disableDelete"
                    @click="handleDeleteItem(row.id)"></i>
                </div>
                <!-- 验证输入 -->
                <verify-input
                  position="right"
                  :id="row.id"
                  :prop="config.prop"
                  :required="config.required"
                  :rules="config.rules"
                  :icon-offset="config.iconOffset"
                  :default-validator="getDefaultValidator(row, config)"
                  :proxy-status="getCurrentPorxyStatus(row, config)"
                  ref="verify"
                  v-else
                  @jump-proxy="handleGotoProxy(row)">
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
                      <span class="name">{{ getDisplayName(row, config) }}</span>
                      <i class="bk-icon icon-angle-down"></i>
                    </span>
                    <!-- 密码框 -->
                    <span class="ghost-input bk-form-input password"
                          :data-placeholder="row[config.prop] ? '' : config.placeholder"
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
                      <span class="name">{{ row[config.prop] }}</span>
                    </span>
                  </div>
                  <!-- 编辑态 -->
                  <input-type
                    v-else
                    v-model.trim="row[config.prop]"
                    :class="{ ml20: getCellInputType(row, config) === 'switcher' }"
                    v-bind="{
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
                      fileInfo: getCellFileInfo(row, config)
                    }"
                    @focus="handleCellFocus(arguments, config)"
                    @blur="handleCellBlur"
                    @change="handleCellValueChange(row, config)"
                    @upload-change="handleCellUploadChange($event, row)">
                  </input-type>
                </verify-input>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <!--空数据内容区-->
    <section class="setup-empty" v-if="!table.data.length">
      <slot name="empty">
        <i class="table-empty-icon bk-icon icon-empty"></i>
        <span class="table-empty-text">{{ $t('暂无数据') }}</span>
      </slot>
    </section>
  </div>
</template>
<script lang="ts">
import { Component, Vue, Prop, Ref, Emit } from 'vue-property-decorator';
import { MainStore, AgentStore } from '@/store/index';
import { bus } from '@/common/bus';
import ColumnSetting from '@/components/common/column-setting.vue';
import VerifyInput from '@/components/common/verify-input.vue';
import InputType from './input-type.vue';
import { throttle, isEmpty } from '@/common/util';
import TableHeader from './table-header.vue';
import { STORAGE_KEY_COL } from '@/config/storage-key';
import { Context } from 'vm';
import { IFileInfo, ISetupHead, ISetupRow, ITabelFliter } from '@/types';

interface IFilterRow {
  [key: string]: ITabelFliter
}

@Component({
  name: 'setup-table',
  components: {
    ColumnSetting,
    VerifyInput,
    InputType,
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
  }) private readonly setupInfo!: { header: ISetupHead[], data: ISetupRow[] };

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
  // 是否为手动安装，校验和云区域变更时需要此变量
  @Prop({ type: Boolean, default: false }) private readonly isManual!: boolean;
  // 是否开启表头设置
  @Prop({ type: String, default: '' }) private readonly localMark!: string;
  @Prop({ type: Function }) private readonly beforeDelete!: Function;

  @Ref('tableBody') private readonly tableBody!: any;
  @Ref('content') private readonly content!: any;
  @Ref('verify') private readonly verify!: any[];

  //  表格信息
  private table: { data: ISetupRow[], config: ISetupHead[] } = {
    data: [],
    config: [],
  };
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
  private editData: {  id: number, prop: string }[] = [];

  private get fetchPwd() {
    return AgentStore.fetchPwd;
  }
  private get cloudList() {
    return AgentStore.cloudList;
  }
  private get apList() {
    return AgentStore.apList;
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

  private created() {
    this.handleInit();
  }
  private mounted() {
    this.handleScroll();
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
      row[prop] = config.getDefaultValue(row);
    } else {
      row[prop] = isEmpty(row[prop]) && config.default ? config.default : row[prop];
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
      return !!config.getReadonly.call(this, row);
    }
    return !!config.readonly;
  }
  private getCellFileInfo(row: ISetupRow, config: ISetupHead) {
    if (row.fileInfo && row[config.prop as keyof ISetupRow]) {
      return row.fileInfo;
    }
    return null;
  }
  /**
   * 当前cell change事件
   * @param {Object} row 当前行
   * @param {Object} config 当前配置项
   */
  @Emit('change')
  private handleCellValueChange(row: ISetupRow, config: ISetupHead) {
    MainStore.updateEdited(true);
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
  private getCurrentPorxyStatus(row: ISetupRow, config: ISetupHead) {
    if (config.getProxyStatus) {
      return config.getProxyStatus.call(this, row);
    }
    return '';
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
    const { prop } = config;
    const { splitCode } = config;
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
   * 通用方法：配置文件内调用login_ip对应性校验
   */
  private handleValidateEqual(row: ISetupRow | any, config: ISetupHead) {
    if (!row || !config) return;
    const { prop, reprop, splitCode } = config;
    let value = row[prop] || '';
    let reValue = row[reprop as string] || '';
    if (!value && reValue) return;
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
  private handleValidateValue(row: ISetupRow | any, config: ISetupHead) {
    const validator = {
      show: false,
      content: '',
      type: '',
    };
    if (!row || !config) return validator;

    const value = row[config.prop];
    // 密码校验区分手动安装
    if (!config.required && config.prop === 'prove') {
      // 1. 密码过期校验
      if (!row.is_manual && isEmpty(value) && row.re_certification) {
        validator.show = true;
        validator.content = window.i18n.t('认证信息过期');
      }
      return validator;
    }
    // 2. 必填项校验
    if (config.required && isEmpty(value)) {
      validator.show = true;
      validator.content = window.i18n.t('必填项');
      return validator;
    }
    // 3. rules校验
    config.rules && config.rules.some((rule: any) => {
      if (rule.regx && !isEmpty(value)) {
        validator.show = !new RegExp(rule.regx).test(value);
        validator.content = rule.content;
      } else if (typeof rule.validator === 'function' && rule.trigger !== 'blur') {
        const isValidate = rule.validator(value);
        validator.show = !isValidate;
        validator.content = rule.content || '';
      }
      // 存在失败校验就终止
      return validator.show;
    });
    if (validator.show) return validator;

    // 4. 唯一性校验
    if (config.unique && !isEmpty(value)) {
      const unique = this.handleValidateUnique(row, config);
      validator.type = config.prop === 'inner_ip' && !unique ? 'unique' : '';
      validator.show = !unique;
      validator.content = window.i18n.t('冲突校验', { prop: 'IP' });
    }
    return validator;
  }
  /**
   * 外部调用的校验方法
   */
  private validate() {
    const union: { [key: string]: any } = {};
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

        if (!validator.show && config.union && !isEmpty(row[config.union])) {
          // 联合校验
          union[config.prop] = union[config.prop] ? union[config.prop] : [];
          const unionValue = value + row[config.union];
          validator.show = union[config.prop].includes(unionValue);
          validator.content = window.i18n.t('冲突校验', { prop: config.label });
          union[config.prop].push(unionValue);
        }

        this.$set((this.table.data[index] as any).validator, config.prop, validator);
        return !validator.show;
      }).every(val => !!val);

      return row.isRowValidate;
    }).every(isRowValidate => !!isRowValidate);

    this.autoSort && this.sortTableData();
    this.$nextTick().then(() => {
      this.verify.map(instance => instance.handleUpdateDefaultValidator());
    });
    return isValidate;
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
      const splitCode = ['\n', '，', ' ', '、', ','].find(splits => item.inner_ip.indexOf(splits) > 0);
      return {
        ipArr: splitCode ? item.inner_ip.split(splitCode) : [item.inner_ip],
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
    const data = this.getTableData().map((data) => {
      const arr = [];
      const item: { [key: string]: any } = {};
      const split: { length: number, values: string[], prop: string } = {
        length: 0,
        values: [],
        prop: '',
      };
      const loginIpValus: string[] = []; // login_ip无 或者 与inner_Ip数量对应
      this.table.config.filter(col => col.prop && col.prop !== 'prove').forEach((col) => {
        const prop = col.prop as keyof ISetupRow;
        // 一个输入框支持多条 IP 时，需要拆分成多条
        if (col.splitCode && col.splitCode.length && data[prop]) {
          const splitCode = col.splitCode.find((splitCode: string) => (data[prop] as string).indexOf(splitCode) > 0);
          const values = this.handleTrimArray((data[prop] as string).split(splitCode as string)) || [];
          if (col.prop === 'login_ip') {
            loginIpValus.splice(0, 0, ...values);
          } else {
            split.values = values;
            split.length = split.values.length;
            split.prop = col.prop;
          }
        }
        // if (col.required || !isEmpty(data[col.prop])) { // 剔除非必填项 - 优化备用（未全面测试）
        //     item[col.prop] = data[col.prop]
        // }
        item[col.prop] = data[prop];
        if (col.prop === 'auth_type') {
          const proveProp = data[col.prop] as string;
          item[proveProp.toLowerCase()] = data.prove;
        }
      });
      // 处理非表头字段的额外参数
      this.extraParams.forEach((param) => {
        if (!isEmpty(data[param as keyof ISetupRow])) {
          item[param] = data[param as keyof ISetupRow];
        }
      });

      if (split.length && split.prop) {
        const isEqual = split.length === loginIpValus.length;
        split.values.forEach((value, index) => {
          const prop = { [split.prop]: value };
          if (isEqual) {
            prop.login_ip = loginIpValus[index];
          }
          const newItem = JSON.parse(JSON.stringify(Object.assign(item, prop)));
          arr.push(newItem);
        });
      } else {
        arr.push(item);
      }
      return arr;
    });
    console.log(data.flat());
    return data.flat();
  }
  /**
   * 批量编辑确定事件
   */
  private handleBatchConfirm(arg: any[], config: ISetupHead) {
    if (!arg || !arg.length) return;
    const [{ value, fileInfo }] = arg;
    const { type } = config;
    if ((isEmpty(value) && type !== 'switcher') && (isEmpty(fileInfo) || !fileInfo.value)) return;
    this.table.data.forEach((row, index) => {
      const isReadOnly = (config.getReadonly && config.getReadonly(row)) || config.readonly;
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
    this.$forceUpdate(); // 强制重新渲染提前，防止 inputInstance 为null的情况出现
    this.$nextTick(() => {
      this.verify.forEach((instance) => {
        if (instance && instance.$attrs.prop === config.prop) {
          instance.handleValidate();
        }
      });
    });
  }
  private getDefaultValidator(row: ISetupRow | any, config: ISetupHead) {
    return {
      show: row.validator[config.prop] ? row.validator[config.prop].show : false,
      content: row.validator[config.prop] ? row.validator[config.prop].content : '',
      errTag: config.errTag,
    };
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
            title: window.i18n.t('安装Proxy'),
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
    this.tableHead = this.table.config.filter(item => item.type === 'operate' || this.filter[item.prop].mockChecked);
  }
  /**
   * 字段显示列确认事件
   */
  private handleColumnUpdate(data: IFilterRow) {
    this.filter = data;
    this.tableHead = this.table.config.filter(item => item.type === 'operate' || this.filter[item.prop].mockChecked);
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
    const len = (`${row[config.prop]}`).length;
    return new Array(len).fill('*')
      .join('');
  }
  private handleCellFocus(arg: any[], config: ISetupHead) {
    const { prop } = config;
    const [refs] = this.$refs[`header_${prop}`] as any[];
    if (refs?.tipsShow) {
      this.popoverEl = refs;
      this.popoverEl.tipsShow();
    }
  }
  private handleCellBlur() {
    this.popoverEl && this.popoverEl.tipsHide();
    this.popoverEl = null;
  }
}
</script>
<style lang="postcss" scoped>
  @import "@/css/mixins/nodeman.css";

  @define-mixin operate-btn {
    font-size: 18px;
    color: #c4c6cc;
    cursor: pointer;
    &:hover {
      color: #979ba5;
    }
  }
  @define-mixin scroll-content {
    position: absolute;
    left: 0;
    top: 0;
    right: 0;
  }

  .setup {
    table {
      width: 100%;
      table-layout: fixed;
    }
    &-header-wrapper {
      padding: 0 15px;
      border: 1px solid #dcdee5;
      background: #fafbfd;
      .setup-header {
        tr {
          height: 42px;
          color: #313238;
          th {
            padding: 0 5px;
          }
        }
      }
      &.setup-setting {
        tr th:last-child {
          padding: 0;
        }
      }
      .column-setting {
        position: relative;
        >>> .bk-tooltip-ref {
          position: absolute;
          right: -15px;
          border-left: 1px solid #dcdee5;
          &:hover {
            background-color: #f0f1f5;
          }
        }
      }
    }
    &-body-wrapper {
      border: 1px solid #dcdee5;
      border-top: 0;
      background: #fff;
      overflow: auto;
      position: relative;
      .ghost-wrapper {
        width: 100%;
        &.is-disabled {
          background-color: #fafbfd;
          cursor: not-allowed;
          border-color: #dcdee5;
          .ghost-input {
            background-color: #fafbfd;
          }
        }
        .ghost-input {
          display: flex;
          align-items: center;
          width: 100%;
          .name {
            height: 32px;
            line-height: 32px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          &::before {
            content: attr(data-placeholder);
            color: #c4c6cc;
            position: relative;
            top: -1px
          }
          &.select {
            i {
              position: absolute;
              right: 3px;
              top: 5px;
              color: #979ba5;
              font-size: 22px;
              transition: transform .3s cubic-bezier(.4,0,.2,1);
              pointer-events: none;
            }
          }
          &.speed {
            display: flex;
            justify-content: space-between;
            border: 1px solid #c4c6cc;
            padding-left: 10px;
            .name {
              flex: 1;
              border: 0;
              height: 30px;
              line-height: 30px;
            }
            .speed-unit {
              width: 38px;
              line-height: 30px;
              height: 30px;
              padding: 0 4px;
              border-left: 1px solid #c4c6cc;
            }
          }
          &.password {
            .name {
              height: 26px;
            }
          }
        }
      }
      .body-content {
        padding: 8px 15px;
      }
      .virtual-scroll {
        &-content {
          @mixin scroll-content;
        }
        &-wrapper {
          @mixin scroll-content;
        }
      }
      .setup-body {
        tr {
          height: 44px;
          td {
            padding: 0 5px;
            .cell-operate {
              display: flex;
              &-plus {
                @mixin operate-btn;
              }
              &-delete {
                margin-left: 8px;

                @mixin operate-btn;
                &[disabled] {
                  color: #dcdee5;
                  cursor: not-allowed;
                }
              }
            }
          }
        }
      }
    }
    &-empty {
      border: 1px solid #dcdee5;
      border-top: 0;
      min-height: 200px;
      background: #fff;

      @mixin layout-flex column, center, center;
      &-icon {
        font-size: 65px;
        color: #c3cdd7;
      }
    }
  }
</style>
