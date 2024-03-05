<template>
  <section class="package-manage">

    <section class="package-manage-head">
      <p class="package-manage-title">{{ $t('nav_Agent包管理') }}</p>
      <bk-tab :active="active" type="unborder-card" label-height="40" @tab-change="updateTabActive">
        <bk-tab-panel v-for="(panel, index) in panels" :key="index" v-bind="panel" />
      </bk-tab>
      <bk-button class="upload-btn" theme="primary" @click="toggleUploadShow">{{ $t('包上传') }}</bk-button>
    </section>

    <section class="package-manage-body">
      <bk-search-select
        ref="searchSelect"
        ext-cls="package-search-select"
        :data="searchData"
        v-model="searchSelectValue"
        :show-condition="false"
        :placeholder="$t('版本号、操作系统/架构、标签、上传用户、状态')"
        v-test="'search'"
        @change="() => pagetionChange()">
        <!-- @paste.native.capture.prevent="handlePaste"
        :key="searchInputKey" -->
      </bk-search-select>

      <section class="package-search-content">
        <div class="package-select-quick">
          <div class="select-quick-head">
            <p class="select-quick-title mb10">{{ $t('快捷筛选') }}</p>
            <bk-compose-form-item style="display: flex; width: 100%;">
              <div class="bk-select" style="padding: 0 8px;background-color: #fafbfd;">
                {{ $t('维度') }}
              </div>
              <bk-select :value="dimension" style="flex: 1;" :clearable="false" @selected="updateOptionalList">
                <bk-option v-for="opt in dimensionList" :key="opt.id" :id="opt.id" :name="opt.name" />
              </bk-select>
            </bk-compose-form-item>
          </div>
          <div class="optional-wrapper">
            <ul class="optional-list">
              <li
                v-for="(optItem, index) in dimensionOptionalList"
                :class="['optional-item', { 'is-all': !index, selected: optItem.id === dimensionOptional }]"
                :key="optItem.id"
                @click="selectDimensionOptional(optItem, 'click')">
                <span v-if="optItem.isAll" class="option-icon all">All</span>
                <i v-if="optItem.icon" :class="['option-icon nodeman-icon', optItem.icon]" />
                <!-- <img class="option-icon-image" :src="icon" /> -->
                <span class="option-name">{{ optItem.name }}</span>
                <span class="option-tag">{{ optItem.count }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="package-select-result" v-bkloading="{ isLoading }">
          <PackageCols :rows="tableData" :maxHeight="tableHeight" :pagetion="pagetion" @pagetion="pagetionChange" />
          <bk-pagination
            ext-cls="pagination"
            size="small"
            :limit="pagetion.limit"
            :count="pagetion.count"
            :current="pagetion.current"
            :limit-list="pagetion.limitList"
            align="right"
            show-total-count
            @change="handlePageChange"
            @limit-change="handlePageLimitChange">
          </bk-pagination>
        </div>
      </section>
    </section>
    <PackageUpload
      :show="uploadShow"
      :active="active"
      @toggle="toggleUploadShow"
      @submit="() => updateTabActive(active)" />
  </section>
</template>
<script lang="ts">
import i18n from '@/setup';
import { AgentStore } from '@/store';
import { computed, defineComponent, provide, reactive, ref, toRefs } from 'vue';
import PackageCols from './package-cols.vue';
import PackageUpload from './package-upload.vue';
import { IPagination, ISearchItem } from '@/types';
import { MainStore } from '@/store/index';
import {
  IPkgParams, IPkgTag, IPkgTagOpt, PkgType,
  IPkgQuickOpt, IPkgDimension, IPkgRow,
} from '@/types/agent/pkg-manage';

type PkgQuickType = 'os_cpu_arch' | 'version';

export default defineComponent({
  components: {
    PackageCols,
    PackageUpload,
  },
  setup() {
    const state = reactive<{
      isLoading: boolean;
      panels: { name: PkgType; label: string; }[];
      active: PkgType;
      dimension: PkgQuickType;
      dimensionOptional: string;
      uploadShow: boolean;
      pagetion: IPagination
    }>({
      isLoading: true,
      panels: [
        { name: 'gse_agent', label: 'Agent' },
        { name: 'gse_proxy', label: 'Proxy' },
      ],
      active: 'gse_agent',
      // 维度
      dimension: 'os_cpu_arch',
      dimensionOptional: 'all',
      pagetion: {
        current: 1,
        limit: 50,
        count: 0,
        limitList: [20, 50, 100, 200]
      },
      uploadShow: false,
    });

    // 可选维度
    // Sort：默认 A-Z
    // Sort: 默认倒序，最新的版本号在最上面
    const dimensionList = ref<IPkgDimension[]>([]);
    const dimensionOptionalList = ref<IPkgQuickOpt[]>([]);
    const searchSelectData = ref<ISearchItem[]>([]);
    const searchSelectValue = ref<ISearchItem[]>([]);
    const tableData = ref<IPkgRow[]>([]);
    const tagList = ref<IPkgTagOpt[]>([]);
    const tagGroup = ref<ISearchItem[]>([]);

    const tagsMap = computed(() => tagList.value.reduce((nameMap: { [k: string]: string }, item) => {
      Object.assign(nameMap, {
        [item.id]: item.name,
        [`${item.id}_class`]: item.className,
      });
      return nameMap;
    }, {}));

    // 升级后的组件应该是 onlyRecommendChildren属性来代替此数据
    const searchData = computed(() => searchSelectData.value
      .filter(item => !searchSelectValue.value.find(opt => opt.id === item.id)));

    provide('tagGroup', tagGroup);
    provide('tagsMap', tagsMap);

    const toggleUploadShow = () => {
      state.uploadShow = !state.uploadShow;
    };

    // 更新快捷筛选 维度
    const updateOptionalList = (id: PkgQuickType = 'os_cpu_arch') => {
      state.dimension = id;
      const { children = [] } = dimensionList.value.find(item => item.id === id) || {};
      const copyChildren = [...children];
      let count = 0;
      if (children.length) {
        const isOs = state.dimension === 'os_cpu_arch';
        copyChildren.forEach((child) => {
          if (isOs) {
            child.icon = `nc-${child.id.split('_')[0]}`;
          }
          count += child.count || 0;
        });
      }
      const allOpt = { id: 'all', name: i18n.t('全部'), isAll: true, count };
      copyChildren.unshift(allOpt);
      dimensionOptionalList.value.splice(0, dimensionOptionalList.value.length, ...copyChildren);
      selectDimensionOptional(allOpt);
    };

    // 维度nav click
    const selectDimensionOptional = (opt: IPkgQuickOpt, type?: string) => {
      if (type === 'click' && opt.id === state.dimensionOptional) return;
      state.dimensionOptional = opt.id;
      getTableData();
    };

    // 所有pkg标签
    const getPkgTags = async () => {
      const res = await AgentStore.apiPkgGetTags({ project: state.active });
      const standardGroupData: ISearchItem[] = [];
      const opts: IPkgTagOpt[] = [];
      res.forEach((item) => {
        const children = item.children.map(child => ({
          id: child.name,
          name: child.description,
          className: item.name === 'builtin' ? child.name : '',
        }));
        standardGroupData.push({
          id: item.name,
          name: item.description,
          children: children.map(child => (child.className ? child : { ...child, id: child.name })),
        });
        opts.push(...children);
      });
      tagList.value.splice(0, tagList.value.length, ...opts);
      tagGroup.value.splice(0, tagGroup.value.length, ...standardGroupData);
    };

    // 上传新包之后需要更新搜索条件
    const updateSearchData = async () => {
      const list = await AgentStore.apiPkgFilterCondtion({
        category: 'agent_pkg_manage',
        project: state.active,
      });
      const multipleKey = ['version', 'tags', 'tag_names'];
      searchSelectData.value.splice(0, searchSelectData.value.length, ...list.map(item => ({
        ...item,
        multiable: multipleKey.includes(item.id), // multiple
        onlyRecommendChildren: true,
      })));
      getPkgTags();
    };

    const getParams = () => {
      const params: IPkgParams = {
        project: state.active,
        page: state.pagetion.current,
        pagesize: state.pagetion.limit,
      };
      if (state.dimensionOptional !== 'all') {
        if (state.dimension === 'os_cpu_arch') {
          const [os, ...cpuArch] = state.dimensionOptional.split('_');
          params.os = os;
          params.cpu_arch = cpuArch.join('_');
        } else {
          params[state.dimension] = state.dimensionOptional;
        }
      }
      searchSelectValue.value.forEach((item) => {
        Object.assign(params, {
          [item.id]: item.values?.map(child => `${child.id}`).join(','),
        });
      });
      return params;
    };
    const getTableData = async () => {
      state.isLoading = true;
      const { list = [], total = 0 } = await AgentStore.apiPkgList(getParams());
      state.pagetion.count = total;
      tableData.value.splice(0, tableData.value.length, ...list.map(row => ({
        ...row,
        hostNumber: '',
        formatTags: row.tags.reduce((arr: IPkgTag[], item) => {
          arr.push(...item.children.map(child => ({
            ...child,
            name: child.description,
            className: item.name === 'builtin' ? child.name : '',
          })));
          return arr;
        }, []),
      })));
      if (total) {
        getHostNumber();
      }
      state.isLoading = false;
    };
    const getHostNumber = async () => {
      const params = {
        project: state.active,
        items: tableData.value.map(({ os, cpu_arch, version }) => ({
          os_type: os,
          cpu_arch,
          version,
        })),
      };
      const list = await AgentStore.apiPkgHostsCount(params);
      list.forEach((item) => {
        const child = tableData.value.find(row => row.os === item.os_type
          && row.version === item.version && row.cpu_arch === item.cpu_arch);
        if (child) {
          child.hostNumber = item.count;
        }
      });
    };
    const tableHeight = computed(() =>{
      return MainStore.windowHeight - 300 - (MainStore.noticeShow ? 40 : 0);
    })
    const handlePageChange = (page?: number) => {
      state.pagetion.current = page || 1;
      getTableData();
    }
    const handlePageLimitChange = (limit: number) => {
      state.pagetion.current = 1;
      state.pagetion.limit = limit;
      getTableData();
    }
    const pagetionChange = (pagetion: { page?: number; pagesize?: number } = {}) => {
      const { page, pagesize } = pagetion;
      Object.assign(state.pagetion, {
        current: page || 1,
        limit: pagesize || state.pagetion.limit,
        count: 0,
      });
      getTableData();
    };

    const updateTabActive = async (type: PkgType = 'gse_agent') => {
      if (type !== state.active) {
        searchSelectValue.value.splice(0, searchSelectValue.value.length);
      }
      state.active = type;
      updateSearchData();
      const list = await AgentStore.apiPkgQuickSearch({ project: type });
      dimensionList.value.splice(0, dimensionList.value.length, ...list);
      updateOptionalList();
    };

    const created = () => {
      updateTabActive();
    };
    created();

    return {
      ...toRefs(state),
      dimensionList,
      dimensionOptionalList,
      searchSelectData,
      searchSelectValue,
      tableData,
      searchData,
      tableHeight,

      toggleUploadShow,
      updateOptionalList,
      selectDimensionOptional,
      updateTabActive,
      getTableData,
      pagetionChange,
      handlePageChange,
      handlePageLimitChange
    };
  },
});
</script>
<style lang="postcss">
@import "@/css/variable.css";

.package-manage {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.package-manage-head {
  position: relative;
  background-color: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;

  .package-manage-title {
    padding: 14px 24px 9px 24px;
    line-height: 24px;
    font-size: 16px;
    color: $fontTitleColor;
  }

  .upload-btn {
    position: absolute;
    right: 24px;
    bottom: 12px;
  }

  .bk-tab-section {
    display: none;
  }
}

.package-manage-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px 24px 0;
  overflow: hidden;

  .package-search-select {
    flex-shrink: 0;
    margin-bottom: 18px;
    background-color: $whiteColor;
  }

  .package-search-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
  /* 快捷筛选 */
  .package-select-quick {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    width: 240px;
    margin-right: 18px;
    /* padding: 10px 16px; */
    overflow-x: hidden;
    overflow-y: auto;
    background-color: #fff;
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);
    border-radius: 2px;
  }
  .select-quick-head {
    padding: 10px 16px 8px 16px;
  }
  .optional-wrapper {
    flex: 1;
    padding-bottom: 10px;
    overflow-x: hidden;
    overflow-y: auto;
  }
  .optional-item {
    display: flex;
    align-items: center;
    padding: 0 16px 0 18px;
    height: 36px;
    cursor: pointer;
    &:hover {
      background-color: $bgOptHover;
    }
    &.selected {
      color: $primaryFontColor;
      background-color: $bgOptHover;
      .option-icon {
        color: $primaryFontColor;
      }
      .option-tag {
        color: $whiteColor;
        background-color: #a3c5fd;
       }
    }
  }
  .option-icon-image {
    margin-right: 6px;
    flex-basis: 0;
    /* width: 16px; */
    height: 20px;
  }
  .option-icon {
    margin-right: 4px;
    font-size: 16px;
    color: #979ba5;
    &.all {
      font-size: 14px;
      font-weight: bold;
    }
  }
  .option-name {
    flex: 1;
  }
  .option-tag {
    line-height: 16px;
    padding: 0 8px;
    background-color: #eaebf0;
    border-radius: 2px;
    color: #979ba5;
  }
  /* 表格 */
  .package-select-result {
    flex: 1;
    overflow: hidden;
  }
  .pagination {
    margin-top: -1px;
    padding: 14px 16px;
    height: 60px;
    border: 1px solid #dcdee5;
    background: #fff;
    >>> .bk-page-total-count {
      color: #63656e;
    }
    >>> .bk-page-count {
      margin-top: -1px;
    }
  }
}
</style>
