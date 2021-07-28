<template>
  <div class="agent-version">
    <bk-form :label-width="100" ref="form">
      <bk-form-item :label="$t('MD5')" required>
        <bk-input class="content-basic" :placeholder="$t('请输入')"></bk-input>
      </bk-form-item>
      <bk-form-item :label="$t('版本包')" required>
        <Upload class="content-basic" :on-upload-error="handleOnUploadError"></Upload>
      </bk-form-item>
    </bk-form>
    <bk-button
      :style="{ marginLeft: `${marginLeft}px` }"
      theme="primary"
      class="nodeman-primary-btn mt30"
      :disabled="disabledUploadBtn"
      @click="handleNext">
      {{ $t('下一步') }}
    </bk-button>
  </div>
</template>
<script lang="ts">
import { Component, Ref, Mixins } from 'vue-property-decorator';

import Upload from '@/components/common/upload.vue';
import formLabelMixin from '@/common/form-label-mixin';

@Component({
  name: 'agent-version-upload',
  components: {
    Upload,
  },
})
export default class AgentVersionUpload extends Mixins(formLabelMixin) {// 上传按钮禁用状态
  private disabledUploadBtn = true;
  private isUploading = false;
  private dynamicSlotName = 'default';
  private file: File | null = null;
  private marginLeft = 100;
  @Ref('form') private readonly form!: any;

  private mounted() {
    this.marginLeft = this.initLabelWidth(this.form) as number;
  }

  public handleOnUploadError(res: any, file: File) {
    this.disabledUploadBtn = false;
    this.file = file;
  }
  public handleNext() {
    this.$router.push({
      name: 'agentVersionDetail',
      params: {
        name: this.file?.name || '',
      },
    });
  }
}
</script>
<style lang="postcss" scoped>
.agent-version {
  .content-basic {
    width: 480px;
  }
}
</style>
