/* eslint-disable import/no-duplicates */

import Vue from 'vue';

import {
  bkBadge, bkButton, bkCheckbox, bkCheckboxGroup, bkCol, bkCollapse, bkCollapseItem, bkContainer, bkDatePicker,
  bkDialog, bkDropdownMenu, bkException, bkForm, bkFormItem, bkComposeFormItem,
  bkInfoBox, bkInput, bkLoading, bkMessage,
  bkNavigation, bkNavigationMenu, bkNavigationMenuItem, bkNotify, bkOption, bkOptionGroup, bkPagination,
  bkPopover, bkProcess, bkProgress, bkRadio, bkRadioGroup, bkRoundProgress, bkRow, bkSearchSelect, bkSelect,
  bkSideslider, bkSlider, bkSteps, bkSwitcher, bkTab, bkTabPanel, bkTable, bkTableColumn, bkTagInput, bkTimePicker,
  bkTimeline, bkTransfer, bkTree, bkBigTree, bkUpload, bkClickoutside, bkTooltips, bkSwiper, bkRate, bkLink, bkCascade,
  bkPopconfirm, bkOverflowTips, bkVirtualScroll, bkTag, bkNavigationMenuGroup,
  // , bkAnimateNumber,
} from 'bk-magic-vue';

// bkDiff 组件体积较大且不是很常用，因此注释掉。如果需要，打开注释即可
// import { bkDiff } from 'bk-magic-vue'

// components use
Vue.use(bkBadge);
Vue.use(bkButton);
Vue.use(bkCheckbox);
Vue.use(bkCheckboxGroup);
Vue.use(bkCol);
Vue.use(bkCollapse);
Vue.use(bkCollapseItem);
Vue.use(bkContainer);
Vue.use(bkDatePicker);
Vue.use(bkDialog);
Vue.use(bkDropdownMenu);
Vue.use(bkException);
Vue.use(bkForm);
Vue.use(bkFormItem);
Vue.use(bkComposeFormItem);
Vue.use(bkInput);
Vue.use(bkNavigation);
Vue.use(bkNavigationMenu);
Vue.use(bkNavigationMenuItem);
Vue.use(bkOption);
Vue.use(bkOptionGroup);
Vue.use(bkPagination);
Vue.use(bkPopover);
Vue.use(bkProcess);
Vue.use(bkProgress);
Vue.use(bkRadio);
Vue.use(bkRadioGroup);
Vue.use(bkRoundProgress);
Vue.use(bkRow);
Vue.use(bkSearchSelect);
Vue.use(bkSelect);
Vue.use(bkSideslider);
Vue.use(bkSlider);
Vue.use(bkSteps);
Vue.use(bkSwitcher);
Vue.use(bkTab);
Vue.use(bkTabPanel);
Vue.use(bkTable);
Vue.use(bkTableColumn);
Vue.use(bkTagInput);
Vue.use(bkTimePicker);
Vue.use(bkTimeline);
Vue.use(bkTransfer);
Vue.use(bkTree);
Vue.use(bkBigTree);
Vue.use(bkUpload);
Vue.use(bkSwiper);
Vue.use(bkRate);
Vue.use(bkLink);
Vue.use(bkCascade);
Vue.use(bkPopconfirm);
// Vue.use(bkAnimateNumber)
Vue.use(bkVirtualScroll);
// bkDiff 组件体积较大且不是很常用，因此注释了。如果需要，打开注释即可
// Vue.use(bkDiff)
Vue.use(bkTag);
Vue.use(bkNavigationMenuGroup);

// directives use
Vue.use(bkClickoutside);
Vue.use(bkTooltips);
Vue.use(bkLoading);
Vue.use(bkOverflowTips);

// Vue prototype mount
Vue.prototype.$bkInfo = bkInfoBox;
Vue.prototype.$bkMessage = bkMessage;
Vue.prototype.$bkNotify = bkNotify;
