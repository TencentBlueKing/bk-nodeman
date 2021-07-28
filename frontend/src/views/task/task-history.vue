<template>
  <div class="task-history-wrapper">
    <!--选择业务-->
    <bk-biz-select
      v-model="search.biz"
      ext-cls="left-select"
      :placeholder="$t('全部业务')"
      @change="handleBizChange">
    </bk-biz-select>
    <!--search select 双向绑定的变量来自mixin-->
    <bk-search-select
      class="task-filter-select"
      :show-condition="false"
      :placeholder="$t('请输入')"
      :data="searchSelectData"
      v-model="searchSelectValue"
      @change="handleSearchSelectChange">
    </bk-search-select>
    <section class="task-table">
      <bk-table
        v-bkloading="{ isLoading: loading }"
        ref="agentTable"
        :data="tableList"
        :pagination="pagination"
        :limit-list="pagination.limitList"
        :row-style="getRowStyle"
        :class="`head-customize-table ${ fontSize }`"
        @sort-change="sortHandle"
        @row-click="detailHandler"
        @page-change="pageChange"
        @page-limit-change="paginationChange">
        <bk-table-column :label="$t('任务ID')" prop="job_id" :resizable="false">
          <template #default="{ row }">
            <a href="javascript: " class="primary">{{ row.id }}</a>
          </template>
        </bk-table-column>
        <bk-table-column
          class-name="biz-column"
          prop="bkBizScopeDisplay"
          :label="$t('业务')"
          :resizable="false">
          <template #default="{ row }">
            {{ row.bkBizScopeDisplay && row.bkBizScopeDisplay.length ? row.bkBizScopeDisplay.join(',') : '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="job_type"
          min-width="140"
          :label="$t('任务类型')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.jobTypeDisplay ? row.jobTypeDisplay : '--' }}
          </template>
        </bk-table-column>
        <bk-table-column
          prop="created_by"
          :label="$t('执行者')"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            {{ row.createdBy ? row.createdBy : '--' }}
          </template>
        </bk-table-column>
        <bk-table-column width="185" :label="$t('执行时间')" prop="startTime">
          <template #default="{ row }">
            {{ formatTimeByTimezone(row.startTime) }}
          </template>
        </bk-table-column>
        <bk-table-column align="right" :label="$t('总耗时')" prop="costTime">
          <template #default="{ row }">{{ takesTimeFormat(row) }} </template>
        </bk-table-column>
        <bk-table-column min-width="20" :resizable="false"></bk-table-column>
        <bk-table-column
          prop="status"
          min-width="115"
          :label="$t('执行状态')"
          :resizable="false"
          :render-header="renderFilterHeader">
          <template #default="{ row }">
            <div class="col-execution">
              <loading-icon v-if="row.status === 'running'"></loading-icon>
              <span v-else :class="`execut-mark execut-${ row.status }`"></span>
              <span :title="titleStatusMap[row.status]">{{ titleStatusMap[row.status] }}</span>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column align="right" :label="$t('总数')" :resizable="false" prop="total_count" sortable="custom">
          <template #default="{ row }">
            <span v-if="isEmptyCell(row.statistics.totalCount)">{{ row.statistics.totalCount }}</span>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column align="right" :label="$t('成功数')" prop="success_count" sortable="custom">
          <template #default="{ row }">
            <a
              v-if="isEmptyCell(row.statistics.successCount)"
              href="javascript: "
              class="success"
              @click.stop="detailHandler(row, 'success')">
              {{ row.statistics.successCount }}
            </a>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column
          min-width="80"
          align="right"
          :label="$t('失败数')"
          prop="failed_count"
          sortable="custom"
          :resizable="false">
          <template #default="{ row }">
            <a
              v-if="isEmptyCell(row.statistics.failedCount)"
              href="javascript: "
              class="failed"
              @click.stop="detailHandler(row, 'failed')">
              {{ row.statistics.failedCount }}
            </a>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <!--自定义字段显示列-->
        <bk-table-column
          key="setting"
          prop="colspaSetting"
          width="42"
          :render-header="renderHeader"
          :resizable="false">
        </bk-table-column>
      </bk-table>
    </section>
  </div>
</template>

<script>
import tableHeaderMixins from '@/components/common/table-header-mixins';
import ColumnSetting from '@/components/common/column-setting';
import pollMixin from '@/common/poll-mixin';
import { MainStore, TaskStore } from '@/store';
import { debounce, isEmpty, takesTimeFormat } from '@/common/util';

export default {
  name: 'TaskHistory',
  mixins: [tableHeaderMixins, pollMixin],
  data() {
    return {
      loading: false,
      titleStatusMap: {
        pending: this.$t('等待执行'),
        running: this.$t('正在执行'),
        success: this.$t('执行成功'),
        failed: this.$t('执行失败'),
        part_failed: this.$t('部分失败'),
        stop: this.$t('已终止'),
        terminated: this.$t('已终止'),
      },
      pagination: {
        limit: 50,
        current: 1,
        count: 0,
        limitList: [50, 100, 200],
      },
      tableList: [],
      search: {
        biz: [],
      },
      // 搜索防抖
      getHistortListDebounce() {},
      filterData: [],
      // 排序参数
      sortData: {
        head: '',
        sort_type: '',
      },
    };
  },
  computed: {
    fontSize() {
      return MainStore.fontSize;
    },
  },
  watch: {
    searchSelectValue: {
      handler() {
        this.getHistortListDebounce();
      },
      deep: true,
    },
  },
  created() {
    this.search.biz = MainStore.selectedBiz;
    this.getHistortList();
    this.handleGetConditionData();
  },
  mounted() {
    this.getHistortListDebounce = debounce(300, this.pageChange);
  },
  methods: {
    /**
     * 获取搜索条件
     */
    async handleGetConditionData() {
      this.filterData = await TaskStore.getFilterList();
    },
    /**
     * 获取请求参数
     */
    getCommonParams() {
      const params = {
        page: this.pagination.current,
        pagesize: this.pagination.limit,
      };
      if (this.search.biz.length) {
        params.bk_biz_id = this.search.biz;
      }
      if (this.sortData.head && this.sortData.sort_type) {
        params.sort = Object.assign({}, this.sortData);
      }
      // searchSelectValue mixin混入的变量
      this.searchSelectValue.forEach((item) => {
        if (item.values) {
          params[item.id] = item.values.map(value => value.id);
        }
      });
      return params;
    },
    /**
     * 获取任务历史列表
     */
    async getHistortList() {
      this.loading = true;
      // 清空上一次的轮询
      this.runingQueue.splice(0, this.runingQueue.length);
      clearTimeout(this.timer);
      this.timer = null;

      const params = this.getCommonParams();
      const res = await TaskStore.requestHistoryTaskList(params);
      this.pagination.count = res.total;
      this.tableList = res.list;
      // 运行任务队列 pollMixin: runingQueue 非成功状态都可以再执行
      this.runingQueue = res.list.filter(item => item.status && item.status !== 'success').map(item => item.id);
      this.loading = false;
    },
    /**
     * 处理轮询的数据
     */
    async handlePollData() {
      const data = await TaskStore.requestHistoryTaskList({
        page: 1,
        pagesize: this.runingQueue.length,
        job_id: this.runingQueue,
      });
      data.list.forEach((item) => {
        const index = this.tableList.findIndex(row => row.id === item.id);
        if (index > -1) {
          if (item.status !== 'running') {
            const i = this.runingQueue.findIndex(id => id === item.id);
            this.runingQueue.splice(i, 1);
          }
          this.$set(this.tableList, index, item);
        }
      });
    },
    /**
     * 业务变更
     */
    handleBizChange() {
      this.getHistortListDebounce();
    },
    /**
     * 分页
     */
    pageChange(page) {
      this.pagination.current = page || 1;
      this.getHistortList();
    },
    /**
     * 分页条数
     */
    paginationChange(limit) {
      this.pagination.limit = limit || 10;
      this.getHistortListDebounce();
    },
    /**
     * 详情
     */
    detailHandler(row, status) {
      this.$router.push({
        name: 'taskDetail',
        params: {
          taskId: row.id,
          status: status && typeof status === 'string' ? status.toUpperCase() : '',
        },
      });
    },
    isEmptyCell(cell) {
      return !isEmpty(cell);
    },
    getRowStyle() {
      return { cursor: 'pointer' };
    },
    sortHandle({ prop, order }) {
      Object.assign(this.sortData, {
        head: prop,
        sort_type: order === 'ascending' ? 'ASC' : 'DEC',
      });
      this.getHistortListDebounce();
    },
    /**
     * 自定义字段显示列
     * @param {createElement 函数} h 渲染函数
     */
    renderHeader(h) {
      return h(ColumnSetting);
    },
    /**
     * 耗时格式化
     */
    takesTimeFormat(row) {
      const { startTime, endTime } = row;
      if (!startTime || !endTime) {
        return '--';
      }
      const startNum = new Date(startTime).getTime();
      const endNum = new Date(endTime).getTime();
      return (isNaN(startNum) || isNaN(endNum)) ? '--' : takesTimeFormat((endNum - startNum) / 1000);
    },
  },
};
</script>

<style lang="postcss" scoped>
@import "@/css/mixins/nodeman.css";

.task-history-wrapper {
  min-height: calc(100vh - 140px);
  padding: 0 0 30px 0;
  overflow: auto;
  .left-select {
    float: left;
    width: 160px;
    background: #fff;
  }
  .task-filter-select {
    float: right;
    margin: 0 0 14px 0;
    width: 500px;
    background: #fff;
  }
  .task-table {
    margin-top: 14px;
    .primary {
      color: #3a84ff;
    }
    .success {
      color: #2dcb56;
    }
    .failed {
      color: #ea3636;
    }
    >>> .biz-column .cell {
      padding-left: 0;
    }
  }
}
</style>
