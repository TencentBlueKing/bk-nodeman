<template>
  <bk-sideslider
    ext-cls="commands-slider"
    transfer
    quick-close
    :width="960"
    :is-show="show"
    :title="$t('手动操作sliderTitle', [slider.opType, slider.row.ip])"
    :before-close="handleHidden">
    <div slot="content" class="commands-wrapper" v-bkloading="{ isLoading: commandLoading }">
      <div class="command-tab">
        <div class="command-tab-head">
          <div :class="['step', { active: tabActive === 'net' }]" @click="tabActive = 'net'">
            <div class="step-content">{{ $t('网络开通策略') }}</div>
          </div>
          <div :class="['step', { active: tabActive === 'operate' }]" @click="tabActive = 'operate'">
            <div class="step-content">{{ $t('手动操作sliderTitle', [slider.opType, slider.hostType]) }}</div>
          </div>
        </div>
        <div class="command-tab-content">
          <!-- 共有的 -->
          <StrategyTemplate
            v-if="tabActive === 'net'"
            class="operation-tips"
            :host-type="slider.hostType"
            :host-list="hostList">
          </StrategyTemplate>
          <div class="operate-content" v-else>
            <div v-if="!commandError">
              <p class="step-title">{{ $t('安装方式') }}:</p>
              <div class="mb30 tag-wrapper">
                <div class="tag-group">
                  <template v-for="(command, index) in commandData">
                    <span class="tag-group-delimiter" v-if="index" :key="index"></span>
                    <span
                      :class="['tag-item', { active: commandType === command.type }]"
                      :key="index"
                      @click="commandType = command.type;">
                      {{ command.type }}
                    </span>
                  </template>
                </div>
                <p class="command-desc">{{ commandDesc }}</p>
              </div>
              <section v-for="(command, index) in commandData" :key="index">
                <template v-if="command.type === commandType">
                  <p class="step-title">{{ $t('在目标主机通过安装', [commandType]) }}:</p>
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
                              <bk-link theme="primary" @click="handleDownloadAll(step.contents)">
                                {{ $t('下载全部') }}
                                <i class="nodeman-icon nc-xiazai"></i>
                              </bk-link>
                            </template>
                          </P>
                          <p v-for="(file, idx) in step.contents" :key="idx">
                            <bk-link theme="primary" target="_blank" @click="handleDownload(file.name)">
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
                                <div class="commands-left">
                                  <p>
                                    <i class="nodeman-icon nc-copy command-icon" v-bk-tooltips="{
                                      delay: [300, 0],
                                      content: $t('复制命令')
                                    }" @click="copyCommand(item.text)"></i>
                                  </p>
                                </div>
                                <!-- eslint-disable-next-line vue/no-v-html -->
                                <div v-html="item.text" class="commands-right"></div>
                              </div>
                            </li>
                          </ul>
                          <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
                        </section>
                      </section>
                    </div>
                  </div>
                </template>
              </section>
            </div>
            <ExceptionCard v-else type="dataAbnormal"></ExceptionCard>
          </div>
        </div>
      </div>
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
  private tabActive  = 'net';
  private commandType = '';
  private commandData: ITaskSolutions[] = [];
  private commandError = false;

  private get hostList() {
    const list = this.tableList.map(item => ({
      bk_cloud_id: item.bkCloudId,
      bk_cloud_name: item.bkCloudName,
      ap_id: item.apId,
      ip: item.ip,
    }));
    list.sort((a, b) => a.bk_cloud_id - b.bk_cloud_id);
    return list;
  }
  private get commandDesc() {
    return this.commandType
      ? this.commandData.find(item => item.type === this.commandType)?.description || ''
      : '';
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
        this.commandType = this.commandData.length ? this.commandData[0].type : '';
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
  public handleDownload(name: string) {
    const element = document.createElement('a');
    element.setAttribute('href', `tools/download/?file_name=${name}`);
    element.setAttribute('download', name);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  }
  public handleDownloadAll(list: ITaskSolutionsFile[]) {
    list.forEach(({ name }) => {
      this.handleDownload(name);
    });
  }

  @Emit('update')
  public handleHidden() {
    return false;
  }
}
</script>

<style lang="postcss" scoped>
  .command-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    .command-tab-head {
      position: relative;
      display: flex;
      align-items: flex-end;
      padding: 0 30px;
      height: 56px;
      background-color: #f5f6fa;
      &::after {
        position: absolute;
        left: 0;
        bottom: 0;
        content: "";
        display: block;
        width: 100%;
        border-bottom: 1px solid #dcdee5;
      }
      .step {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 42px;
        padding: 0 16px;
        background: #e1e3eb;
        border-radius: 4px 4px 0 0;
        font-size: 14px;
        cursor: pointer;
        .step-content {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }
        &.active {
          background: #fff;
          border: 1px solid #dcdee5;
          border-bottom: 1px solid #fff;
          box-shadow: 0px 0px 6px 0px rgba(0,0,0,.04);
          color: #313238;
          z-index: 5;
        }
        & + .step {
          margin-left: 8px;
        }
      }
    }
    .command-tab-content {
      flex: 1;
      padding: 20px 30px;
      overflow: auto;
    }
    .step-title {
      margin-bottom: 8px;
      line-height: 22px;
      font-weight: Bold;
      font-size: 14px;
      color: #63656e;
    }
    .tag-wrapper {
      display: flex;
      align-items: center;
      height: 32px;
      .command-desc {
        margin-left: 8px;
        color: #979ba5;
      }
    }
    .tag-group {
      display: flex;
      align-items: center;
      padding: 0 4px;
      height: 100%;
      border-radius: 4px;
      background-color: #f0f1f5;

      .tag-item {
        padding: 0px 6px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        border-radius: 4px;
        &.active {
          background-color: #fff;
          color: #3a84ff;
        }
      }

      .tag-group-delimiter {
        margin:  0 4px;
        width: 1px;
        height: 14px;
        background-color: #dcdee5;
      }
    }
  }
  .bk-steps-vertical {
    .bk-step {
      display: flex;
      white-space: normal;
      &::after {
        background: #dcdee5;
      }
      &:last-child::after {
        display: none;
      }
    }
    .bk-step-number {
      flex-shrink: 0;
    }
    .bk-step-content {
      flex: 1;
      margin-left: 6px;
      display: flex;
      flex-direction: column;
      padding-bottom: 24px;
    }
    .bk-step-title {
      line-height: 22px;
      font-size: 14px;
    }
    .bk-step-body {
      margin-top: 12px;
      font-size: 12px;
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
  >>> .row-select .cell {
    padding-left: 24px;
    padding-right: 0;
  }
  >>> .row-ip .cell {
    padding-left: 24px;
  }
  >>> .row-select .cell {
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
      /* padding: 24px 30px; */
      max-height: calc(100vh - 52px);
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
      padding: 12px 12px 12px 40px;
      /* border: 1px solid #dcdee5; */
      border-radius: 2px;
      background: #f5f7fa;
      .commands-right {
        width: 100%;
        max-height: 128px;
        min-height: 22px;
        line-height: 20px;
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
        .commands-right {
          padding-left: 40px;
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }
      &.single .commands-right {
        max-height: none;
      }
      .commands-left {
        position: absolute;
        left: 12px;
        top: 12px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        /* width: 46px; */
        font-size: 16px;
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
    max-height: 100%;
    overflow: auto;
  }
</style>
