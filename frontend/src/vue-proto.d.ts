import Vue from 'vue';
import { TranslateResult } from 'vue-i18n';
import 'vue-router';
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
    $bkInfo: (options: {
      title: string | TranslateResult
      subTitle?: string | TranslateResult
      width?: number | string
      type?: string,
      okText?: string | TranslateResult
      cancelText?: string | TranslateResult
      confirmFn?: Function
      cancelFn?: Function
    }) => {}
    $filters: Function
    $RSA: {
      instance: Dictionary,
      setPublicKey: (publicKey: string) => void
      setName: (name: string) => void
      setPrivateKey: (privateKey: string) => void
      getKey: () => Dictionary
      getKeyLength: () => number
      getChunkLength: () => number
      encrypt: (word: string) => string
      decrypt: (word: string) => string
      encryptChunk: (word: string) => string
      decryptChunk: (word: string) => string
      getNameMixinEncrypt: (word: string) => string
    }
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
  }
}
