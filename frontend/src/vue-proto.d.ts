import Vue, { VNode } from 'vue';
import { TranslateResult } from 'vue-i18n';
import 'vue-router';
import { INodemanHttp } from './types';
import { NmSafety } from './setup/safety';
// 给vue对象添加自定义方法
declare module 'vue/types/vue' {
  interface Vue {
    $bkPopover: (e: EventTarget, options: {
      [prop: string]: any
      content: any
      trigger?: string
      arrow?: boolean
      theme?: string
      maxWidth?: number
      offset?: any
      sticky?: boolean
      duration?: number[]
      interactive?: boolean
    }) => {}
    $bkMessage: (options: { [prop: string]: any }) => {}
    messageSuccess: (message: string, delay?: number) => {}
    messageError: (message: string, delay?: number) => {}
    messageInfo: (message: string, delay?: number) => {}
    $bkInfo: (options: {
      title: string | TranslateResult
      subHeader?: string | TranslateResult | VNode
      subTitle?: string | TranslateResult
      width?: number | string
      type?: string,
      okText?: string | TranslateResult
      cancelText?: string | TranslateResult
      extCls?: string
      confirmFn?: Function
      cancelFn?: Function
    }) => {}
    $filters: Function
    $safety: NmSafety,
    $textTool: {
      getTextWidth: (text: string, extraWidth?: number) => number
      getHeadWidth: (text: string, config?: Dictionary) => number
    }
    $initIpProp: (obj: Dictionary, keys: string[]) => void
    $setIpProp:  (key: string, val: Dictionary) => any
    $DHCP: boolean
    $http: INodemanHttp
    emptySearchClear: () => void
    emptyRefresh: () => void
    filterEmpty: (any) => string
  }
}

type Dictionary<T> = { [key: string]: T };
type ErrorHandler = (err: Error) => void;
type RawLocation = string | Location;
interface Location {
  name?: string;
  path?: string;
  hash?: string;
  query?: Dictionary<string | (string | null)[] | null | undefined>;
  params?: Dictionary<any>;
  append?: boolean;
  replace?: boolean;
}

declare module 'vue-router' {
  export default class VueRouter {
    public push (location: RawLocation, onComplete?: Function, onAbort?: ErrorHandler): void
    public replace(location: RawLocation, onComplete?: Function | undefined, onAbort?: ErrorHandler | undefined): void
  }
}
