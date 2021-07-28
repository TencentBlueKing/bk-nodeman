/* eslint-disable no-underscore-dangle */
import { DirectiveOptions } from 'vue';
import { DirectiveBinding } from 'vue/types/options';
import { addListener, removeListener } from 'resize-detector';

interface ICustomElements extends HTMLElement {
  __mutation__?: MutationObserver
}

export const mutation: DirectiveOptions = {
  bind: (el: ICustomElements, binding: DirectiveBinding) => {
    const options: MutationObserverInit = {
      attributes: true, childList: true, subtree: true,
    };
    const observer = new MutationObserver(binding.value);
    observer.observe(el, options);
    el.__mutation__ = observer;
  },
  unbind: (el: ICustomElements) => {
    el.__mutation__?.disconnect();
  },
};

export const resize: DirectiveOptions = {
  bind: (el: HTMLElement, binding: DirectiveBinding) => {
    addListener(el, binding.value);
  },
  unbind: (el: HTMLElement, binding: DirectiveBinding) => {
    removeListener(el, binding.value);
  },
};

export default {
  mutation,
  resize,
};
