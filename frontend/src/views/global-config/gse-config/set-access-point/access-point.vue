<template>
  <div class="gse-config-wrapper" v-bkloading="{ isLoading: loading }">
    <section class="process-wrapper" v-if="!loading">
      <StepHost
        v-if="curStep === 1"
        :point-id="pointId"
        :step-check="stepCheck"
        :is-edit="isEdit"
        @change="checkedChange"
        @step="stepChange">
      </StepHost>
      <StepInfo
        v-if="curStep === 2"
        :point-id="pointId"
        :is-edit="isEdit"
        @step="stepChange">
      </StepInfo>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import { Route } from 'vue-router';
import { MainStore, ConfigStore } from '@/store/index';
import StepHost from './step-host.vue';
import StepInfo from './step-info.vue';
import { isEmpty } from '@/common/util';

@Component({
  name: 'AccessPoint',
  components: {
    StepHost,
    StepInfo,
  },
})

export default class AccessPoint extends Vue {
  @Prop({ type: String, default: '' }) private readonly pointId!: string;

  private curStep = 1;
  private stepCheck = false; // 第一步操作是否成功

  private get detail() {
    return ConfigStore.apDetail;
  }
  private get loading() {
    return ConfigStore.pageLoading;
  }
  private get isEdit() {
    return !isEmpty(this.pointId);
  }

  private async mounted() {
    if (this.isEdit) {
      this.stepCheck = true; // 编辑时默认连通性检测通过
      await ConfigStore.getGseDetail({ pointId: this.pointId });
    } else {
      this.$nextTick(() => {
        ConfigStore.updateLoading(false);
      });
    }
  }
  private beforeRouteLeave(to: Route, from: Route, next: () => void) {
    MainStore.setToggleDefaultContent(); // 带返回的路由背景置为白色
    next();
  }
  private checkedChange(isChecked: boolean) {
    this.stepCheck = !!isChecked;
  }
  private stepChange(stepNum?: number) {
    this.curStep = stepNum || this.curStep + 1;
  }
}
</script>

<style lang="postcss">
    .gse-config-wrapper {
      min-height: calc(100vh - 142px);
      padding: 0 0 40px 0;
      .gse-config-container {
        margin-top: 24px;
      }
    }
</style>
