<template>
  <article class="add-cloud" v-bkloading="{ isLoading: loading }" v-test.cloudInfo="'cloudInfo'">
    <!--提示-->
    <section class="add-cloud-tips mb20">
      <tips :list="tipsList"></tips>
    </section>
    <!--表单-->
    <section class="add-cloud-form">
      <bk-form :label-width="116" :model="formData" :rules="rules" ref="form" v-test.cloudInfo="'cloudForm'">
        <bk-form-item error-display-type="normal" :label="$t('云区域名称')" property="bkCloudName" required>
          <bk-input
            v-test.cloudInfo="'cloudName'"
            class="content-basic"
            :placeholder="$t('请输入')"
            v-model="formData.bkCloudName" />
        </bk-form-item>
        <bk-form-item error-display-type="normal" :label="$t('云服务商')" property="isp" required>
          <bk-select
            v-test.cloudInfo="'cloudIsp'"
            class="content-basic"
            :placeholder="$t('请选择')"
            v-model="formData.isp"
            :clearable="false">
            <bk-option
              v-for="option in ispList"
              :key="option.isp"
              :id="option.isp"
              :name="option.isp_name">
              <img :src="`data:image/svg+xml;base64,${option.isp_icon}`" class="option-icon mr5" v-if="option.isp_icon">
              <span>{{ option.isp_name }}</span>
            </bk-option>
          </bk-select>
        </bk-form-item>
        <bk-form-item
          error-display-type="normal"
          :ext-cls="apList.length > 1 ? 'content-access' : ''"
          :label="$t('选择接入点')"
          required>
          <div class="bk-button-group">
            <bk-button
              v-for="item in apList"
              :key="item.id"
              v-test.cloudInfo="`cloudAp.${item.id}`"
              @click="handleChangeAp(item)"
              :class="{ 'is-selected': item.id === formData.apId }">
              {{ item.name }}
            </bk-button>
          </div>
        </bk-form-item>
      </bk-form>
    </section>
    <!--操作按钮-->
    <section class="add-cloud-footer">
      <bk-button
        theme="primary"
        :style="{ marginLeft: `${marginLeft}px` }"
        ext-cls="nodeman-primary-btn"
        :loading="loadingSubmitBtn"
        @click="handleSubmit">
        {{ submitBtnText }}
      </bk-button>
      <bk-button class="nodeman-cancel-btn ml5" @click="handleCancel">{{ $t('取消') }}</bk-button>
    </section>
    <bk-dialog
      :value="dialog.show"
      theme="primary"
      width="400"
      :mask-close="false"
      :show-footer="false"
      @cancel="handleCancel">
      <div class="bk-info-box">
        <div class="dialog-create-icon">
          <i class="bk-icon  icon-check-1"></i>
        </div>
        <div class="bk-dialog-type-header has-sub-header">
          <div class="header">{{ $t('云区域创建成功') }}</div>
          <div class="desc mt10">
            <p>{{ $t('仍需安装Proxy才能够正常使用') }}</p>
          </div>
        </div>
        <div class="footer-wrapper">
          <auth-component
            tag="div"
            :authorized="!!proxyOperateList.length"
            :apply-info="[{ action: 'proxy_operate' }]">
            <template slot-scope="{ disabled }">
              <bk-button theme="primary" :disabled="disabled" @click="setupProxy">{{ $t('安装Proxy') }}</bk-button>
            </template>
          </auth-component>
          <bk-button class="ml10" @click="handleCancel">{{ $t('稍后安装') }}</bk-button>
        </div>
      </div>
    </bk-dialog>
  </article>
</template>
<script lang="ts">
import { Component, Prop, Watch, Ref } from 'vue-property-decorator';
import { MainStore, CloudStore } from '@/store/index';
import Tips from '@/components/common/tips.vue';
import formLabelMixin from '@/common/form-label-mixin';
import { ICloudSource } from '@/types/cloud/cloud';
import { IAp } from '@/types/config/config';
import { reguFnName, reguRequired } from '@/common/form-check';

@Component({
  name: 'cloud-manager-add',
  components: {
    Tips,
  },
})

export default class CloudManagerAdd extends formLabelMixin {
  @Prop({ type: [Number, String], default: 0 }) private readonly id!: string | number;
  // 操作类型 编辑 or 新增
  @Prop({
    type: String,
    default: 'add',
    validator(v) {
      return ['add', 'edit'].includes(v);
    },
  }) private readonly type!: string;
  @Ref('form') private readonly formRef!: any;

  private tipsList = [
    this.$t('云区域管理提示一'),
  ];
  // 表单数据
  private formData: {
    bkCloudName:  string
    isp: string
    apId: null | number
  } = {
    bkCloudName: '',
    isp: '',
    apId: null,
  };
  // 表单校验
  private rules = {
    bkCloudName: [reguRequired, reguFnName()],
    isp: [reguRequired],
  };
  private loading = false;
  // 是否显示下一步加载效果
  private loadingSubmitBtn = false;
  private apList: IAp[] = [];
  private marginLeft = 116;
  private dialog: Dictionary = {
    show: false,
    bk_cloud_id: null,
  };

  private get ispList() {
    return MainStore.ispList;
  }
  private get defaultAp() {
    return this.apList.length === 1 ? this.apList[0] : { id: -1, name: this.$t('自动选择接入点') };
  }
  private get submitBtnText(): string {
    const textMap: Dictionary = {
      add: this.$t('提交'),
      edit: this.$t('保存'),
    };

    return textMap[this.type];
  }
  private get proxyOperateList() {
    return CloudStore.authority.proxy_operate || [];
  }

  @Watch('id', { immediate: true })
  public handleIdChange() {
    this.handleInit();
  }

  private mounted() {
    this.marginLeft = this.initLabelWidth(this.formRef) || 0;
  }
  private async handleInit() {
    this.initFormData();
    const promiseList = [];
    promiseList.push(this.handleGetApList());
    if (!this.ispList.length) {
      promiseList.push(MainStore.getIspList());
    }
    if (this.id) {
      MainStore.setNavTitle(window.i18n.t('编辑云区域'));
      promiseList.push(this.handleGetCloudDetail());
    }
    this.loading = true;
    await Promise.all(promiseList);
    this.loading = false;
    // 接入点为-1或者不存在就取默认第一个接入点
    if (this.apList.length && (this.formData.apId === -1 || !this.formData.apId)) {
      this.formData.apId = this.apList[0].id;
    }
  }
  /**
   * 获取云区域详情
   */
  private async handleGetCloudDetail() {
    const form = await CloudStore.getCloudDetail(`${this.id}`);
    this.$set(this, 'formData', Object.assign(this.formData, form));
  }
  /**
   * 获取接入点信息
   */
  private async handleGetApList() {
    this.apList = await CloudStore.getApList();
  }
  /**
   * 初始化表单
   */
  private initFormData() {
    this.formData = {
      bkCloudName: '',
      isp: '',
      apId: null,
    };
  }
  /**
   * 接入点选择事件
   * @param {Object} item
   */
  private handleChangeAp(item: IAp) {
    this.formData.apId = item.id;
  }
  /**
   * 提交
   */
  private handleSubmit() {
    this.formRef.validate().then(async () => {
      this.loadingSubmitBtn = true;
      let data = null;
      if (this.type === 'add') {
        data = await this.handleCreateCloud();
      } else {
        data = await this.handleUpdateCloud();
      }
      this.loadingSubmitBtn = false;
      if (!data) return;

      if (this.type === 'add') {
        this.handleCreateSuccess(data);
      } else {
        this.handleEditSuccess();
      }
    });
  }
  /**
   * 编辑成功后处理逻辑
   */
  private handleEditSuccess() {
    this.$bkMessage({ theme: 'success', message: this.$t('编辑成功') });
    this.handleCancel();
  }
  /**
   * 创建成功后处理逻辑
   */
  private handleCreateSuccess(data: ICloudSource) {
    this.dialog.show = true;
    this.dialog.bk_cloud_id = data.bk_cloud_id;
  }
  /**
   * 创建云区域
   */
  private async handleCreateCloud() {
    const data = await CloudStore.createCloud({
      bk_cloud_name: this.formData.bkCloudName,
      isp: this.formData.isp,
      ap_id: this.formData.apId as number,
    });
    return data;
  }
  /**
   * 编辑云区域
   */
  private async handleUpdateCloud() {
    const data = await CloudStore.updateCloud({
      pk: this.id as number,
      params: {
        bk_cloud_name: this.formData.bkCloudName,
        isp: this.formData.isp,
        ap_id: this.formData.apId as number,
      },
    });
    return data;
  }
  /**
   * 取消
   */
  private handleCancel() {
    this.$router.push({ name: 'cloudManager' });
  }
  /**
   * 默认接入点变更
   */
  private handleDefaultApChange(value: number) {
    if (!value && !this.formData.apId && this.apList.length) {
      this.formData.apId = this.apList[0].id;
    }
  }
  private setupProxy() {
    this.dialog.show = false;
    this.$router.replace({
      name: 'setupCloudManager',
      params: {
        id: `${this.dialog.bk_cloud_id || this.id}`,
        type: 'create',
      },
    });
  }
}
</script>
<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

>>> .tooltips-icon {
  /* stylelint-disable-next-line declaration-no-important */
  right: 10px !important;
}
.option-icon {
  height: 20px;
  position: relative;
  top: 5px;
}
.add-cloud-form {
  .content-basic {
    width: 480px;
  }
  .content-access {
    margin-top: 15px;
  }
}
.add-cloud-footer {
  margin-top: 30px;
}
.dialog-create-icon {
  margin: 0 auto 16px;
  width: 42px;
  height: 42px;
  line-height: 42px;
  font-size: 30px;
  color: #3fc06d;
  font-weight: 600;
  text-align: center;
  border-radius: 21px;
  background: #e5f6ea;
}
.header {
  line-height: 32px;
  font-size: 20px;
}
.desc {
  line-height: 22px;
  padding-bottom: 10px;
}
.footer-wrapper {
  text-align: center;
}
.info-dialog-btn {
  text-decoration: none;
  cursor: pointer;
  color: #3a84ff;
  &[disabled] {
    color: #c4c6cc;
  }
}
</style>
