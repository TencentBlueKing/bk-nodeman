<template>
  <section class="task-log-content clearfix">
    <div class="step-wrapper">
      <div class="outer-border-cover">
        <bk-table
          ext-cls="log-step-table"
          ref="logStepTable"
          height="100%"
          size="small"
          :data="stepList"
          :row-style="getRowStyle"
          @row-click="handleStepClick">
          <bk-table-column :label="$t('步骤')" :resizable="false" min-width="180">
            <template #default="{ row, $index }">
              <span :class="row.status" :title="row.step">
                {{ `${ $index + 1 }. ${ row.step }` }}
              </span>
            </template>
          </bk-table-column>

          <bk-table-column class-name="column-subscript" align="right" prop="spendTime" :label="$t('耗时')">
          </bk-table-column>

          <bk-table-column class-name="column-subscript" min-width="15"></bk-table-column>

          <bk-table-column class-name="column-subscript" :label="$t('执行情况')" :resizable="false" min-width="105">
            <template #default="{ row }">
              <div
                class="command-guide col-execution"
                v-if="['running', 'pending'].includes(row.status) && showCommandBtn && row.step === commandStep">
                <span class="execut-mark execut-ignored"></span>
                <i18n tag="span" path="等待手动操作查看" class="execut-text">
                  <bk-button text theme="primary" @click="handleRowView">
                    {{ $t('操作指引') }}
                  </bk-button>
                </i18n>
              </div>
              <div v-else class="col-execution">
                <loading-icon v-if="row.status === 'running'"></loading-icon>
                <span v-else :class="`execut-mark execut-${ row.status }`"></span>
                <span :class="row.status" :title="statusMap[row.status]">{{ statusMap[row.status] }}</span>
              </div>
            </template>
          </bk-table-column>

          <bk-table-column class-name="column-subscript" prop="opera" :width="hasOperaCell ? 100 : 30">
            <template #default="{ row, $index }">
              <bk-button
                v-if="row.status === 'running' && !(showCommandBtn && row.step === commandStep)"
                v-test="'stop'"
                ext-cls="step-operation"
                size="small"
                hover-theme="danger"
                :disabled="stopLoading || retryLoading"
                @click.stop="handleTaskStop(row)">
                <loading-icon v-if="stopLoading"></loading-icon>
                <span v-else>{{ $t('终止') }}</span>
              </bk-button>
              <i class="bk-icon icon-right-shape" v-if="isLogOverflow && scrollStep === $index"></i>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </div>

    <div :class="['log-detail-wrapper', { 'log-detail-screen': isFullScreen }]">
      <div class="log-detail-content">
        <div class="log-header clearfix">
          <h4 class="title fl">{{ $t('执行日志') }}</h4>
          <div>
            <i class="mr20 nodeman-icon nc-xiazai"
               v-bk-tooltips="{
                 delay: [300, 0],
                 content: $t('下载日志'),
                 theme: 'log-operate',
                 placements: ['top']
               }"
               v-test="'download'"
               @click="exportHandle"></i>
            <i :class="`nodeman-icon nc-icon-${ isFullScreen ? 'un-' : '' }full-screen`"
               v-bk-tooltips="{
                 delay: [300, 0],
                 content: isFullScreen ? $t('退出全屏') : $t('全屏'),
                 theme: 'log-operate',
                 placements: ['top']
               }"
               @click.stop="handleScreen"></i>
          </div>
        </div>

        <div class="log-body">
          <div class="log-sheet sheet-top"></div>
          <div class="log-content" ref="logContent">
            <div class="log-list" ref="logList">
              <section v-for="(step, index) in stepList" :key="`step${index}`">
                <div ref="step" :id="`log${index}`">
                  <template v-if="step.formatLog">
                    <div
                      v-for="(log, logIndex) in step.formatLog"
                      :key="logIndex"
                      :class="['log-item', log.type, { 'is-fold': log.isFold }]">
                      <!-- eslint-disable-next-line vue/no-v-html -->
                      <span class="log-text" v-html="log.content"></span>
                      <i
                        v-if="log.type === 'debug'"
                        :class="`log-fold-icon bk-icon icon-play-shape ${ log.isFold ? 'right' : 'down'}`"
                        @click="logTextToggle(log)">
                      </i>
                    </div>
                  </template>
                </div>
              </section>
              <span class="dot" v-if="dotLoading">...</span>
            </div>
          </div>
          <div class="log-sheet sheet-bottom"></div>
        </div>
      </div>
      <div v-if="isLogOverflow && !isKeepScroll" class="btn-scroll-bottom" @click="scrollToBottom">
        <i class="nodeman-icon nc-icon-bottom-fill"></i>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { Component, Emit, Prop, Ref, Vue } from 'vue-property-decorator';
import { addListener, removeListener } from 'resize-detector';
import { downloadLog, debounce } from '@/common/util';
import { IStepItem, ILog } from '@/types/task/task';

@Component({ name: 'TaskLogContent' })

export default class TaskLogContent extends Vue {
  @Prop({ type: String, default: [String, Number] }) private readonly taskId!: string | number;

  @Prop({ type: Boolean, default: false }) private readonly stopLoading!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly retryLoading!: boolean;
  @Prop({ type: Boolean, default: false }) private readonly dotLoading!: boolean;
  @Prop({ type: String, default: '' }) private readonly jobType!: string;
  @Prop({ type: String, default: '' }) private readonly curIp!: string;
  @Prop({ type: String, default: '-1' }) private readonly curId!: string;
  @Prop({ type: Boolean, default: false }) private readonly isManualType!: boolean;
  @Prop({ type: Array, default: () => [] }) private readonly stepList!: IStepItem[];

  @Ref('step') private readonly stepRef!: HTMLElement[];
  @Ref('logContent') private readonly logWrapperEle!: any;
  @Ref('logList') private readonly logList!: HTMLElement;

  public loading = true;
  public isFullScreen = false;
  public isKeepScroll = true; // 日志是否保持在最新
  public statusMap = {
    running: this.$t('正在执行'),
    failed: this.$t('执行失败'),
    part_failed: this.$t('部分失败'),
    success: this.$t('执行成功'),
    stop: this.$t('已终止'),
    pending: this.$t('等待执行'),
  };;
  public listenResize =function () {};
  public scrollStep = 0;
  public logOffsetTop: { top: number, height: number, content: boolean }[] = [];
  public isManualTrigger = false; // 点击步骤时防止自动计算下标
  public logContentHeight = 0; // 日志容器高度
  public isLogOverflow = false; // 日志内容是否溢出
  public listLoading = false;
  public relativePosition = 0;
  public movePosition = 0;

  private get hasOperaCell() {
    return this.stepList.find(item => item.status === 'running');
    // return this.stepList.find(item => item.status === 'running' || item.status === 'failed')
  }
  // 操作的主机或任务类型 Agent | Proxy | Plugin
  private get operateHost() {
    const res = /(agent)|(proxy)|(plugin)/ig.exec(this.jobType);
    return res ? res[0] : '';
  }
  // 能查看命令的任务类型
  private get showCommandBtn() {
    if (!this.operateHost || this.operateHost === 'Plugin' || !this.isManualType) {
      return false;
    }
    return /(INSTALL)|(REINSTALL)|(UPGRADE)/ig.test(this.jobType);
  }
  private get commandStep() {
    return /UN/ig.test(this.jobType) ? this.$t('手动卸载Guide') : this.$t('手动安装Guide');
  }

  private mounted() {
    this.logWrapperEle.addEventListener('scroll', this.handleScroll);
    this.listenResize = debounce(300, () => this.handleResize());
    addListener(this.$el as HTMLElement, this.listenResize);
  }
  private beforeDestroy() {
    removeListener(this.$el as HTMLElement, this.listenResize);
    window.removeEventListener('scroll', this.handleScroll);
  }

  public handleScroll() {
    const { scrollTop } = this.logWrapperEle;
    // 保留本次滚动scrollTop（和上次进行对比，判断滚动方向）
    this.movePosition = scrollTop;
    const contentHeight = this.logWrapperEle.scrollHeight;
    this.isKeepScroll = scrollTop >= contentHeight - this.logContentHeight;

    if (!this.isManualTrigger) {
      const paddingTop = 20;
      // 判断滚动方向
      const direction = this.movePosition < this.relativePosition ? 'up' : 'down';
      let index = 0;

      if (direction === 'up') {
        // 向上滚动时找到第一个即可
        index = this.logOffsetTop.findIndex(item => item.content
          && ((scrollTop + paddingTop) < (item.top + item.height)));
      } else {
        // 向下滚动时找到最后一个
        this.logOffsetTop.forEach((item, logIndex) => {
          if (item.content && (scrollTop + this.logContentHeight > item.top + paddingTop)) {
            index = logIndex;
          }
        });
      }

      if (index < 0) {
        index = this.logOffsetTop.findIndex(item => item.content);
        this.logOffsetTop.forEach((item, itemIndex) => {
          if (item.content) {
            index = itemIndex;
          }
        });
      }
      this.scrollStep = index;
      // 更新上一次的 scrollTop
      this.relativePosition = this.movePosition;
    }
    this.isManualTrigger = false;
  }
  public tryScrollToBottom() {
    if (this.isKeepScroll) {
      this.$nextTick(this.scrollToBottom);
    }
  }
  public resetOffsetInfo() {
    this.logOffsetTop = this.stepRef ? this.stepRef.map((item: HTMLElement) => ({
      top: item.offsetTop,
      height: item.offsetHeight,
      content: !!item.textContent,
    })) : [];
    this.handleResize();
  }
  /*
    * 滚动到底部
    */
  public scrollToBottom() {
    this.isKeepScroll = true;
    const contentHeight = this.logWrapperEle.scrollHeight;
    this.logWrapperEle.scrollTop = contentHeight - this.logContentHeight;
  }
  /**
   * 日志步骤点击事件
   */
  public handleStepClick(row: IStepItem) {
    if (!row.status) return;
    this.isManualTrigger = true; // 打开手动计算模式
    // 找到锚点
    const rowIndex = this.stepList.findIndex(item => item.id === row.id && item.step === row.step);
    const anchor = document.getElementById(`log${rowIndex}`);
    if (anchor && this.logWrapperEle) {
      if (row.status === 'running' || row.status === 'pending') {
        this.isManualTrigger = false;
        this.scrollToBottom();
      } else {
        this.scrollStep = rowIndex;
        const total = anchor.offsetTop; // 定位锚点
        this.logWrapperEle.scrollTop = total - 20; // 20 顶部遮罩层高度 -> log-header
      }
    }
  }
  /**
   * 下载日志
   */
  public exportHandle() {
    const logArr = this.stepList.reduce((arr: string[], item) => {
      arr.push(item.log);
      return arr;
    }, []);
    downloadLog(`bk_nodeman_${this.taskId}_${this.curIp}.log`, logArr.join('\n'));
  }
  /**
   * 日志全屏
   */
  public handleScreen() {
    this.isFullScreen = !this.isFullScreen;
    this.$nextTick(() => {
      this.handleResize();
    });
  }
  public getRowStyle() {
    return {
      cursor: this.isLogOverflow ? 'pointer' : 'default',
    };
  }
  /**
   * 折叠日志
   */
  public logTextToggle(log: ILog) {
    if (log.type === 'debug') {
      log.isFold = !log.isFold;
      this.$nextTick(() => {
        this.logOffsetTop = this.stepRef ? this.stepRef.map(item => ({
          top: item.offsetTop,
          height: 0,
          content: !!item.textContent,
        })) : [];
      });
    }
  }
  /**
   * 监听窗口大小，判断是否需要展示日志步骤下标
   */
  public handleResize() {
    this.logContentHeight = this.logWrapperEle.offsetHeight;
    this.isLogOverflow = this.logList && (this.logContentHeight < this.logList.offsetHeight);
  }
  @Emit('task-stop')
  public handleTaskStop(row: IStepItem) {
    return row;
  }
  @Emit('row-view')
  public handleRowView() {}
}
</script>

<style lang="postcss" scoped>
@import "@/css/variable.css";
@import "@/css/transition.css";

.task-log-content {
  flex: 1;
  display: flex;
  height: calc(100% - 100px);
}
.step-wrapper {
  width: 420px;
  min-width: 40%;
  height: 100%;
  border-bottom: 0;
  background: #fafbfd;
  overflow: hidden;
}
.outer-border-cover {
  height: 100%
}
.log-step-table {
  width: 100%;
  .pending {
    color: #c4c6cc;
  }
  .step-operation {
    padding: 0 5px;
    min-width: 54px;
  }
  >>> .column-subscript {
    .cell {
      padding: 0 10px;
    }
    i.icon-right-shape {
      position: absolute;
      top: 15px;
      right: 10px;
      color: #c4c6cc;
    }
  }
  .command-guide {
    position: absolute;
    top: 10px;
    left: 10px;
    white-space: nowrap;
    z-index: 5;
  }
}
.log-detail-wrapper {
  position: relative;
  flex: 1;
  padding-left: 10px;
  overflow: hidden;
  &.log-detail-screen {
    position: fixed;
    top: 52px;
    right: 0;
    bottom: 0;
    left: 0;
    padding: 0;
    z-index: 1050;
  }
  .btn-scroll-bottom {
    position: absolute;
    right: 24px;
    bottom: 10px;
    font-size: 0;
    cursor: pointer;
    z-index: 20;
    i {
      font-size: 28px;
      color: #98989b;
    }
  }
}
.log-detail-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 0px 0px 2px 2px;
  background: #313238;
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 15px 0 20px;
  height: 43px;
  border-bottom: 1px solid #3b3c42;
  font-size: 14px;
  background: #202024;
  overflow: hidden;
  .title {
    flex: 1;
    margin: 0;
    font-weight: normal;
    color: #fff;
  }
  .nodeman-icon {
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
  }
}
.log-body {
  flex: 1;
  position: relative;
  width: 100%;
  overflow: hidden;
  .log-sheet {
    position: absolute;
    left: 0;
    right: 14px;
    height: 20px;
    background: #313238;
    z-index: 10;
  }
  .sheet-top {
    top: 0;
  }
  .sheet-bottom {
    bottom: 0;
  }
}
.log-content {
  width: 100%;
  height: 100%;
  overflow: auto;
  &::-webkit-scrollbar {
    width: 14px;
    height: 16px;
  }
  &::-webkit-scrollbar-thumb {
    border-radius: 0;
    border: 1px solid #63656e;
    background: #3b3c42;
    box-shadow: none;
  }
  &::-webkit-scrollbar-track {
    box-shadow: inset 1px 0 1px #3b3c42;
    background-color: #313238;
  }
  .log-list {
    padding: 20px 0 20px 0;
  }
  .log-item {
    position: relative;
    padding-left: 30px;
    padding-right: 28px;
    .log-fold-icon {
      position: absolute;
      top: 10px;
      left: 4px;
      padding: 4px 4px;
      font-size: 12px;
      color: #c4c6cc;
      cursor: pointer;
      transition: transform .2s ease-in-out;
      &.down {
        transform: rotate(90deg);
      }
    }
    .log-text {
      display: inline-block; /* stylelint-disable-next-line declaration-no-important */
      font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", "source-code-pro", "monospace" !important;
      line-height: 24px;
      font-size: 12px;
      color: #c4c6cc;
      white-space: pre-wrap;
      word-wrap: break-word;
      word-break: break-word;
      >>> a {
        color: #3c96ff;
        text-decoration: underline;
      }
    }
    &.error .log-text {
      color: #cc4141;
    }
    &.debug {
      padding-top: 7px;
      padding-bottom: 7px;
      background: #2a2b2f;
      .log-text:first-line {
        color: #f0f1f5;
        font-weight: 700;
      }
    }
    &.is-fold .log-text {
      height: 24px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}
.dot {
  position: relative;
  display: inline-block;
  margin-left: 30px;
  font-size: 20px;
  line-height: 22px;
  vertical-align: bottom;
  color: transparent;
  overflow: hidden; /* stylelint-disable-next-line declaration-no-important */
  font-family: simsun!important;
  &::after {
    position: absolute;
    left: 0;
    top: 0;
    display: inline-block;
    content: "...";
    width: 0;
    height: 100%;
    z-index: 5;
    color: #c4b9b9; /* stylelint-disable-next-line declaration-no-important */
    font-family: "simsun"!important;
    vertical-align: bottom;
    overflow: hidden;
    animation: dot 3s infinite step-start;
  }
}
</style>
