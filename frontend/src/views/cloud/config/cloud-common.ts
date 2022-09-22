import { ICloud } from '@/types/cloud/cloud';
import { sort } from '@/common/util';

export function cloudSort(data: ICloud[], permissionSwitch: boolean) {
  let enableData: ICloud[] = [...data];
  let disableData: ICloud[] = [];
  // 一类分类
  if (permissionSwitch) {
    enableData = data.filter(item => item.view);
    disableData = cloudSecondSort(data.filter(item => !item.view));
  }
  enableData = cloudSecondSort(enableData);
  return [...enableData, ...disableData];
}

/**
 * 二类分类 & 排序
 * 分类   一类：有无权限; 二类：未安装、0个可用、1个可用、n个可用    PS: alive_proxy_count可用数量
 * 规则   一类 > 二类 + 字母排序
 */
export function cloudSecondSort(data: ICloud[]) {
  const notInstalledList = data.filter(item => !item.proxyCount);
  const unavailableList = data.filter(item => item.proxyCount && !item.aliveProxyCount);
  const onlyOneList = data.filter(item => item.aliveProxyCount === 1);
  const multipleList = data.filter(item => item.aliveProxyCount > 1);
  // 二类分别做一次排序
  [notInstalledList, unavailableList, onlyOneList, multipleList].forEach((list) => {
    sort(list, 'bkCloudName');
  });
  return [...notInstalledList, ...unavailableList, ...onlyOneList, ...multipleList];
}
