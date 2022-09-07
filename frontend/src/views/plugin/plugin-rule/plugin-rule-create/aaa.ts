import https  from '@/api/modules/ipchooser';

export const fetchTopologyWithCount = async () => https.ipChooserHostCheck();
export const fetchTopologyHost = async () => https.ipChooserHostCheck();
export const fetchTopogyHostIdList = async () => https.ipChooserHostCheck();
export const fetchHostInfoByHostId = async () => https.ipChooserHostCheck();
export const fetchInputParseHostList = async () => https.ipChooserHostCheck();
export const fetchNodePath = async () => https.ipChooserHostCheck();
export const fetchBatchNodeAgentStatistics = async () => https.ipChooserHostCheck();
export const fetchDynamicGroup = async () => https.ipChooserHostCheck();
export const fetchDynamicGroupHost = async () => https.ipChooserHostCheck();
export const fetchBatchGroupAgentStatistics = async () => https.ipChooserHostCheck();
export const fetchAll = async () => https.ipChooserHostCheck();
export const update = async () => https.ipChooserHostCheck();

export default {
  fetchTopologyWithCount,
  fetchTopologyHost,
  fetchTopogyHostIdList,
  fetchHostInfoByHostId,
  fetchInputParseHostList,
  fetchNodePath,
  fetchBatchNodeAgentStatistics,
  fetchDynamicGroup,
  fetchDynamicGroupHost,
  fetchBatchGroupAgentStatistics,
  fetchAll,
  update,
};
