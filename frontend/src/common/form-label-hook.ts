import { ref } from 'vue';

export default function useFormLabelWidth() {
  const minWidth = ref(0);

  const initLabelWidth = (form: Vue) => {
    const el = form ? form.$el : null;
    if (!el) return;
    let max = 0;
    const leftPadding = 28;
    const safePadding = 8;
    const $labelEleList = el.querySelectorAll('.bk-label');
    $labelEleList.forEach((item) => {
      const spanEle = item.querySelector('span');
      if (spanEle) {
        const { width } = spanEle.getBoundingClientRect();
        max = Math.max(minWidth.value, max, width);
      }
    });
    const width = Math.ceil(max + leftPadding + safePadding);
    $labelEleList.forEach((item) => {
      (item as HTMLElement).style.width = `${width}px`;
    });
    el.querySelectorAll('.bk-form-content').forEach((item) => {
      (item as HTMLElement).style.marginLeft = `${width}px`;
    });
    return width;
  };

  return {
    minWidth,
    initLabelWidth,
  };
}
