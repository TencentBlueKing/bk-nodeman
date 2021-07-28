<template>
  <!-- 监控后台服务弹窗 -->
  <bk-dialog
    header-position="left"
    width="800"
    :title="dialogTitle"
    :show-footer="false"
    :value="visible"
    @cancel="closeDialog">
    <section class="dialog-content">
      <section v-if="mode === 'saas'">
        <bk-big-tree class="dialog-tree" :data="saasData" default-expand-all>
          <span class="custom-tree-node" slot-scope="{ node, data }">
            <i class="bk-icon-loading" v-if="data.loading"></i>
            <span :class="data.class">{{ node.name }}</span>
            <bk-popover placement="top" :tippy-options="{ boundary: 'window' }">
              <i class="nodeman-icon nc-tips-fill ml10"></i>
              <div slot="content" class="popover-slot-content">
                <p>{{ $t('接口描述：') }} {{ data.description }}</p>
                <p>{{ $t('测试参数：') }} {{ data.args }}</p>
                <p>{{ $t('测试结果：') }} {{ data.result }}</p>
                <p v-if="data.class === 'class-error'"> {{ $t('出错信息：') }} {{ data.message }}</p>
              </div>
            </bk-popover>
          </span>
        </bk-big-tree>
      </section>
      <div class="dialog-detail" v-else>
        <p class="dialog-detail-title mb10"> {{ dialogStatus }} {{ dialogMessage }} </p>
        <div v-for="(item,index) in tips.solution" v-show="tips.status > 1" :key="index">
          <bk-collapse
            class="dialog-collapse"
            accordion
            v-model="activeName"
            v-show="tips.status > 1">
            <bk-collapse-item :name="item.reason">
              <div class="collapse-title">
                <bk-tag size="small" theme="danger">{{ possibleSolutionText }}{{ index + 1 }}</bk-tag>
                <span>{{ item.reason }}</span>
              </div>
              <div slot="content" class="collapse-content pb10">
                <bk-tag size="small" theme="info">{{ errorSolutionText }}{{ index + 1 }}</bk-tag>
                {{ item.solution }}
              </div>
            </bk-collapse-item>
          </bk-collapse>
        </div>
      </div>
    </section>
  </bk-dialog>
</template>
<script lang="ts">
import { Vue, Component, Prop, Emit, Watch } from 'vue-property-decorator';

@Component({ name: 'HealthzDialog' })
export default class HealthzDialog extends Vue {
  @Prop({ type: Object, default: () => ({}) }) private readonly dialog!: Dictionary;
  @Prop({ type: String, default: 'saas' }) private readonly mode!: string;
  @Prop({ type: Boolean, default: false }) private readonly visible!: boolean;

  private activeName = '';
  private possibleSolutionText = this.$t('可能原因');
  private errorSolutionText = this.$t('解决方案');
  private tips: Dictionary = {};

  private saasData: Dictionary[] = []; // 要测试的接口数据

  private get dialogStatus() {
    if (this.tips.status === 0) {
      return this.$t('正常');
    } if (this.tips.status === 1) {
      return this.$t('关注');
    } if (this.tips.status > 1) {
      return this.$t('异常');
    }
    return this.$t('未知');
  }
  // 弹窗的描述
  private get dialogTitle() {
    if (this.tips.description && this.dialogStatus) return this.tips.description + this.dialogStatus;
    return '';
  }
  // 弹窗的信息
  private get dialogMessage() {
    return this.tips.message;
  }

  @Watch('visible')
  public handleVisibleChange(value: boolean) {
    if (!!value) {
      this.tips = this.dialog;
      if (this.mode === 'saas') {
        this.loadSaasDataToTest();
      }
    }
  }

  @Emit('closed')
  public closeDialog() {
    return false;
  }

  // 通过全局的数据分离得到当前组件的数据
  public loadSaasDataToTest() {
    const data: Dictionary[] = [];
    const { api_list: apiList = [] } = this.dialog;
    if (!!apiList.length) {
      apiList.forEach((item: Dictionary) => {
        const tmpChildren: Dictionary[] = [];
        const { children_api_list: childrenApiList = [] } = item;
        if (!!childrenApiList.length) {
          childrenApiList.forEach((child: Dictionary) => {
            tmpChildren.push({
              id: child.api_name,
              name: child.api_name,
              description: child.description,
              loading: false,
              class: '',
              message: '',
              result: {},
              args: child.args,
            });
          });
        }
        if (item.api_name) {
          data.push({
            id: item.api_name,
            name: item.api_name,
            children: tmpChildren,
            folder: !!tmpChildren.length,
            description: item.description,
            loading: false,
            class: '',
            message: '',
            result: {},
            args: item.args,
          });
        }
      });
    }
    this.saasData.splice(0, this.saasData.length, ...data);
  }
}
</script>
<style scoped lang="postcss">
    .dialog-content {
      min-height: 260px;
      max-height: 400px;
      overflow: auto;
    }
    .dialog-detail {
      color: #63656e;
    }
    .dialog-detail-title {
      line-height: 20px;
    }
    .dialog-collapse {
      border-top: 1px solid #ebeef5;
      border-bottom: 1px solid #ebeef5;
    }
    .collapse-title,
    .collapse-content {
      color: #63656e;
    }
    >>> .dialog-tree .clearfix::after {
      content: "";
    }
    .popover-slot-content {
      max-width: 800px;
      max-height: 500px;
      overflow: auto;
    }
</style>
