declare module '*.vue' {
  import Vue from 'vue';
  export default Vue;
}

declare namespace NodeJS {
  interface Global {
    [prop: string]: any
  }
}

interface Dictionary {
  [prop: string]: any
}

interface Window {
  [prop: string]: any
}

declare const LOGIN_DEV_URL: any;
declare const AJAX_URL_PREFIX: any;
declare const AJAX_MOCK_PARAM: any;
declare const LOCAL_DEV_URL: any;
declare const LOCAL_DEV_PORT: any;
declare const NODE_ENV: any;

declare module 'bk-magic-vue' {
  export const locale: any;
  export const lang: any;
  export const bkBadge: any;
  export const bkButton: any;
  export const bkCheckbox: any;
  export const bkCheckboxGroup: any;
  export const bkCol: any;
  export const bkCollapse: any;
  export const bkCollapseItem: any;
  export const bkContainer: any;
  export const bkDatePicker: any;
  export const bkDialog: any;
  export const bkDropdownMenu: any;
  export const bkException: any;
  export const bkForm: any;
  export const bkFormItem: any;
  export const bkInfoBox: any;
  export const bkInput: any;
  export const bkLoading: any;
  export const bkMessage: any;
  export const bkNavigation: any;
  export const bkNavigationMenu: any;
  export const bkNavigationMenuItem: any;
  export const bkNotify: any;
  export const bkOption: any;
  export const bkOptionGroup: any;
  export const bkPagination: any;
  export const bkPopover: any;
  export const bkProcess: any;
  export const bkProgress: any;
  export const bkRadio: any;
  export const bkRadioGroup: any;
  export const bkRoundProgress: any;
  export const bkRow: any;
  export const bkSearchSelect: any;
  export const bkSelect: any;
  export const bkSideslider: any;
  export const bkSlider: any;
  export const bkSteps: any;
  export const bkSwitcher: any;
  export const bkTab: any;
  export const bkTabPanel: any;
  export const bkTable: any;
  export const bkTableColumn: any;
  export const bkTagInput: any;
  export const bkTimePicker: any;
  export const bkTimeline: any;
  export const bkTransfer: any;
  export const bkTree: any;
  export const bkBigTree: any;
  export const bkUpload: any;
  export const bkClickoutside: any;
  export const bkTooltips: any;
  export const bkSwiper: any;
  export const bkRate: any;
  export const bkLink: any;
  export const bkCascade: any;
  export const bkOverflowTips: any;
}

declare module '@blueking/paas-login'

declare module '*.svg'
declare module '*.png'
declare module '*.jpg'
