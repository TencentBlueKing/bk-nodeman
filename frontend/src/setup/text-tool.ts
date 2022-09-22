import Vue from 'vue';

interface ITextItem {
  value: string,
  font: string
}

class TextTool {
  private canvas: HTMLCanvasElement = null;
  private ctx: CanvasRenderingContext2D  = null;
  private systemCls = '';
  private font = '';
  private fontSize = 12;
  private fontFamilyZh = '';
  private fontFamilyEn = ''; // 英文、数字、符号
  public constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.init();
  }
  public init() {
    const isWin = window.navigator.platform.toLowerCase().indexOf('win') === 0;
    this.systemCls = isWin ? 'win' : 'mac';
    this.fontFamilyZh = isWin ? 'Microsoft YaHei' : 'PingFang SC';
    this.fontFamilyEn = isWin ? 'Arial' : 'Helvetica Neue';
  }
  public setFont(font: string) {
    this.font = font;
    this.ctx.font = font;
  }
  public setFontSize(fontSize: number) {
    this.fontSize = fontSize;
  }
  public resetCanvas() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
  }
  public getWidth2(text: string): number {
    this.setFont('12px Microsoft YaHei');
    return this.ctx.measureText(text).width;
  }
  public getWidth(item: ITextItem): number {
    this.setFont(item.font);
    return this.ctx.measureText(item.value).width;
  }
  // extraWidth： padding、margin等已知的额外宽度
  public getTextWidth(text: string, extraWidth = 0) {
    let width = extraWidth;
    try {
      const textArr: ITextItem[] = `${text}`.split('').map(item => ({
        value: item,
        font: `${this.fontSize}px ${escape(item).indexOf('%u') < 0 ? this.fontFamilyEn : this.fontFamilyZh}`,
      }));
      textArr.forEach((item) => {
        width += this.getWidth(item);
      });
    } catch (_) {
      width = 0;
      console.warn(_);
    }
    return Math.ceil(width);
  }
  public getHeadWidth(text: string, config = {}) {
    let realText = text;
    let extraWidth = 0;
    const { extra = 0, padding = 30, margin = 0, filter = false, sort = false } = config;
    extraWidth = extraWidth + extra + padding + margin;
    if (filter || sort) {
      if (filter) {
        extraWidth += 14; // 13 + 1
        realText = `${text}\n`;
      }
      if (sort) {
        extraWidth += 20;
      }
    }
    return this.getTextWidth(realText, extraWidth);
  }
}

export const textTool = new TextTool();

Vue.prototype.$textTool = textTool;
