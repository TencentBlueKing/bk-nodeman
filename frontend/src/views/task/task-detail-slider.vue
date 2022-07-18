<template>
  <bk-sideslider
    ext-cls="commands-slider"
    transfer
    quick-close
    :width="620"
    :is-show="show"
    :title="$t('手动操作sliderTitle', [slider.opType, slider.row.innerIp])"
    :before-close="handleHidden">
    <div slot="content" class="commands-wrapper" v-bkloading="{ isLoading: commandLoading }">
      <!-- 共有的 -->
      <p class="guide-title">
        <bk-popover
          ref="popover"
          trigger="click"
          theme="light silder-guide"
          placement="bottom-start">
          <span class="guide-link pointer">{{ $t('网络策略开通指引') }}</span>
          <template #content>
            <StrategyTemplate
              v-if="slider.show"
              class="operation-tips"
              :host-type="slider.hostType"
              :host-list="hostList">
            </StrategyTemplate>
          </template>
        </bk-popover>
      </p>
      <p class="guide-title">
        {{ $t('手动操作指引', [$t('目标主机lower'), slider.opType, slider.hostType]) }}
      </p>
      <bk-tab v-if="!commandError" :active.sync="commandType" type="unborder-card">
        <bk-tab-panel v-for="(command, index) in commandData" :name="command.name" :label="command.name" :key="index">

          <p class="commands-title mb20">{{ command.description }}</p>

          <div class="bk-steps bk-steps-vertical bk-steps-dashed bk-steps-primary custom-icon">
            <div class="bk-step current" v-for="(step, stepIndex) in command.steps" :key="stepIndex">
              <span class="bk-step-indicator bk-step-number">
                <span class="number">{{ stepIndex + 1 }}</span>
              </span>

              <section class="bk-step-content">
                <div class="bk-step-title"><p>{{ step.description }}</p></div>

                <section v-if="step.type === 'dependencies'" class="bk-step-body">
                  <P class="mb10">
                    {{ '文件列表：' }}
                    <template v-if="step.contents.length > 1">
                      <bk-link theme="primary" @click="downloadAll(step.contents)">{{ $t('下载全部') }}</bk-link>
                    </template>
                  </P>
                  <p v-for="(file, idx) in step.contents" :key="idx">
                    <bk-link theme="primary" target="_blank" :href="file.text">
                      {{ file.name }}
                      <template v-if="file.description"> ({{ file.description }})</template>
                    </bk-link>
                  </p>
                </section>

                <section v-if="step.type === 'commands'" class="bk-step-body">
                  <ul class="commands-list" v-if="step.contents.length">
                    <li class="commands-item" v-for="(item, idx) in step.contents" :key="idx">
                      <p class="command-title mb10" v-if="item.show_description">{{ item.description }}</p>
                      <div class="command-conatainer single">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <div v-html="item.text" class="commands-left"></div>
                        <div class="commands-right">
                          <p>
                            <i class="nodeman-icon nc-copy command-icon" v-bk-tooltips="{
                              delay: [300, 0],
                              content: $t('复制命令')
                            }" @click="copyCommand(item.text)"></i>
                          </p>
                        </div>
                      </div>
                    </li>
                  </ul>
                  <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
                </section>
              </section>
            </div>
          </div>

        </bk-tab-panel>
      </bk-tab>
      <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
    </div>
  </bk-sideslider>
</template>

<script lang="ts">
import { Vue, Component, Prop, Model, Emit, Watch } from 'vue-property-decorator';
import Tips from '@/components/common/tips.vue';
import StrategyTemplate from '@/components/common/strategy-template.vue';
import ExceptionCard from '@/components/exception/exception-card.vue';
import { copyText } from '@/common/util';
import { TaskStore } from '@/store';
import { ITaskHost, ITaskSolutions, ITaskSolutionsFile } from '@/types/task/task';

@Component({
  name: 'TaskDetailSlider',
  components: {
    Tips,
    StrategyTemplate,
    ExceptionCard,
  },
})
export default class TaskDetailSlider extends Vue {
  @Model('update', { default: false }) private readonly show!: boolean;
  @Prop({ type: Object, default: () => ({ row: {} }) }) private readonly slider!: Dictionary;
  @Prop({ type: String, default: '' }) private readonly title!: string;
  @Prop({ type: [String, Number], default: '' }) private readonly taskId!: string | number;
  @Prop({ type: String, default: '' }) private readonly operateHost!: string;
  @Prop({ type: Array, default: () => [] }) private readonly tableList!: ITaskHost[];

  private commandLoading = false;
  private commandType = '';
  private commandData: ITaskSolutions[] = [];
  private commandError = false;
  private iframeId = 1;

  private get hostList() {
    const list = this.tableList.map(item => ({
      bk_cloud_id: item.bkCloudId,
      bk_cloud_name: item.bkCloudName,
      ap_id: item.apId,
      inner_ip: item.innerIp,
    }));
    list.sort((a, b) => a.bk_cloud_id - b.bk_cloud_id);
    return list;
  }

  @Watch('show')
  public handleShowChange(isShow: boolean) {
    if (isShow) {
      this.commandError = false;
      this.requestCommandData(this.slider.row);
    } else {
      this.commandData = [];
      this.commandLoading = false;
    }
  }

  // 每次点击都需要获取最新的命令
  public async requestCommandData(row: any) {
    if (!this.commandLoading) {
      this.commandLoading = true;
      const res = await TaskStore.requestCommands({
        jobId: this.taskId as number,
        params: { bk_host_id: row.bkHostId },
      });
      if (res) {
        this.commandData = res.solutions || [];
        this.commandType = this.commandData.length ? this.commandData[0].name : '';
      }
      this.commandError = !res;
      this.commandLoading = false;
    }
  }
  public async copyCommand(commandStr: string) {
    if (commandStr) {
      copyText(commandStr, () => {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('命令复制成功'),
        });
      });
    }
  }
  public handleDown(url: string) {
    const { iframeId } = this;
    this.iframeId += 1;
    const iframeName = `iframe_${iframeId}`;
    const frame = document.createElement('iframe'); // 创建a对象
    frame.setAttribute('style', 'display: none');
    frame.setAttribute('src', url);
    frame.setAttribute('id', iframeName);
    document.body.appendChild(frame);
    setTimeout(() => {
      const node = document.getElementById(iframeName) as HTMLElement;
      node.parentNode?.removeChild(node);
    }, 5000);
  }
  public downloadAll(list: ITaskSolutionsFile[]) {
    list.forEach(({ text }) => this.handleDown(text));
  }

  @Emit('update')
  public handleHidden() {
    return false;
  }
}
</script>

<style lang="postcss" scoped>
  .bk-steps-vertical {
    .bk-step {
      display: flex;
      white-space: normal;
      &:last-child::after {
        display: none;
      }
    }
    .bk-step-number {
      flex-shrink: 0;
    }
    .bk-step-content {
      margin-left: 6px;
      display: flex;
      flex-direction: column;
      padding-bottom: 24px;
    }
    .bk-step-title {
      line-height: 24px;
      font-size: 16px;
      color: #000!important;
    }
    .bk-step-body {
      margin-top: 12px;
      font-size: 14px;
    }
  }

  .task-detail-wrapper {
    .tips-text-decs {
      color: #313238;
    }
    .execut-text {
      &.has-icon {
        cursor: pointer;
      }
      &:hover .filtered-icon {
        color: #3a84ff;
      }
    }
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  /deep/ .row-ip .cell {
    padding-left: 24px;
  }
  /deep/ .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  .guide-title {
    margin: 0 0 14px 0;
    .guide-link {
      color: #3a84ff;
      &.pointer {
        cursor: pointer;
      }
    }
  }
  .commands-slider {
    .commands-wrapper {
      padding: 24px 30px;
      min-height: calc(100vh - 52px);
      overflow: auto;
    }
    .commands-step-title {
      color: #000;
      font-size: 14px;
    }
    .commands-item {
      margin-bottom: 20px;
      &:last-child {
        margin-bottom: 0;
      }
    }
    .command-title {
      font-size: 14px;
      color: #63656e;
    }
    .command-conatainer {
      position: relative;
      padding: 12px 28px 16px 20px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      background: #fafbfd;
      .commands-left {
        width: 100%;
        max-height: 128px;
        min-height: 22px;
        line-height: 18px;
        font-size: 12px;
        color: #979ba5;
        overflow-x: hidden;
        overflow-y: auto;
        word-break: break-all;
        >>> span {
          color: #313238;
        }
      }
      &.fold {
        padding: 7px 10px;
        .commands-left {
          padding-right: 56px;
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }
      &.single .commands-left {
        max-height: none;
      }
      .commands-right {
        position: absolute;
        right: 5px;
        bottom: 5px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        width: 46px;
        line-height: 18px;
        font-size: 17px;
        text-align: right;
      }
      .command-icon {
        color: #979ba5;
        cursor: pointer;
        &:hover {
          color: #63656e;
        }
      }
    }
  }
  .operation-tips {
    max-height: 600px;
    overflow: auto;
  }
</style>
