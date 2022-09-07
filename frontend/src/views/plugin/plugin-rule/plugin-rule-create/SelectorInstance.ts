import createIpSelector from '@/components/ip-selector-X/index.js';
import AppManageService  from './aaa';

const SelectorInstance = createIpSelector({
  panelList: ['staticTopo', 'dynamicTopo', 'dynamicGroup', 'manualInput'],
  unqiuePanelValue: false,
  fetchTopologyHostCount: AppManageService.fetchTopologyWithCount,
  fetchTopologyHostsNodes: AppManageService.fetchTopologyHost,
  fetchTopologyHostIdsNodes: AppManageService.fetchTopogyHostIdList,
  fetchHostsDetails: AppManageService.fetchHostInfoByHostId,
  fetchHostCheck: AppManageService.fetchInputParseHostList,
  fetchNodesQueryPath: AppManageService.fetchNodePath,
  fetchHostAgentStatisticsNodes: AppManageService.fetchBatchNodeAgentStatistics,
  fetchDynamicGroups: AppManageService.fetchDynamicGroup,
  fetchHostsDynamicGroup: AppManageService.fetchDynamicGroupHost,
  fetchHostAgentStatisticsDynamicGroups: AppManageService.fetchBatchGroupAgentStatistics,
  fetchCustomSettings: AppManageService.fetchAll,
  updateCustomSettings: AppManageService.update,
  fetchConfig: () => QueryGlobalSettingService.fetchRelatedSystemUrls()
    .then(data => ({
      // eslint-disable-next-line max-len
      bk_cmdb_dynamic_group_url: `${data.BK_CMDB_ROOT_URL}/#/business/${window.PROJECT_CONFIG.SCOPE_ID}/custom-query`,
      // eslint-disable-next-line max-len
      bk_cmdb_static_topo_url: `${data.BK_CMDB_ROOT_URL}/#/business/${window.PROJECT_CONFIG.SCOPE_ID}/custom-query`,
    })),
});

export default SelectorInstance;
