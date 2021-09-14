<template>
  <div
    :class="['params-config', { 'has-scroll': isScroll }]"
    v-test.policy="'policyParams'"
    v-bkloading="{ isLoading: loading || stepLoading, opacity: 1 }">
    <div class="scroll-content" ref="configContent">
      <bk-collapse v-if="!loading" class="params-config-content" v-model="activeName">
        <bk-collapse-item
          v-for="mainItem in list"
          v-test.policy="'collapseItem'"
          :key="mainItem.id"
          :name="mainItem.name"
          :class="['mb10', { 'item-content-empty': !mainItem.data.length && !mainItem.child.length }]"
          hide-arrow
          content-hidden-type="hidden">

          <!-- collapse title -->
          <i :class="['bk-icon icon-down-shape arrow', { active: activeName.includes(mainItem.name) }]"></i>
          <span class="title ml5">{{ mainItem.support_os_cpu }}</span>
          <span class="version ml5">{{ `(${mainItem.version})` }}</span>
          <div class="operate-btn-group">
            <template v-if="mainItem.data.length || mainItem.child.length">
              <span
                v-if="list.length > 1"
                v-bk-tooltips.top="$t('复用到所有相同表单')"
                class="item-content-btn"
                @click.stop="handleBrush(mainItem)">
                <i class="nodeman-icon nc-brush-fill"></i>
              </span>
              <span
                v-bk-tooltips.top="$t('恢复默认值')"
                class="ml10 item-content-btn"
                @click.stop="handleRestore('form', mainItem)">
                <i class="nodeman-icon nc-withdraw-fill"></i>
              </span>
            </template>
            <i v-else class="bk-icon icon-check-circle-shape check-icon" v-bk-tooltips.right="$t('必填参数完整')"></i>
          </div>

          <!-- collapse-content -->
          <template #content>
            <ExceptionCard v-if="!mainItem.data.length && !mainItem.child.length" :text="$t('没有需要填写的参数')" />

            <bk-form
              v-if="mainItem.data.length"
              :model="mainItem.form"
              :ref="`form${mainItem.name}`"
              :label-width="labelWidth">

              <!-- main-content -->
              <bk-form-item
                v-for="main in mainItem.data"
                :key="main.inputName"
                :label="main.prop"
                :property="main.prop"
                :icon-offset="-25"
                :required="main.required"
                :rules="main.rules">
                <!-- <div class="item-content"> -->
                <div
                  :class="[
                    'item-content',
                    { 'is-focus': activeInput === main.inputName && (isFocus || isClick) }
                  ]">
                  <!-- @mouseleave="handleMouseLeave">
                @mouseenter="handleMouseenter(mainItem, main.prop)" -->
                  <bk-input
                    class="item-content-input"
                    :class="{ 'ml42': main.disabled }"
                    :disabled="main.disabled"
                    v-model.trim="mainItem.form[main.prop]"
                    @input="handleOperate(arguments, mainItem, main, 'change')"
                    @focus="handleOperate(arguments, mainItem, main, 'focus')"
                    @blur="handleOperate(arguments, mainItem, main, 'blur')">
                  </bk-input>
                  <div class="operate-btn-group">
                    <span
                      class="item-content-btn"
                      v-bk-tooltips.top-end="$t('插入系统内置变量')"
                      @mousedown.capture="handleMousedown(...arguments, main.inputName)">
                      <i class="nodeman-icon nc-variable"
                         @click="handleOperate([mainItem.form[main.prop], $event], mainItem, main, 'insert')"></i>
                    </span>
                    <span
                      v-if="!main.disabled && mainItem.form[main.prop]"
                      v-bk-tooltips.top="$t('复用到所有相同表单')"
                      class="item-content-btn ml10"
                      @click="handleBrush(mainItem, main)">
                      <i class="nodeman-icon nc-brush-fill"></i>
                    </span>
                    <span
                      v-bk-tooltips.top="$t('恢复默认值')"
                      class="item-content-btn ml10"
                      v-if="!main.disabled"
                      @click="handleRestore('prop', mainItem, main)">
                      <i class="nodeman-icon nc-withdraw-fill"></i>
                    </span>
                  </div>
                </div>
              </bk-form-item>
            </bk-form>
            <section :class="['bk-form', { mt30: mainItem.data.length }]" v-if="mainItem.child.length">
              <div class="bk-form-item">
                <label class="bk-label" :style="`width: ${labelWidth}px`">
                  <span class="bk-label-text">{{ $t('可选子配置') }}</span>
                </label>
                <div class="bk-form-content" :style="`margin-left: ${labelWidth}px`">
                  <bk-select searchable multiple display-tag show-select-all v-model="mainItem.childActive">
                    <bk-option
                      v-for="option in mainItem.child"
                      :key="option.name"
                      :id="option.name"
                      :name="option.title">
                    </bk-option>
                  </bk-select>
                </div>
              </div>
            </section>

            <!-- child-content -->
            <section v-if="mainItem.child.length">
              <template v-for="child in mainItem.child">
                <div class="mt30" v-if="mainItem.childActive.includes(child.name)" :key="child.inputName">
                  <bk-form
                    :key="child.inputName"
                    :model="child.form"
                    :ref="`form${child.name}`"
                    :label-width="labelWidth">

                    <bk-form-item class="child-config-head" :label="$t('子配置')">
                      <div class="child-config-content">
                        <span class="child-title">{{ child.title}}</span>
                        <i
                          class="nodeman-icon nc-minus child-delete"
                          @click.stop="handleDeleteChild(mainItem, child.name)">
                        </i>
                      </div>
                    </bk-form-item>

                    <bk-form-item
                      v-for="childItem in child.data"
                      :key="`${child.title}_${childItem.prop}`"
                      :label="childItem.prop"
                      :property="childItem.prop"
                      :icon-offset="50"
                      :required="childItem.required"
                      :rules="childItem.rules">
                      <!-- <div class="item-content"> -->
                      <div
                        :class="[
                          'item-content',
                          { 'is-focus': activeInput === childItem.inputName && (isFocus || isClick) }
                        ]">
                        <bk-input
                          class="item-content-input"
                          :class="{ 'ml42': childItem.disabled }"
                          :disabled="childItem.disabled"
                          v-model.trim="child.form[childItem.prop]"
                          @input="handleOperate(arguments, mainItem, childItem, 'change')"
                          @focus="handleOperate(arguments, mainItem, childItem, 'focus')"
                          @blur="handleOperate(arguments, mainItem, childItem, 'blur')">
                        </bk-input>
                        <div class="operate-btn-group">
                          <span
                            class="item-content-btn"
                            @mousedown.capture="handleMousedown(...arguments, childItem.inputName)">
                            <i
                              class="nodeman-icon nc-variable"
                              @click="handleOperate(
                                [child.form[childItem.prop], $event], mainItem, childItem, 'insert'
                              )">
                            </i>
                          </span>
                          <span
                            v-if="!childItem.disabled && child.form[childItem.prop]"
                            v-bk-tooltips.top="$t('复用到所有相同表单')"
                            :class="[
                              'item-content-btn ml10',
                              { 'active': activeInput === childItem.inputName }
                            ]"
                            @click="handleBrush(child, childItem)">
                            <i class="nodeman-icon nc-brush-fill"></i>
                          </span>
                          <span
                            v-bk-tooltips.top="$t('恢复默认值')"
                            class="item-content-btn ml10"
                            v-if="!childItem.disabled"
                            @click="handleRestore('prop', child, childItem)">
                            <i class="nodeman-icon nc-withdraw-fill"></i>
                          </span>
                        </div>
                      </div>
                    </bk-form-item>

                  </bk-form>
                </div>
              </template>
            </section>
          </template>
        </bk-collapse-item>

        <div style="display: none;">
          <VariablePopover
            ref="popoverRef"
            :search="isClick"
            :search-value="searchValue"
            :loading="variableLoading"
            :list="variableList"
            @selected="handlePopoverSelected">
          </VariablePopover>
        </div>
      </bk-collapse>

      <section v-if="!loading" :class="['footer', { 'fixed': isScroll }]">
        <div class="footer-content">
          <bk-button v-test.common="'stepNext'" theme="primary" class="nodeman-primary-btn" @click="handleNextStep">
            {{ $t('下一步') }}
          </bk-button>
          <bk-button class="ml5" v-test.common="'stepPrev'" @click="handleStepChange(step - 1)">
            {{ $t('上一步') }}
          </bk-button>
          <bk-button class="ml5" @click="handleCancel">
            {{ $t('取消') }}
          </bk-button>
          <bk-button class="fr" v-test.common="'formReset'" @click="handleRestore('all')">
            {{ $t('重置') }}
          </bk-button>
        </div>
      </section>
    </div>
  </div>
</template>
<script lang="ts">
import { Vue, Component, Emit, Prop, Ref } from 'vue-property-decorator';
import { PluginStore } from '@/store';
import { IParamsConfig, IParamsData, IPk } from '@/types/plugin/plugin-type';
import { addListener, removeListener } from 'resize-detector';
import { debounce, deepClone } from '@/common/util';
import VariablePopover from './variable-popover.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
import { reguRequired } from '@/common/form-check';

interface IVariables {
  title: string
  default?: any
  type: string
  _required?: boolean,
  items?: Dictionary
}
interface IVariablesRes {
  id: number
  name: string
  version: string
  'is_main': boolean
  creator?: string
  variables: {
    type?: string,
    properties: IVariables
  }
}
interface IVariablesItem {
  key: string
  value: string
  description: string
  setStr: string
}

@Component({
  name: 'params-config',
  components: {
    VariablePopover,
    ExceptionCard,
  },
})
/**
 * 编辑参数： 回填选中系统版本的参数，其它信息保留且不展示
 * 升级：回填同上
 */
export default class ParamsConfig extends Vue {
  @Prop({ type: String, default: '' }) private readonly type!: string;
  @Prop({ type: Number, default: 3 }) private readonly step!: number;
  @Prop({ type: Boolean, default: true }) private readonly stepLoading!: boolean;

  private loading = false;
  private list: IParamsConfig[] = [];
  private activeName: string[] = [];
  private labelWidth = 130;
  private filterOs: string[] = [];
  private configs: IPk[] = [];
  // 底部footer监听
  private isScroll = false;
  private listenResize!: any;
  // 变量下拉列表相关擦拭
  private activeInfo: Dictionary = {};
  private sysIdRecord: string[] = []; // 上一步之后需要重新加载
  // private selectActive = false
  private outTimer: any = null;
  private activeInput = ''; // 确认当前处于激活状态的input
  private isFocus = false;
  private isClick = false;
  private selectType = ''; // 'focus | 'hover'
  private selectSys = ''; // linux | windows ...
  private searchValue = '';
  private variableLoading = false;
  private variableMap: {
    [key: string]: IVariablesItem[]
  } = {};
  private popoverInstance: any = null;

  @Ref('popoverRef') private readonly popoverRef!: any;
  @Ref('configContent') private readonly configContent!: any;

  private get lastItemIsExpand() {
    const item = this.list[this.list.length - 1];
    return item ? this.activeName.includes(item.name as string) : false;
  }
  private get variableList() {
    const list = this.selectSys ? this.variableMap[this.selectSys] : [];
    if (!list.length || !this.searchValue) {
      return list;
    }
    return list.filter(item => item.setStr.includes(this.searchValue));
  }

  private mounted() {
    this.listenResize = debounce(300, () => this.handleResize());
  }
  private beforeDestroy() {
    removeListener(this.configContent, this.listenResize);
  }

  // 初始化操作系统列表
  private initStep() {
    const copyConfigs: IPk[] = JSON.parse(JSON.stringify(PluginStore.strategyData.configs || []));
    if (this.sysIdRecord.length) { // 判断是否跟之前的数据全部相等
      const sysIdList = copyConfigs.map(item => `${item.id}`);
      if (sysIdList.length === this.sysIdRecord.length && sysIdList.every(item => this.sysIdRecord.includes(item))) {
        this.handleUpdateStepLoaded({ step: this.step, loaded: true });
        return;
      }
    }
    this.configs.splice(0, this.configs.length, ...deepClone(copyConfigs));
    this.list = copyConfigs.map((item: any) => {
      // const childList: IPkConfigTemplate[] = item.config_templates
      //   ? item.config_templates.filter((item: IPkConfigTemplate) => !item.is_main) : []
      // const activeName = this.isEdit || this.isUpgrade ? childList.map(item => `${item.id}`) : []
      item.data = [];
      item.form = {};
      item.title = item.support_os_cpu;
      item.name = `${item.id}`;
      item.child = [];
      item.childActive = []; // [...activeName]
      item.defaultActive = []; // activeName
      item.is_main = true;
      return item;
    });
    const osSet = new Set(this.list.map(item => item.os));
    this.filterOs = [...osSet];
    this.activeName = this.list.filter(item => item.data.length || (item.child && item.child.length))
      .map(item => item.name as string);
    this.getVariablesConfig();
    this.getVariableList();
  }

  // 拉取所有变量
  public async getVariableList() {
    this.variableLoading = true;
    const res = await PluginStore.variableList() || {};
    this.variableLoading = false;
    this.filterOs.forEach((key) => {
      res[key] = res[key]?.map((item: IVariablesItem) => ({
        ...item,
        setStr: `${item.key} ${item.description}`,
      })) || [];
    });
    this.variableMap = res;
  }

  // 初始化主配置和子配置，并按操作系统分类 && 回填表单
  private async getVariablesConfig() {
    let idList: number[] = [];
    // 获取所有 选中版本下config_templates字段内的id集合
    this.list.forEach((item) => {
      if (item.config_templates && item.config_templates.length) {
        idList = idList.concat(item.config_templates.map(config => config.id));
      }
    });
    idList = Array.from(new Set(idList));
    if (idList.length) {
      this.loading = true;
      const list = await PluginStore.getConfigVariables({ config_tpl_ids: idList });
      this.loading = false;
      list.forEach((item: IVariablesRes) => {
        const itemList = Object.entries(item.variables.properties || {});
        const form: Dictionary = {};
        let variableList: IParamsData[] = [];
        // 处理表单遍历所需的统一格式 && 回填参数
        itemList.forEach(([key, value]) => {
          form[key] = value.default || '';
          variableList.push({
            prop: key,
            type: value.type === 'number' ? 'number' : 'string', // 强制转为字符串
            // eslint-disable-next-line no-underscore-dangle
            required: item.is_main ? !!value._required : false,
            // eslint-disable-next-line no-underscore-dangle
            rules: item.is_main && !!value._required ? [reguRequired] : [],
            default: value.default || '',
            inputName: `${item.is_main ? '' : item.id}-${key}`,
            ...value,
          });
        });
        this.list.forEach((sysItem: IParamsConfig) => {
          if (sysItem.config_templates && sysItem.config_templates.find((config: any) => item.id === config.id)) {
            const copyForm = Object.assign({}, form);
            const storeParams = PluginStore.strategyData.params || [];
            const supportOsCpu = sysItem.support_os_cpu;
            const params = storeParams.find(param => `${param.os_type} ${param.cpu_arch}` === supportOsCpu);
            const context: Dictionary = params ? params.context :  {}; // 拿到策略参数的集合
            Object.assign(copyForm, context);
            const currentData = item.is_main ? variableList : sysItem.data; // 主配置参数无默认值问题
            currentData.forEach((inputItem) => {
              inputItem.default = context[inputItem.prop] || '';
            });
            // }
            variableList = deepClone(variableList.map(inputItem => ({
              ...inputItem,
              inputName: `${sysItem.name}${item.is_main ? '' : '-'}${inputItem.inputName}`,
            })));
            // 如果是主配置
            if (item.is_main) {
              sysItem.data.splice(0, sysItem.data.length, ...variableList);
              this.$set(sysItem, 'form', Object.assign({}, copyForm)); // 回填
            } else { // 如果是子配置，放入child
              sysItem.child?.push({
                title: item.name,
                version: '',
                name: `${item.id}`,
                is_main: item.is_main,
                form: Object.assign({}, copyForm),
                data: [...variableList],
              });
            }
          }
        });
      });
    }
    this.handleUpdateStepLoaded({ step: this.step, loaded: true });
    this.$nextTick(() => {
      if (this.configContent) {
        addListener(this.configContent, this.listenResize);
      }
    });
  }

  // 回填信息
  public handleResetValue() {

  }

  // 删除子配置
  public handleDeleteChild(item: IParamsConfig, name: string) {
    const index = item.childActive.findIndex(item => item === name);
    if (index > -1) {
      item.childActive.splice(index, 1);
    }
  }

  // 恢复默认值
  public handleRestore(type: 'all' | 'form' | 'prop', item: IParamsConfig, itemChild: IParamsData) {
    if (type === 'prop') {
      item.form[itemChild.prop] = itemChild.default || '';
    } else if (type === 'form') {
      this.formRestore(item);
    } else {
      this.list.forEach(item => this.formRestore(item));
    }
  }
  // 单个form重置
  public formRestore(mainConfig: IParamsConfig) {
    const { childActive, defaultActive } = mainConfig;
    mainConfig.childActive.splice(0, childActive.length, ...defaultActive);
    mainConfig.data.forEach((main) => {
      mainConfig.form[main.prop] = main.default || '';
    });
    mainConfig.child?.forEach((child) => {
      child.data.forEach((item) => {
        child.form[item.prop] = item.default || '';
      });
    });
  }

  // 复制所有相同表单
  public handleBrush(sourceItem: IParamsConfig, data: IParamsData) {
    if (data)  {
      // 目前子配置覆盖功能有争议，老的覆盖功能先保留
      const value = sourceItem.form[data.prop];
      if (value) {
        this.list.forEach((list) => {
          if (Object.prototype.hasOwnProperty.call(list.form, data.prop)) {
            list.form[data.prop] = value;
          }
          if (list.child && list.child.length) {
            list.child.forEach((child) => {
              if (Object.prototype.hasOwnProperty.call(child.form, data.prop)) {
                child.form[data.prop] = value;
              }
            });
          }
        });
      }
    } else { // 按系统复制
      const { id: sourceId, childActive: sourceChildActive, form: sourceForm, child: sourceChild } = sourceItem;
      const childFormMap: Dictionary = {};
      sourceChild?.forEach((childItem) => {
        childFormMap[childItem.name] = childItem.form;
      });
      this.list.forEach((item) => {
        const { id, childActive, form, child } = item;
        if (id !== sourceId) {
          // 主配置填充逻辑
          Object.keys(form).forEach((key) => {
            if (Object.prototype.hasOwnProperty.call(sourceForm, key)) {
              item.form[key] = sourceForm[key];
            }
          });
          // 子配置填充逻辑
          child?.forEach((childItem) => {
            const { name, form } = childItem;
            if (childActive.includes(name) && sourceChildActive.includes(name)) {
              if (sourceChild) {
                const data = sourceChild.find(child => child.name === childItem.name);
                const sourceChildForm = data ? data.form : {};
                Object.keys(form).forEach((key) => {
                  if (Object.prototype.hasOwnProperty.call(sourceChildForm, key)) {
                    childItem.form[key] = sourceChildForm[key];
                  }
                });
              }
            }
          });
        }
      });
    }
  }

  // 检查表单
  public async handleValidateForm() {
    const checkList: Promise<boolean>[] = [];
    this.list.forEach((item: IParamsConfig) => {
      const refs: any = this.$refs[`form${item.name}`];
      if (refs?.length) {
        refs.reduce((list: Promise<boolean>[], ref: any) => {
          list.push(ref.validate());
          return list;
        }, checkList);
      }
      if (item.child && item.child.length) {
        item.child.forEach((child) => {
          if (item.childActive.includes(child.name)) {
            const childRefs: any = this.$refs[`form${child.name}`];
            if (childRefs?.length) {
              childRefs.reduce((list: Promise<boolean>[], childRef: any) => {
                list.push(childRef.validate());
                return list;
              }, checkList);
            }
          }
        });
      }
    });
    return Promise.all(checkList)
      .then(() => false)
      .catch(() => {
        const active = this.list.filter(item => Object.values(item.form).some(value => !value)).map(item => item.name);
        this.activeName = Array.from(new Set((active as string[]).concat(this.activeName)));
        return true;
      });
  }

  // 更新策略的 params 和 configs 属性
  public beforeStepLeave() {
    this.handleValidateForm();
    const formatValue = JSON.parse(JSON.stringify(PluginStore.strategyData.params));
    this.list.forEach((item) => {
      const params: Dictionary = {
        cpu_arch: item.cpu_arch,
        os_type: item.os,
        context: {}, // 主配置、子配置的值都集合到context
      };
      const itemList = Object.entries(item.form);
      itemList.forEach(([key, value]) => {
        params.context[key] = value;
      });
      // 子配置的值非空时 覆盖相同字段的值
      if (item.childActive.length && item.child) {
        item.child.forEach((child) => {
          if (item.childActive.includes(child.name)) {
            Object.keys(child.form).forEach((key) => {
              params.context[key] = child.form[key] || params.context[key] || '';
            });
          }
        });
      }
      const index = formatValue.findIndex((param: any) => `${param.os_type} ${param.cpu_arch}` === item.title);
      if (index < 0) {
        formatValue.push(params);
      } else {
        formatValue.splice(index, 1, params);
      }
    });
    PluginStore.setStateOfStrategy({
      key: 'params',
      value: formatValue,
    });
    const copyStoreConfigs: IPk[] = deepClone(PluginStore.strategyData.configs || []);
    this.configs.forEach((item, index) => {
      if (item.config_templates.length) {
        // 存在的主配置项一定会留在 config_templates 里边
        const tempList = this.list[index].config_templates.filter(item => item.is_main);
        if (this.list[index].childActive.length) {
          this.list[index].childActive.forEach((name) => {
            const childTemp = this.list[index].config_templates.find(temp => `${temp.id}` === name);
            if (childTemp) {
              tempList.push(childTemp);
            }
            item.config_templates.splice(0, item.config_templates.length, ...deepClone(tempList));
          });
        } else {
          item.config_templates.splice(0, item.config_templates.length, ...deepClone(tempList));
        }
      }
      const configIndex = copyStoreConfigs.findIndex(config => item.id === config.id);
      if (configIndex > -1) {
        copyStoreConfigs.splice(configIndex, 1, deepClone(item));
      }
    });
    // 此处更新 configs, 主要更新选中的子配置项 config_templates
    PluginStore.setStateOfStrategy({
      key: 'configs',
      value: copyStoreConfigs,
    });
    const copySysIdRecord = [...this.sysIdRecord];
    this.sysIdRecord = this.list.map(item => `${item.name}`);
    // console.log(`loading: ${this.loading}`, !this.sysIdRecord.every(sys => copySysIdRecord.includes(sys)))
    return this.loading ? false : !this.sysIdRecord.every(sys => copySysIdRecord.includes(sys));
  }

  public handleMousedown(event: Event, inputName: string) {
    if (this.activeInput === inputName) {
      if (event?.preventDefault) {
        event.preventDefault();
      }
      return false;
    }
    this.$nextTick(() => {
      this.activeInput = '';
    });
  }
  public handleOperate(
    [value, event]: any[],
    mainItem: IParamsConfig,
    itemChild: IParamsData,
    type: 'change' | 'focus' | 'blur' | 'insert',
  ) {
    const valueTrim = value.replace(/\s+/g, '');
    this.selectSys = mainItem.os;
    this.$set(this, 'activeInfo', itemChild);

    this.activeInput = itemChild.inputName as string;

    if (type === 'focus' || type === 'change') {
      if (type === 'change') {
        this.$store.commit('updateEdited', true);
        this.handleUpdateReload({ step: this.step + 1, needReload: false });
      }
      if (!this.isFocus) {
        this.popoverInstance && this.popoverInstance.destroy();
        this.popoverInstance = null;
      }
      this.isFocus = true;
      if (/^(\{\{)((?!\}\}).)*$/.test(valueTrim)) {
        this.searchValue = valueTrim.replace(/\{+/g, '');
        // 备用方案 - 解决onHidden使用了setTimeout产生的问题。
        if (!this.popoverInstance) {
          setTimeout(() => {
            this.showPopover(event, 'focus');
          }, 200);
        }
      } else {
        this.popoverInstance && this.popoverInstance.destroy();
      }
    } else if (type === 'insert') {
      this.popoverInstance && this.popoverInstance.destroy();
      this.popoverInstance = null;
      this.isClick = true;
      this.isFocus = false;
      this.showPopover(event, 'click');
    }
  }
  // 下拉赋值
  public handlePopoverSelected(variableItem: IVariablesItem) {
    const { inputName, prop } = this.activeInfo;
    this.list.forEach((mainItem) => {
      const main = mainItem.data?.find(item => item.inputName === inputName);
      if (main) {
        mainItem.form[prop] = variableItem.key;
        return;
      }
      if (mainItem.child?.length) {
        mainItem.child.forEach((child) => {
          const childItem = child.data?.find(item => item.inputName === inputName);
          if (childItem) {
            child.form[prop] = variableItem.key;
            return;
          }
        });
      }
    });
    this.destroyPopover();
  }
  public showPopover(e: Event, type: 'focus' | 'click') {
    this.popoverInstance && this.popoverInstance.destroy();
    this.popoverInstance = null;
    const offset = type === 'click' ? '70, 0' : '0, 0';

    this.popoverInstance = this.$bkPopover(e.target as EventTarget, {
      content: this.popoverRef.$el,
      trigger: 'manual',
      arrow: false,
      theme: 'light menu',
      maxWidth: 400,
      offset,
      sticky: true,
      interactive: true,
      boundary: 'window',
      placement: type === 'focus' ? 'bottom-start' : 'bottom-end',
      onHidden: () => {
        this.destroyPopover();
      },
    });
    this.popoverInstance && this.popoverInstance.show();
  }
  private destroyPopover() {
    this.popoverInstance && this.popoverInstance.destroy();
    this.popoverInstance = null;
    // this.selectSys = ''
    this.isFocus = false;
    this.isClick = false;
    this.searchValue = '';
  }
  // 底部footer浮动
  public handleResize() {
    this.isScroll = this.configContent
      ? this.configContent.scrollHeight > this.$root.$el.clientHeight - 52 - 102 : false;
  }
  public handleNextStep() {
    this.handleValidateForm().then(() => {
      this.handleStepChange(this.step + 1);
    });
  }

  @Emit('step-change')
  public handleStepChange(step: number) {
    return step;
  }
  @Emit('cancel')
  public handleCancel() {}
  @Emit('update-reload')
  public handleUpdateReload({ step, needReload }: { step: number, needReload?: boolean }) {
    return { step, needReload };
  }
  @Emit('update-loaded')
  public handleUpdateStepLoaded({ step, loaded }: { step: number, loaded?: boolean }) {
    return { step, loaded };
  }
}
</script>
<style lang="postcss" scoped>
.operate-btn-group {
  position: absolute;
  top: 8px;
  right: 14px;
  display: inline-flex;
  line-height: 1;
}
>>> .bk-collapse-item {
  width: 100%;
  &-header {
    position: relative;
    border: 1px solid #f0f1f5;
    border-radius: 2px;
    background: #f0f1f5;
    .bk-icon {
      font-size: 14px;
      position: relative;
      top: -1px;
    }
    .operate-btn-group {
      top: 13px;
    }
  }
  &-content {
    padding: 20px 0 30px 0;
  }
  & + .footer {
    margin-top: 20px;
  }
  &.bk-collapse-item-active  + .footer {
    margin-top: 0;
  }
  &.item-content-empty {
    .bk-collapse-item-content {
      padding-top: 0;
    }
    .bk-exception-card {
      margin-top: -1px;
    }
  }
}
.params-config {
  position: relative;
  height: 100%;
  overflow: hidden;
  .scroll-content {
    height: 100%;
    padding-bottom: 24px;
    overflow: auto;
  }
  &.has-scroll {
    .scroll-content {
      padding-bottom: 36px;
    }
    .footer {
      position: absolute;
      right: 0;
      bottom: 0;
      width: 100%;
      border-top: 1px solid #dcdee5;
      background: #fff;
    }
  }
  &-content {
    position: relative;
    padding: 30px 25px 20px 25px;
    width: 730px;
  }
  .footer {
    .footer-content {
      padding: 10px 0 10px 24px;
      width: 705px;
    }
  }
}
.arrow {
  transition: transform .2s ease-in-out;
  transform: rotate(-90deg);
  color: #63656e;
  display: inline-block;
  &.active {
    transform: rotate(0deg);
  }
}
.title {
  color: #63656e;
  font-size: 14px;
  font-weight: 700;
}
.check-icon {
  font-size: 16px;
  color: #4bc7ad;
}
.version {
  color: #979ba5;
  font-size: 12px;
  font-weight: 700;
}
.child-config-head {
  color: #63656e;
  >>> .bk-label,
  >>> .bk-form-content {
    height: 19px;
    line-height: 19px;
    min-height: auto;
  }
  >>> .bk-label-text {
    position: relative;
    font-weight: 700;
    &::before {
      position: absolute;
      display: inline-block;
      content: "";
      top: 3px;
      left: -13px;
      height: 13px;
      width: 3px;
      background: #dcdee5;
    }
  }
  .child-config-content {
    display: flex;
    align-items: center;
    .child-title {
      font-weight: 700;
    }
    .child-delete {
      margin-left: 10px;
      color: #c4c6cc;
      &:hover {
        color: #3a84ff;
        cursor: pointer;
      }
    }
  }
}
.item-content {
  display: flex;
  .operate-btn-group {
    display: none;
  }
  &.is-focus,
  &:hover {
    .operate-btn-group {
      display: inline-flex;
    }
  }
  .ml42 {
    margin-right: 42px;
  }
  &-input {
    flex: 1;
    .bk-input-text {
      padding-right: 100px;
    }
  }
  &-btn {
    width: 16px;
    height: 16px;
    font-size: 14px;
    cursor: pointer;
    color: #979ba5;
    &:hover {
      color: #3a84ff;
    }
  }
}
</style>
